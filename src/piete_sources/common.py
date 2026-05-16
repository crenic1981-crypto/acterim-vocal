"""Utilitare comune: filtre, deduplicare, cache, date, parsare HTML."""
from __future__ import annotations
import json, re, time
from datetime import datetime, timedelta
from pathlib import Path
from bs4 import BeautifulSoup

GRAND_EST_DEPT = {"08", "10", "51", "52", "54", "55", "57", "67", "68", "88"}
CPV_BTP = {"45", "39"}
SOURCE_PRIORITY = {"BOAMP": 1, "DECP": 2, "TED": 3, "PLACE": 4, "Région GE": 5,
                   "France Marchés": 6, "Marchés Sécurisés": 7, "AWS": 8,
                   "Maximilien": 9, "e-marchespublics": 10, "Centrale Marchés": 11}

CACHE_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "piete_cache.json"
CACHE_TTL_HOURS = 6


def date_il_y_a(jours: int) -> str:
    return (datetime.now() - timedelta(days=jours)).strftime("%Y-%m-%d")


def is_grand_est(lieu: str) -> bool:
    if not lieu:
        return False
    # (67), 67XXX, Bas-Rhin, etc.
    m = re.search(r'\b(\d{2})\d{0,3}\b', lieu)
    if m and m.group(1) in GRAND_EST_DEPT:
        return True
    VILLES = {"strasbourg", "metz", "nancy", "reims", "mulhouse", "colmar",
              "troyes", "charleville", "épinal", "chaumont", "bar-le-duc",
              "saint-dié", "thionville", "haguenau", "saverne", "sarrebourg"}
    return any(v in lieu.lower() for v in VILLES)


def is_btp_cpv(cpv: str) -> bool:
    return str(cpv or "")[:2] in CPV_BTP


def normalize_siren(raw: str) -> str:
    digits = re.sub(r"\D", "", str(raw or ""))
    return digits[:9] if len(digits) >= 9 else ""


def parse_html_rows(html: str, source: str) -> list[dict]:
    """Parser générique HTML — tentative best-effort."""
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("table tr") or soup.select(".result-item") or soup.select("article")
    out = []
    for row in rows:
        text = row.get_text(separator=" ", strip=True)
        if not text or len(text) < 20:
            continue
        out.append({"titre": text[:200], "source": source, "_raw": True})
    return out


def filter_grand_est_btp(marches: list[dict]) -> list[dict]:
    filtered = []
    for m in marches:
        if not is_btp_cpv(m.get("cpv", "")):
            continue
        if not is_grand_est(m.get("lieu", "") + " " + m.get("dept", "")):
            continue
        statut = (m.get("statut") or "").lower()
        if statut and statut not in ("attribué", "attribue", "awarded", "attribution", ""):
            continue
        duree = m.get("duree_mois") or 0
        if duree and float(duree) < 0.05:
            continue
        # Consortium → un prospect per membru
        if m.get("consortium"):
            for mb in m["consortium"]:
                filtered.append({**m, "attributaire": mb.get("nom", ""),
                                  "siren": normalize_siren(mb.get("siren", "")),
                                  "consortium": []})
        else:
            filtered.append(m)
    return filtered


def deduplicate(marches: list[dict]) -> list[dict]:
    seen: dict[tuple, dict] = {}
    for m in marches:
        key = (normalize_siren(m.get("siren", "")), m.get("montant"), m.get("date_attrib"))
        if key not in seen:
            seen[key] = m
        else:
            p_exist = SOURCE_PRIORITY.get(seen[key].get("source", ""), 99)
            p_new = SOURCE_PRIORITY.get(m.get("source", ""), 99)
            if p_new < p_exist:
                seen[key] = m
    return list(seen.values())


# --- Cache ---
def cache_valid() -> bool:
    if not CACHE_FILE.exists():
        return False
    data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    ts = data.get("_ts", 0)
    return (time.time() - ts) < CACHE_TTL_HOURS * 3600


def load_cache() -> dict:
    return json.loads(CACHE_FILE.read_text(encoding="utf-8"))


def save_cache(result: dict) -> None:
    CACHE_FILE.parent.mkdir(exist_ok=True)
    result["_ts"] = time.time()
    CACHE_FILE.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
