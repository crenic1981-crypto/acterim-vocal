"""Sursa 10 — TED / JOUE Europa (Categoria A) — marchés mari > seuils europene."""
from __future__ import annotations
import aiohttp
from .common import date_il_y_a, normalize_siren

URL = "https://ted.europa.eu/api/v3.0/notices/search"


async def fetch(session: aiohttp.ClientSession, jours: int = 90) -> list[dict]:
    payload = {
        "query": (
            f"FT~\"Grand Est\" AND CY=FR AND CPV~45 "
            f"AND PD>={date_il_y_a(jours).replace('-', '')} "
            f"AND TY=7"
        ),
        "limit": 100,
        "fields": ["ND", "PD", "TI", "PN", "CAE", "OJ"],
    }
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    try:
        async with session.post(URL, json=payload, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=60)) as r:
            if r.status != 200:
                return []
            data = await r.json()
        results = []
        for notice in (data.get("notices") or data.get("results") or []):
            nd = notice.get("ND") or notice.get("nd", "")
            results.append({
                "marche_id": f"TED-{nd}",
                "titre": str(notice.get("TI") or notice.get("ti") or "")[:200],
                "montant": 0,
                "attributaire": str(notice.get("CAE") or ""),
                "siren": "",
                "date_attrib": str(notice.get("PD") or ""),
                "lieu": "Grand Est",
                "duree_mois": 0,
                "source": "TED",
                "cpv": "45",
                "consortium": [],
                "lots": [],
            })
        return results
    except Exception:
        return []
