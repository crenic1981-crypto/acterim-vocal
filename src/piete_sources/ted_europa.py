"""Sursa 10 — TED / JOUE Europa.
Mode réactif: cherche par SIREN ou nom société.
Mode scan: cherche Grand Est global.
"""
from __future__ import annotations
import aiohttp
from .common import date_il_y_a, normalize_siren

URL = "https://ted.europa.eu/api/v3.0/notices/search"


def _parse_notices(notices: list[dict], siren: str = "") -> list[dict]:
    out = []
    for n in notices:
        nd = n.get("ND") or n.get("nd", "")
        out.append({
            "marche_id": f"TED-{nd}",
            "titre": str(n.get("TI") or n.get("ti") or "")[:200],
            "montant": 0,
            "attributaire": str(n.get("CAE") or n.get("cae") or ""),
            "siren": siren,
            "date_attrib": str(n.get("PD") or n.get("pd") or ""),
            "lieu": "Grand Est",
            "dept": "",
            "duree_mois": 0,
            "source": "TED",
            "cpv": "45",
            "consortium": [],
            "lots": [],
        })
    return out


async def fetch_by_company(session: aiohttp.ClientSession, siren: str,
                           societe: str, jours: int = 365) -> list[dict]:
    """Mode réactif — cherche par SIREN ou nom."""
    payload = {
        "query": (
            f'(FT~"{siren}" OR FT~"{societe[:40]}") '
            f'AND CY=FR AND CPV~45 '
            f'AND PD>={date_il_y_a(jours).replace("-", "")} '
            f'AND TY=7'
        ),
        "limit": 50,
        "fields": ["ND", "PD", "TI", "CAE"],
    }
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    try:
        async with session.post(URL, json=payload, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=45)) as r:
            if r.status != 200:
                return []
            data = await r.json()
        notices = data.get("notices") or data.get("results") or []
        return _parse_notices(notices, siren)
    except Exception:
        return []


async def fetch(session: aiohttp.ClientSession, jours: int = 90) -> list[dict]:
    """Mode scan global."""
    payload = {
        "query": (
            f'FT~"Grand Est" AND CY=FR AND CPV~45 '
            f'AND PD>={date_il_y_a(jours).replace("-", "")} AND TY=7'
        ),
        "limit": 100,
        "fields": ["ND", "PD", "TI", "CAE"],
    }
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    try:
        async with session.post(URL, json=payload, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=60)) as r:
            if r.status != 200:
                return []
            data = await r.json()
        notices = data.get("notices") or data.get("results") or []
        return _parse_notices(notices)
    except Exception:
        return []
