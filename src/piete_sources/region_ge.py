"""Sursa 9 — Région Grand Est (Categoria B) — platforma regională oficială."""
from __future__ import annotations
import aiohttp
from .common import parse_html_rows

URL = "https://www.grandest.fr/marches-publics/"


async def fetch(session: aiohttp.ClientSession, jours: int = 90) -> list[dict]:
    try:
        params = {"periode": jours, "cpv_categorie": "45", "statut": "attribue"}
        async with session.get(URL, params=params, timeout=aiohttp.ClientTimeout(total=30)) as r:
            if r.status != 200:
                return []
            html = await r.text()
        rows = parse_html_rows(html, "Région GE")
        for row in rows:
            row["cpv"] = "45"
            row["lieu"] = "Grand Est"
        return rows
    except Exception:
        return []
