"""Sursa 11 — La Centrale des Marchés (Categoria B)."""
from __future__ import annotations
import asyncio, aiohttp
from .common import parse_html_rows, GRAND_EST_DEPT

BASE = "https://www.lacentraledesmarches.com"


async def _fetch_dept(session: aiohttp.ClientSession, dept: str) -> list[dict]:
    try:
        url = f"{BASE}/marches-publics/search"
        params = {"departement": dept, "cpv_root": "45", "statut": "attribue"}
        headers = {"User-Agent": "Mozilla/5.0 ACTERIM-Bot/3.0"}
        async with session.get(url, params=params, headers=headers,
                               timeout=aiohttp.ClientTimeout(total=20)) as r:
            if r.status != 200:
                return []
            html = await r.text()
        rows = parse_html_rows(html, "Centrale Marchés")
        for row in rows:
            row["lieu"] = f"({dept})"
            row["cpv"] = "45"
        return rows
    except Exception:
        return []


async def fetch(session: aiohttp.ClientSession, jours: int = 90) -> list[dict]:
    tasks = [_fetch_dept(session, d) for d in sorted(GRAND_EST_DEPT)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    out = []
    for r in results:
        if isinstance(r, list):
            out.extend(r)
    return out
