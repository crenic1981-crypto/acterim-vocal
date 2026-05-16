"""Sursa 2 — DECP v3 (Categoria A)."""
from __future__ import annotations
import aiohttp
from .common import date_il_y_a, normalize_siren, GRAND_EST_DEPT

URL = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-v3/records"
DEPT_FILTER = ",".join(f'"{d}"' for d in sorted(GRAND_EST_DEPT))


async def fetch(session: aiohttp.ClientSession, jours: int = 90) -> list[dict]:
    params = {
        "where": (
            f'datenotification >= date\'{date_il_y_a(jours)}\' '
            f'AND (codecpv LIKE "45%" OR codecpv LIKE "39%") '
            f'AND lieuexecutioncode IN ({DEPT_FILTER})'
        ),
        "limit": 100,
        "select": "id,objet,montant,titulaire_denominationsociale,titulaire_id,"
                  "datenotification,lieuexecutionnom,dureemois,codecpv",
    }
    results = []
    offset = 0
    while True:
        params["offset"] = offset
        async with session.get(URL, params=params, timeout=aiohttp.ClientTimeout(total=60)) as r:
            if r.status != 200:
                break
            data = await r.json()
        records = data.get("results", [])
        if not records:
            break
        for rec in records:
            results.append({
                "marche_id": f"DECP-{rec.get('id', '')}",
                "titre": (rec.get("objet") or "")[:200],
                "montant": int(rec.get("montant") or 0),
                "attributaire": rec.get("titulaire_denominationsociale", ""),
                "siren": normalize_siren(rec.get("titulaire_id") or ""),
                "date_attrib": rec.get("datenotification", ""),
                "lieu": rec.get("lieuexecutionnom", ""),
                "duree_mois": float(rec.get("dureemois") or 0),
                "source": "DECP",
                "cpv": str(rec.get("codecpv") or ""),
                "consortium": [],
                "lots": [],
            })
        if len(records) < 100:
            break
        offset += 100
    return results
