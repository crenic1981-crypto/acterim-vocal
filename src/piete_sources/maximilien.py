"""Sursa 8 — Maximilien (Categoria B) — filtrare manuală Grand Est."""
from __future__ import annotations
import aiohttp
from .common import parse_html_rows, is_grand_est

URL = "https://www.maximilien.fr/consultations/list"


async def fetch(session: aiohttp.ClientSession, jours: int = 90) -> list[dict]:
    try:
        params = {"statut": "attribue", "cpv_famille": "45", "nb_resultats": 50}
        headers = {"User-Agent": "Mozilla/5.0 ACTERIM-Bot/3.0"}
        async with session.get(URL, params=params, headers=headers,
                               timeout=aiohttp.ClientTimeout(total=30)) as r:
            if r.status != 200:
                return []
            html = await r.text()
        rows = parse_html_rows(html, "Maximilien")
        # Filtru manual Grand Est (Maximilien = Île-de-France mais indexe national)
        rows = [row for row in rows if is_grand_est(row.get("lieu", ""))]
        for row in rows:
            row["cpv"] = "45"
        return rows
    except Exception:
        return []
