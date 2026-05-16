"""Sursa 1 — BOAMP API.
Mode reactiv: caută după SIREN/titulaire pentru o firmă specifică.
Mode scan: scan global Grand Est (pentru inject_marches_excel).
"""
from __future__ import annotations
import aiohttp
from .common import date_il_y_a, normalize_siren, is_grand_est, GRAND_EST_DEPT

URL = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records"


def _parse_records(records: list[dict]) -> list[dict]:
    out = []
    for rec in records:
        lieu_raw = rec.get("lieu_execution") or {}
        lieu_str = lieu_raw.get("nom", "") if isinstance(lieu_raw, dict) else str(lieu_raw)
        titulaires = rec.get("titulaire") or []
        if not titulaires:
            titulaires = [""]
        for t in titulaires:
            out.append({
                "marche_id": f"BOAMP-{rec.get('idweb', '')}",
                "titre": (rec.get("objet") or "")[:200],
                "montant": int(rec.get("montant") or 0),
                "attributaire": str(t).strip(),
                "siren": "",  # BOAMP titulaire = nom, pas SIRET
                "date_attrib": rec.get("dateparution", ""),
                "lieu": lieu_str,
                "dept": str(rec.get("code_departement") or [""])[2:4],
                "duree_mois": float(rec.get("duree") or 0),
                "source": "BOAMP",
                "cpv": "45",  # filtre via nature_libelle
                "consortium": [],
                "lots": [],
            })
    return out


async def fetch_by_company(session: aiohttp.ClientSession, siren: str,
                           societe: str, jours: int = 365) -> list[dict]:
    """Mode reactif — cherche marchés d'une firme par nom (BOAMP n'a pas SIRET dans titulaire)."""
    # Nom court pour la recherche (évite les formes juridiques)
    import re
    nom_court = re.sub(r'\s+(SAS|SARL|SA|EURL|SASU|SNC|GIE|SCOP)\s*$', '',
                       societe.upper().strip(), flags=re.IGNORECASE)[:40]
    results = []
    for nom in {nom_court, societe[:40]}:
        params = {
            "where": (
                f'nature_libelle = "Résultat de marché" '
                f'AND dateparution >= "{date_il_y_a(jours)}" '
                f'AND titulaire LIKE "*{nom}*"'
            ),
            "limit": 50,
            "select": "idweb,dateparution,objet,titulaire,code_departement,donnees,duree",
        }
        try:
            async with session.get(URL, params=params,
                                   timeout=aiohttp.ClientTimeout(total=30)) as r:
                if r.status != 200:
                    continue
                data = await r.json()
            results.extend(_parse_records(data.get("results", [])))
        except Exception:
            continue
    return results


async def fetch(session: aiohttp.ClientSession, jours: int = 90) -> list[dict]:
    """Mode scan global — toutes départements Grand Est (utilisé par inject_marches_excel)."""
    since = date_il_y_a(jours)
    all_marches = []
    for dept in sorted(GRAND_EST_DEPT):
        offset = 0
        while True:
            params = {
                "where": f'nature_libelle = "Résultat de marché" AND dateparution >= "{since}"',
                "refine": f"code_departement:{dept}",
                "limit": 100,
                "offset": offset,
                "select": "idweb,dateparution,objet,titulaire,code_departement,duree",
            }
            try:
                async with session.get(URL, params=params,
                                       timeout=aiohttp.ClientTimeout(total=30)) as r:
                    if r.status != 200:
                        break
                    data = await r.json()
                recs = data.get("results", [])
                for rec in recs:
                    lieu_raw = rec.get("lieu_execution") or {}
                    lieu_str = lieu_raw.get("nom", "") if isinstance(lieu_raw, dict) else str(lieu_raw)
                    titulaires = rec.get("titulaire") or []
                    for t in titulaires:
                        all_marches.append({
                            "marche_id": f"BOAMP-{rec.get('idweb', '')}",
                            "titre": (rec.get("objet") or "")[:150],
                            "montant": 0,
                            "attributaire": str(t).strip(),
                            "siren": "",
                            "dept": dept,
                            "lieu": lieu_str or f"({dept})",
                            "date_attrib": rec.get("dateparution", ""),
                            "duree_mois": float(rec.get("duree") or 0),
                            "source": "BOAMP",
                            "cpv": "45",
                        })
                if len(recs) < 100:
                    break
                offset += 100
            except Exception:
                break
    return all_marches
