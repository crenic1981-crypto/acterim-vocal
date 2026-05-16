"""Sursa 7 — AWS / marches-publics.info (Categoria B)."""
from __future__ import annotations
import asyncio, aiohttp
from .common import parse_html_rows, GRAND_EST_DEPT

URL = "https://www.marches-publics.info/consultations.htm"


async def _fetch_dept(session: aiohttp.ClientSession, dept: str) -> list[dict]:
    try:
        params = {"dept": dept, "cpv": "45", "etat": "attribue"}
        async with session.get(URL, params=params, timeout=aiohttp.ClientTimeout(total=20)) as r:
            if r.status != 200:
                return []
            html = await r.text()
        rows = parse_html_rows(html, "AWS")
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
