"""Sub-agent Firme — eligibilitate + date juridice/financiare BTP."""
from __future__ import annotations
import asyncio, json, time
from pathlib import Path
import httpx
from . import config

CACHE_FILE = config.CACHE_DIR / "firme_cache.json"
CACHE_TTL = 30 * 24 * 3600  # 30 zile


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(c: dict) -> None:
    CACHE_FILE.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")


async def _pappers(siren: str, client: httpx.AsyncClient) -> dict | None:
    if not config.PAPPERS_API_KEY:
        return None
    try:
        r = await client.get(
            "https://api.pappers.fr/v2/entreprise",
            params={"api_token": config.PAPPERS_API_KEY, "siren": siren},
            timeout=15,
        )
        if r.status_code != 200:
            return None
        d = r.json()
        siege = d.get("siege") or {}
        dirigeants = d.get("representants") or []
        dirigeant = ""
        if dirigeants:
            p = dirigeants[0]
            dirigeant = f"{p.get('prenom','')} {p.get('nom','')}".strip()
        finance = (d.get("finances") or [{}])[0]
        return {
            "siren": d.get("siren", siren),
            "societe": d.get("nom_entreprise") or d.get("denomination", ""),
            "adresse": siege.get("adresse_ligne_1", ""),
            "cp": siege.get("code_postal", ""),
            "ville": siege.get("ville", ""),
            "dept": (siege.get("code_postal") or "")[:2],
            "naf": d.get("code_naf", ""),
            "forme": d.get("forme_juridique", ""),
            "date_creation": d.get("date_creation", ""),
            "effectif": int(d.get("effectif_min") or 0),
            "ca_annuel": int(finance.get("chiffre_affaires") or 0),
            "dirigeant": dirigeant,
            "site": d.get("site_web", ""),
        }
    except Exception:
        return None


async def _annuaire_entreprises(siren: str, client: httpx.AsyncClient) -> dict | None:
    try:
        r = await client.get(
            f"https://recherche-entreprises.api.gouv.fr/search",
            params={"q": siren}, timeout=15,
        )
        if r.status_code != 200:
            return None
        res = (r.json().get("results") or [])
        if not res:
            return None
        e = res[0]
        siege = e.get("siege") or {}
        return {
            "siren": e.get("siren", siren),
            "societe": e.get("nom_complet") or e.get("nom_raison_sociale", ""),
            "adresse": siege.get("adresse", ""),
            "cp": siege.get("code_postal", ""),
            "ville": siege.get("libelle_commune", ""),
            "dept": (siege.get("code_postal") or "")[:2],
            "naf": e.get("activite_principale", ""),
            "forme": e.get("nature_juridique", ""),
            "date_creation": e.get("date_creation", ""),
            "effectif": int(e.get("tranche_effectif_salarie") or 0),
            "dirigeant": (e.get("dirigeants") or [{}])[0].get("nom_complet", ""),
        }
    except Exception:
        return None


def _evaluate(data: dict) -> dict:
    flags: list[str] = []
    if not data.get("siren") or len(data["siren"]) != 9:
        return {"siren": data.get("siren", ""), "eligible": False, "exclusion_raison": "siren_invalid"}
    if not config.is_btp_naf(data.get("naf", "")):
        return {"siren": data["siren"], "eligible": False, "exclusion_raison": "naf_non_btp"}
    if not config.is_grand_est(data.get("dept", "")):
        return {"siren": data["siren"], "eligible": False, "exclusion_raison": "hors_grand_est"}
    if (data.get("effectif") or 0) < config.EFFECTIF_MIN:
        return {"siren": data["siren"], "eligible": False, "exclusion_raison": "effectif_insuffisant"}
    forme = (data.get("forme") or "").lower()
    if "auto" in forme or "micro" in forme:
        return {"siren": data["siren"], "eligible": False, "exclusion_raison": "auto_entrepreneur"}
    # Vechime
    dc = data.get("date_creation", "")
    if dc and len(dc) >= 4:
        try:
            an = int(dc[:4])
            if 2026 - an < config.VECHIME_MIN_ANI:
                return {"siren": data["siren"], "eligible": False, "exclusion_raison": "vechime_insuffisante"}
        except ValueError:
            pass
    ca = data.get("ca_annuel") or 0
    if ca == 0:
        flags.append("ca_non_communique")
    elif ca < config.CA_MIN:
        return {"siren": data["siren"], "eligible": False, "exclusion_raison": "ca_insuffisant"}
    data["flags"] = flags
    data["eligible"] = True
    return data


async def run(siren: str | None = None, name: str | None = None) -> dict:
    """Cascadă surse → primul care completează → evaluare eligibilitate."""
    if not siren and not name:
        return {"eligible": False, "exclusion_raison": "input_vide"}

    cache = _load_cache()
    key = siren or name or ""
    cached = cache.get(key)
    if cached and (time.time() - cached.get("_ts", 0)) < CACHE_TTL:
        return {k: v for k, v in cached.items() if k != "_ts"}

    async with httpx.AsyncClient() as client:
        data: dict | None = None
        if siren:
            for source in (_pappers, _annuaire_entreprises):
                data = await source(siren, client)
                if data and data.get("naf"):
                    break

    if not data:
        result = {"siren": siren or "", "eligible": False, "exclusion_raison": "introuvable"}
    else:
        result = _evaluate(data)

    cache[key] = {**result, "_ts": time.time()}
    _save_cache(cache)
    return result


async def run_batch(sirens: list[str]) -> list[dict]:
    sem = asyncio.Semaphore(5)
    async def _one(s: str):
        async with sem:
            return await run(siren=s)
    return await asyncio.gather(*[_one(s) for s in sirens])
