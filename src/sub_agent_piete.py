"""Sub-agent Piete — marchés publics BTP atribuite Grand Est."""
from __future__ import annotations
import asyncio
from datetime import datetime, timedelta
import httpx
from . import config

BOAMP_API = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records"
DECP_API = "https://decp.info/api/v1/marches.json"


async def _boamp(client: httpx.AsyncClient, siren: str | None = None) -> list[dict]:
    since = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    where_parts = [f"dateparution >= date'{since}'", "(famille_cpv = 45 OR famille_cpv = 39)"]
    dept_filter = " OR ".join([f"departement = '{d}'" for d in config.GRAND_EST])
    where_parts.append(f"({dept_filter})")
    if siren:
        where_parts.append(f"siret like '{siren}%'")
    try:
        r = await client.get(BOAMP_API, params={
            "where": " AND ".join(where_parts),
            "limit": 100,
            "select": "idweb,objet,montant,attributaire,siret,dateparution,lieu_execution_nom,cpv,dc",
        }, timeout=30)
        if r.status_code != 200:
            return []
        out = []
        for rec in r.json().get("results", []):
            siret = (rec.get("siret") or "")[:9]
            out.append({
                "marche_id": f"BOAMP-{rec.get('idweb','?')}",
                "titre": rec.get("objet", "")[:200],
                "montant": int(rec.get("montant") or 0),
                "attributaire": rec.get("attributaire", ""),
                "siren": siret,
                "date_attrib": rec.get("dateparution", ""),
                "lieu": rec.get("lieu_execution_nom", ""),
                "source": "BOAMP",
                "cpv": str(rec.get("cpv", "")),
            })
        return out
    except Exception:
        return []


def _score_marches(n: int) -> int:
    if n >= 3:
        return 20
    if n == 2:
        return 15
    if n == 1:
        return 10
    return 0


async def run(siren: str | None = None) -> dict:
    async with httpx.AsyncClient() as client:
        results = await _boamp(client, siren=siren)
    # Deduplicare după marche_id
    seen, dedup = set(), []
    for m in results:
        if m["marche_id"] in seen:
            continue
        seen.add(m["marche_id"])
        dedup.append(m)
    if siren:
        dedup = [m for m in dedup if m["siren"] == siren]
    return {
        "marches": dedup,
        "nb": len(dedup),
        "score_bonus": _score_marches(len(dedup)),
    }
