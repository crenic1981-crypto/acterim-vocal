"""Sursa 5 — e-marchespublics.com (Categoria C — skip dacă login eșuează)."""
from __future__ import annotations
import aiohttp
from .common import parse_html_rows


async def fetch(session: aiohttp.ClientSession, jours: int = 90) -> list[dict]:
    try:
        url = "https://www.e-marchespublics.com/consultations/attribuees"
        params = {"region": "Grand-Est", "cpv_filter": "45,39"}
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=20)) as r:
            if r.status in (401, 403):
                return []  # login requis — skip silent
            if r.status != 200:
                return []
            html = await r.text()
        rows = parse_html_rows(html, "e-marchespublics")
        for row in rows:
            row["cpv"] = "45"
            row["lieu"] = "Grand Est"
        return rows
    except Exception:
        return []
