"""Sursa 2 — DECP v3 (Données Essentielles Commande Publique).
Cea mai precisă pentru SIREN — titulaire_id = SIRET (primele 9 = SIREN).
"""
from __future__ import annotations
import aiohttp
from .common import date_il_y_a, normalize_siren, GRAND_EST_DEPT

URL = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-v3/records"
DEPT_FILTER = ",".join(f'"{d}"' for d in sorted(GRAND_EST_DEPT))


def _build_row(rec: dict) -> dict:
    return {
        "marche_id": f"DECP-{rec.get('id', '')}",
        "titre": (rec.get("objet") or "")[:200],
        "montant": int(float(rec.get("montant") or 0)),
        "attributaire": rec.get("titulaire_denominationsociale", ""),
        "siren": normalize_siren(rec.get("titulaire_id") or ""),
        "date_attrib": rec.get("datenotification", ""),
        "lieu": rec.get("lieuexecutionnom", ""),
        "dept": str(rec.get("lieuexecutioncode") or "")[:2],
        "duree_mois": float(rec.get("dureemois") or 0),
        "source": "DECP",
        "cpv": str(rec.get("codecpv") or ""),
        "consortium": [],
        "lots": [],
    }


async def fetch_by_siren(session: aiohttp.ClientSession, siren: str,
                         jours: int = 365) -> list[dict]:
    """Mode réactif — filtre direct sur SIREN (titulaire_id LIKE siren%)."""
    params = {
        "where": (
            f'datenotification >= "{date_il_y_a(jours)}" '
            f'AND (codecpv LIKE "45%" OR codecpv LIKE "39%") '
            f'AND titulaire_id LIKE "{siren}%"'
        ),
        "limit": 50,
        "select": "id,objet,montant,titulaire_denominationsociale,titulaire_id,"
                  "datenotification,lieuexecutionnom,lieuexecutioncode,dureemois,codecpv",
    }
    try:
        async with session.get(URL, params=params,
                               timeout=aiohttp.ClientTimeout(total=30)) as r:
            if r.status != 200:
                return []
            data = await r.json()
        return [_build_row(rec) for rec in data.get("results", [])]
    except Exception:
        return []


async def fetch(session: aiohttp.ClientSession, jours: int = 90) -> list[dict]:
    """Mode scan global Grand Est CPV 45/39."""
    params = {
        "where": (
            f'datenotification >= "{date_il_y_a(jours)}" '
            f'AND (codecpv LIKE "45%" OR codecpv LIKE "39%") '
            f'AND lieuexecutioncode IN ({DEPT_FILTER})'
        ),
        "limit": 100,
        "select": "id,objet,montant,titulaire_denominationsociale,titulaire_id,"
                  "datenotification,lieuexecutionnom,lieuexecutioncode,dureemois,codecpv",
    }
    results = []
    offset = 0
    while True:
        params["offset"] = offset
        try:
            async with session.get(URL, params=params,
                                   timeout=aiohttp.ClientTimeout(total=60)) as r:
                if r.status != 200:
                    break
                data = await r.json()
            recs = data.get("results", [])
            results.extend(_build_row(r) for r in recs)
            if len(recs) < 100:
                break
            offset += 100
        except Exception:
            break
    return results
