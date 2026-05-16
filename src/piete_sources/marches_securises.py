"""Sursa 6 — Marchés Sécurisés (Categoria B)."""
from __future__ import annotations
import asyncio, aiohttp
from .common import parse_html_rows, GRAND_EST_DEPT

BASE = "https://www.marches-securises.fr/entreprise/"


async def _fetch_dept(session: aiohttp.ClientSession, dept: str) -> list[dict]:
    try:
        params = {"module": "marches", "action": "attribues", "departement": dept, "cpv": "45"}
        async with session.get(BASE, params=params, timeout=aiohttp.ClientTimeout(total=20)) as r:
            if r.status != 200:
                return []
            html = await r.text()
        rows = parse_html_rows(html, "Marchés Sécurisés")
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
