"""Sursa 1 — BOAMP API (Categoria A, prioritate maximă)."""
from __future__ import annotations
import aiohttp
from .common import date_il_y_a, normalize_siren, is_grand_est

URL = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records"


async def fetch(session: aiohttp.ClientSession, jours: int = 90) -> list[dict]:
    params = {
        "where": (
            f'dateparution >= date\'{date_il_y_a(jours)}\' '
            f'AND nature_libelle = "Avis d\'attribution" '
            f'AND (descripteur_code LIKE "45%" OR descripteur_code LIKE "39%")'
        ),
        "refine": "famille_libelle:Travaux",
        "limit": 100,
        "select": "idweb,dateparution,objet,nomacheteur,attributaires,montant,"
                  "lieu_execution,famille_libelle,descripteur_code,cpv,duree,siret",
    }
    results = []
    offset = 0
    while True:
        params["offset"] = offset
        async with session.get(URL, params=params, timeout=aiohttp.ClientTimeout(total=60)) as r:
            if r.status != 200:
                break
            data = await r.json()
        records = data.get("results", [])
        if not records:
            break
        for rec in records:
            lieu = (rec.get("lieu_execution") or {})
            lieu_str = lieu.get("nom", "") if isinstance(lieu, dict) else str(lieu)
            if not is_grand_est(lieu_str):
                continue
            attrs = rec.get("attributaires") or [{}]
            a = attrs[0] if attrs else {}
            siren = normalize_siren(a.get("siret") or rec.get("siret") or "")
            consortium = [
                {"nom": x.get("denomination", ""), "siren": normalize_siren(x.get("siret", ""))}
                for x in attrs[1:]
            ] if len(attrs) > 1 else []
            results.append({
                "marche_id": f"BOAMP-{rec.get('idweb', '')}",
                "titre": (rec.get("objet") or "")[:200],
                "montant": int(rec.get("montant") or 0),
                "attributaire": a.get("denomination", ""),
                "siren": siren,
                "date_attrib": rec.get("dateparution", ""),
                "lieu": lieu_str,
                "duree_mois": float(rec.get("duree") or 0),
                "source": "BOAMP",
                "cpv": str(rec.get("cpv") or rec.get("descripteur_code") or ""),
                "consortium": consortium,
                "lots": [],
            })
        if len(records) < 100:
            break
        offset += 100
    return results
