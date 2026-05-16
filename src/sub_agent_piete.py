"""Sub-agent Piete v3.2 — două moduri de funcționare:

MODE REACTIV (principal): check_company(siren, societe)
  - Apelat de Agent Principal cu SIREN + nume firmă
  - Caută șantierele active ale firmei în 11 surse
  - Returnează JSON cu santiere_active[] + luni_pe_santier
  - Firma NU e exclusă dacă rezultatul e zero

MODE SCAN (secundar): scan_all_sources(jours)
  - Scan global Grand Est pentru inject_marches_excel / prospectare
  - Cache 6h
"""
from __future__ import annotations
import asyncio
from datetime import date
import aiohttp

from .piete_sources import (
    boamp, decp, place, france_marches, e_marchespublics,
    marches_securises, aws_marches, maximilien, region_ge,
    ted_europa, centrale,
)
from .piete_sources.common import (
    filter_btp_for_siren, filter_grand_est_btp, deduplicate,
    santier_activ_3_luni, cache_valid, load_cache, save_cache,
    date_il_y_a,
)

TIMEOUT_TOTAL = 60  # secunde max per firmă


# ---------- Helpers HTML pour mode réactif ----------

async def _fetch_html_by_company(session: aiohttp.ClientSession, url: str,
                                  name: str, siren: str, societe: str) -> list[dict]:
    from .piete_sources.common import parse_html_rows
    for query in [siren, societe[:40].replace(" ", "+")]:
        try:
            async with session.get(f"{url}?q={query}",
                                   timeout=aiohttp.ClientTimeout(total=20)) as r:
                if r.status in (401, 403):
                    return []
                if r.status == 200:
                    html = await r.text()
                    if len(html) > 500:
                        rows = parse_html_rows(html, name)
                        for row in rows:
                            row["cpv"] = "45"
                            row["lieu"] = "Grand Est"
                            row["siren"] = ""
                        return rows
        except Exception:
            pass
    return []


SOURCES_HTML = {
    "PLACE": "https://www.marches-publics.gouv.fr/?page=Entreprise.EntrepriseAdvancedSearch",
    "France Marchés": "https://www.francemarches.com/marches-publics/recherche/",
    "Marchés Sécurisés": "https://www.marches-securises.fr/entreprise/",
    "AWS": "https://www.marches-publics.info/consultations.htm",
    "Maximilien": "https://www.maximilien.fr/consultations/list",
    "Région GE": "https://www.grandest.fr/marches-publics/",
    "La Centrale": "https://www.lacentraledesmarches.com/marches-publics/search",
    "e-marchespublics": "https://www.e-marchespublics.com/consultations/attribuees",
}


async def _safe(coro, name: str) -> tuple[str, list[dict]]:
    """Wrapper: retourne (name, result) ou (name, []) si échec."""
    try:
        result = await asyncio.wait_for(coro, timeout=TIMEOUT_TOTAL)
        return name, result if isinstance(result, list) else []
    except Exception:
        return name, []


# ---------- MODE RÉACTIF ----------

async def check_firma_santiere(siren: str, societe: str, jours: int = 365) -> dict:
    """Vérifie les chantiers actifs d'une firme. Cache désactivé — toujours fresh."""
    connector = aiohttp.TCPConnector(limit=20, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            _safe(boamp.fetch_by_company(session, siren, societe, jours), "BOAMP"),
            _safe(decp.fetch_by_siren(session, siren, jours), "DECP"),
            _safe(ted_europa.fetch_by_company(session, siren, societe, jours), "TED"),
        ] + [
            _safe(_fetch_html_by_company(session, url, name, siren, societe), name)
            for name, url in SOURCES_HTML.items()
        ]
        raw = await asyncio.gather(*tasks)

    surse_ok = sum(1 for _, r in raw if r)
    all_marches: list[dict] = []
    for _, result in raw:
        all_marches.extend(result)

    filtered = filter_btp_for_siren(deduplicate(all_marches), siren)
    santiere_active = [m for m in filtered if santier_activ_3_luni(m)]

    luni_max = "0 / 0"
    if santiere_active:
        best = max(santiere_active, key=lambda m: int(m.get("luni_pe_santier", "0 / 0").split("/")[0]))
        luni_max = best.get("luni_pe_santier", "0 / 0")

    return {
        "siren": siren,
        "societe": societe,
        "santiere_active": santiere_active,
        "nb_santiere_active": len(santiere_active),
        "luni_pe_santier_max": luni_max,
        "scan_date": date.today().isoformat(),
        "surse_consultate": len(tasks),
        "surse_eshuate": len(tasks) - surse_ok,
    }


async def check_company(siren: str, societe: str) -> dict:
    """Entry point principal — apelat de Agent Principal după confirmarea eligibilității."""
    if not siren or len(siren) != 9 or not siren.isdigit():
        return {
            "siren": siren, "societe": societe,
            "santiere_active": [], "nb_santiere_active": 0,
            "luni_pe_santier_max": "0 / 0",
            "scan_date": date.today().isoformat(),
            "surse_consultate": 0, "surse_eshuate": 0,
            "error": "siren_invalid",
        }
    return await check_firma_santiere(siren, societe)


# ---------- MODE SCAN (backward compat) ----------

SOURCES_SCAN = [
    ("BOAMP",            boamp.fetch),
    ("DECP",             decp.fetch),
    ("PLACE",            place.fetch),
    ("France Marchés",   france_marches.fetch),
    ("e-marchespublics", e_marchespublics.fetch),
    ("Marchés Sécurisés",marches_securises.fetch),
    ("AWS",              aws_marches.fetch),
    ("Maximilien",       maximilien.fetch),
    ("Région GE",        region_ge.fetch),
    ("TED",              ted_europa.fetch),
    ("Centrale Marchés", centrale.fetch),
]


async def scan_all_sources(jours: int = 90, filter_siren: str | None = None,
                           force: bool = False) -> dict:
    if not force and cache_valid():
        cached = load_cache()
        if filter_siren:
            cached["marches"] = [m for m in cached["marches"] if m.get("siren") == filter_siren]
        return cached

    connector = aiohttp.TCPConnector(limit=20, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [_safe(fn(session, jours), name) for name, fn in SOURCES_SCAN]
        raw = await asyncio.gather(*tasks)

    surse_ok = sum(1 for _, r in raw if r)
    all_marches: list[dict] = []
    for _, r in raw:
        all_marches.extend(r)

    filtered = filter_grand_est_btp(deduplicate(all_marches))
    if filter_siren:
        filtered = [m for m in filtered if m.get("siren") == filter_siren]

    result = {
        "scan_date": date.today().isoformat(),
        "periode_jours": jours,
        "surse_active": surse_ok,
        "surse_eshuate": len(SOURCES_SCAN) - surse_ok,
        "total_marches": len(filtered),
        "marches": filtered,
    }
    if not filter_siren:
        save_cache(result)
    return result


def _score_marches(n: int) -> int:
    if n >= 3: return 20
    if n == 2: return 15
    if n == 1: return 10
    return 0


async def run(siren: str | None = None, jours: int = 90, force: bool = False) -> dict:
    """Backward compat pour agent_principal.py (scan mode)."""
    result = await scan_all_sources(jours=jours, filter_siren=siren, force=force)
    nb = result["total_marches"]
    return {**result, "nb": nb, "score_bonus": _score_marches(nb)}
