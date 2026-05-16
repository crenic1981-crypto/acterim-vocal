"""Sub-agent Piete v3.0 — orchestrare 11 surse marchés publics BTP Grand Est.
Entry point: scan_all_sources() / run()
"""
from __future__ import annotations
import asyncio
from datetime import datetime
import aiohttp

from .piete_sources import (
    boamp, decp, place, france_marches, e_marchespublics,
    marches_securises, aws_marches, maximilien, region_ge,
    ted_europa, centrale,
)
from .piete_sources.common import (
    filter_grand_est_btp, deduplicate,
    cache_valid, load_cache, save_cache,
)

SOURCES = [
    ("BOAMP",           boamp.fetch),
    ("DECP",            decp.fetch),
    ("PLACE",           place.fetch),
    ("France Marchés",  france_marches.fetch),
    ("e-marchespublics",e_marchespublics.fetch),
    ("Marchés Sécurisés",marches_securises.fetch),
    ("AWS",             aws_marches.fetch),
    ("Maximilien",      maximilien.fetch),
    ("Région GE",       region_ge.fetch),
    ("TED",             ted_europa.fetch),
    ("Centrale Marchés",centrale.fetch),
]


async def _safe_fetch(session: aiohttp.ClientSession, name: str, fn, jours: int) -> list[dict]:
    try:
        result = await asyncio.wait_for(fn(session, jours), timeout=60)
        return result if isinstance(result, list) else []
    except Exception:
        return []  # skip silent — sursele eșuate nu blochează


async def scan_all_sources(jours: int = 90, filter_siren: str | None = None,
                           force: bool = False) -> dict:
    if not force and cache_valid():
        cached = load_cache()
        if filter_siren:
            cached["marches"] = [m for m in cached["marches"]
                                 if m.get("siren") == filter_siren]
        return cached

    connector = aiohttp.TCPConnector(limit=20, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [_safe_fetch(session, name, fn, jours) for name, fn in SOURCES]
        raw_results = await asyncio.gather(*tasks)

    surse_ok = sum(1 for r in raw_results if r)
    all_marches: list[dict] = []
    for r in raw_results:
        all_marches.extend(r)

    filtered = filter_grand_est_btp(all_marches)
    deduped = deduplicate(filtered)

    if filter_siren:
        deduped = [m for m in deduped if m.get("siren") == filter_siren]

    result = {
        "scan_date": datetime.now().strftime("%Y-%m-%d"),
        "periode_jours": jours,
        "surse_active": surse_ok,
        "surse_eshuate": len(SOURCES) - surse_ok,
        "total_marches": len(deduped),
        "marches": deduped,
    }
    if not filter_siren:
        save_cache(result)
    return result


def _score_marches(n: int) -> int:
    if n >= 3: return 20
    if n == 2: return 15
    if n == 1: return 10
    return 0


async def run(siren: str | None = None, jours: int = 90, force: bool = False) -> dict:
    """Interfață compatibilă cu agent_principal.py."""
    result = await scan_all_sources(jours=jours, filter_siren=siren, force=force)
    nb = result["total_marches"]
    return {
        **result,
        "nb": nb,
        "score_bonus": _score_marches(nb),
    }
