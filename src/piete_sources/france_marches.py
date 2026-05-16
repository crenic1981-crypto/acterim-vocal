"""Sursa 4 — France Marchés (Categoria B)."""
from __future__ import annotations
import aiohttp
from .common import date_il_y_a, parse_html_rows

BASE = "https://www.francemarches.com"


async def fetch(session: aiohttp.ClientSession, jours: int = 90) -> list[dict]:
    try:
        url = f"{BASE}/marches-publics/grand-est/attribution/"
        headers = {"User-Agent": "Mozilla/5.0 ACTERIM-Bot/3.0"}
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as r:
            if r.status != 200:
                return []
            html = await r.text()
        rows = parse_html_rows(html, "France Marchés")
        for row in rows:
            row["cpv"] = "45"
            row["lieu"] = "Grand Est"
        return rows
    except Exception:
        return []
