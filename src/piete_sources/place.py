"""Sursa 3 — PLACE marchespublics.gouv.fr (Categoria B, scraping HTML)."""
from __future__ import annotations
import asyncio, aiohttp
from .common import date_il_y_a, parse_html_rows, GRAND_EST_DEPT

BASE = "https://www.marches-publics.gouv.fr/index.php"


async def _fetch_dept(session: aiohttp.ClientSession, dept: str, jours: int) -> list[dict]:
    params = {
        "page": "Entreprise.EntrepriseAdvancedSearch",
        "ctl_ref_dept": dept,
        "ctl_ref_cpv": "45000000",
        "ctl_date_pub_debut": date_il_y_a(jours),
        "ctl_etat": "attribue",
    }
    try:
        async with session.get(BASE, params=params, timeout=aiohttp.ClientTimeout(total=30)) as r:
            if r.status != 200:
                return []
            html = await r.text()
        rows = parse_html_rows(html, "PLACE")
        for row in rows:
            row["lieu"] = f"({dept})"
            row["cpv"] = "45"
        return rows
    except Exception:
        return []


async def fetch(session: aiohttp.ClientSession, jours: int = 90) -> list[dict]:
    tasks = [_fetch_dept(session, d, jours) for d in sorted(GRAND_EST_DEPT)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    out = []
    for r in results:
        if isinstance(r, list):
            out.extend(r)
    return out
