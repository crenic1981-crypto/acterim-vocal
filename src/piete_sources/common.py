"""Utilitare comune: filtre, deduplicare, cache, date, parsare HTML."""
from __future__ import annotations
import json, re, time
from datetime import date, datetime, timedelta
from pathlib import Path
from bs4 import BeautifulSoup

try:
    from dateutil.relativedelta import relativedelta
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False

GRAND_EST_DEPT = {"08", "10", "51", "52", "54", "55", "57", "67", "68", "88"}
CPV_BTP = {"45", "39"}
MIN_LUNI_PE_SANTIER = 3
DEFAULT_DUREE_MOIS = 12  # medie BTP dacă durată necunoscută

# Prioritate deduplicare: DECP cel mai precis pentru SIREN
SOURCE_PRIORITY = {"DECP": 1, "BOAMP": 2, "TED": 3, "PLACE": 4, "Région GE": 5,
                   "France Marchés": 6, "Marchés Sécurisés": 7, "AWS": 8,
                   "Maximilien": 9, "e-marchespublics": 10, "Centrale Marchés": 11}

CACHE_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "piete_cache.json"
CACHE_TTL_HOURS = 6


# ---------- Date ----------

def date_il_y_a(jours: int) -> str:
    return (datetime.now() - timedelta(days=jours)).strftime("%Y-%m-%d")


def parse_date(s: str | None) -> date | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(s)[:19], fmt).date()
        except ValueError:
            continue
    return None


# ---------- Géographie ----------

def is_grand_est(lieu: str) -> bool:
    if not lieu:
        return False
    m = re.search(r'\((\d{2})\)', lieu)
    if m:
        return m.group(1) in GRAND_EST_DEPT
    m2 = re.search(r'\b(\d{5})\b', lieu)
    if m2:
        return m2.group(1)[:2] in GRAND_EST_DEPT
    VILLES = {"strasbourg", "metz", "nancy", "reims", "mulhouse", "colmar",
              "troyes", "charleville", "épinal", "chaumont", "bar-le-duc",
              "saint-dié", "thionville", "haguenau", "saverne", "sarrebourg"}
    return any(v in lieu.lower() for v in VILLES)


def is_btp_cpv(cpv: str) -> bool:
    return str(cpv or "")[:2] in CPV_BTP


def normalize_siren(raw: str) -> str:
    digits = re.sub(r"\D", "", str(raw or ""))
    return digits[:9] if len(digits) >= 9 else digits


# ---------- Logica șantier activ ----------

def santier_activ_3_luni(marche: dict, today: date | None = None) -> bool:
    """
    True dacă firma e pe șantier de ≥ 3 luni ȘI șantierul nu s-a terminat.
    Modifică marche in-place: adaugă luni_pe_santier și date_fin_estimee.
    """
    today = today or date.today()
    date_attrib = parse_date(marche.get("date_attrib"))
    if not date_attrib:
        return False

    duree_mois = marche.get("duree_mois")
    # Durată 0 sau null → default 12 luni
    if not duree_mois:
        duree_mois = DEFAULT_DUREE_MOIS

    try:
        duree_mois = float(duree_mois)
    except (TypeError, ValueError):
        duree_mois = DEFAULT_DUREE_MOIS

    if duree_mois < 0.1:
        return False  # date insuficiente

    # Date fin estimée
    if HAS_DATEUTIL:
        date_fin = date_attrib + relativedelta(months=int(duree_mois))
    else:
        months = int(duree_mois)
        year = date_attrib.year + (date_attrib.month + months - 1) // 12
        month = (date_attrib.month + months - 1) % 12 + 1
        date_fin = date_attrib.replace(year=year, month=month)

    # 1. Au trecut ≥ 3 luni de la atribuire
    jours_scurs = (today - date_attrib).days
    luni_scurse = jours_scurs / 30.0
    if luni_scurse < MIN_LUNI_PE_SANTIER:
        return False

    # 2. Șantierul încă în curs
    if date_fin <= today:
        return False

    luni_display = int(min(luni_scurse, duree_mois))
    marche["luni_pe_santier"] = f"{luni_display} / {int(duree_mois)}"
    marche["date_fin_estimee"] = date_fin.isoformat()
    return True


# ---------- Filtrare ----------

def filter_btp_for_siren(marches: list[dict], siren_target: str) -> list[dict]:
    """Filtre stricte: SIREN match + BTP (CPV) + Grand Est + atribuit."""
    filtered = []
    for m in marches:
        siren_m = normalize_siren(m.get("siren", ""))
        if siren_m and siren_m != siren_target:
            continue  # SIREN diferit — excludem
        if not is_btp_cpv(m.get("cpv", "")):
            continue
        if not is_grand_est(m.get("lieu", "") + " " + m.get("dept", "")):
            continue
        statut = (m.get("statut") or "").lower()
        if statut and statut not in ("attribué", "attribue", "awarded", "attribution", ""):
            continue
        filtered.append(m)
    return filtered


def filter_grand_est_btp(marches: list[dict]) -> list[dict]:
    """Filtrare fără SIREN match (pentru scan global)."""
    filtered = []
    for m in marches:
        if not is_btp_cpv(m.get("cpv", "")):
            continue
        if not is_grand_est(m.get("lieu", "") + " " + m.get("dept", "")):
            continue
        statut = (m.get("statut") or "").lower()
        if statut and statut not in ("attribué", "attribue", "awarded", "attribution", ""):
            continue
        if m.get("consortium"):
            for mb in m["consortium"]:
                filtered.append({**m, "attributaire": mb.get("nom", ""),
                                  "siren": normalize_siren(mb.get("siren", "")),
                                  "consortium": []})
        else:
            filtered.append(m)
    return filtered


# ---------- Deduplicare ----------

def deduplicate(marches: list[dict]) -> list[dict]:
    """Prioritate: DECP > BOAMP > TED > restul."""
    seen: dict[tuple, dict] = {}
    for m in marches:
        key = (
            m.get("montant"),
            str(m.get("date_attrib", ""))[:10],
            str(m.get("titre", ""))[:50].lower().strip(),
        )
        if key not in seen:
            seen[key] = m
        else:
            p_exist = SOURCE_PRIORITY.get(seen[key].get("source", ""), 99)
            p_new = SOURCE_PRIORITY.get(m.get("source", ""), 99)
            if p_new < p_exist:
                seen[key] = m
    return list(seen.values())


# ---------- HTML ----------

def parse_html_rows(html: str, source: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("table tr") or soup.select(".result-item") or soup.select("article")
    out = []
    for row in rows:
        text = row.get_text(separator=" ", strip=True)
        if not text or len(text) < 20:
            continue
        out.append({"titre": text[:200], "source": source, "_raw": True})
    return out


# ---------- Cache (scan global uniquement) ----------

def cache_valid() -> bool:
    if not CACHE_FILE.exists():
        return False
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        return (time.time() - data.get("_ts", 0)) < CACHE_TTL_HOURS * 3600
    except Exception:
        return False


def load_cache() -> dict:
    return json.loads(CACHE_FILE.read_text(encoding="utf-8"))


def save_cache(result: dict) -> None:
    CACHE_FILE.parent.mkdir(exist_ok=True)
    result["_ts"] = time.time()
    CACHE_FILE.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
