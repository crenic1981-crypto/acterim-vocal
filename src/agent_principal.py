"""Agent Principal — hub central. Singurul care scrie în Google Sheets.
Orchestrează sub-agenții, calculează scoring, gestionează campanii."""
from __future__ import annotations
import asyncio, json
from datetime import datetime
from typing import Any
from . import config, sub_agent_firme, sub_agent_contacte, sub_agent_piete, sub_agent_teren
from .google_sheets import SheetsClient, PROSPECTS_HEADERS, fmt_date


# ---------- Scoring ----------

def _score_effectif(e: int) -> int:
    if e >= 50: return 20
    if e >= 20: return 15
    if e >= 10: return 10
    if e >= 5: return 5
    return 0

def _score_ca(ca: int) -> int:
    if ca >= 5_000_000: return 20
    if ca >= 2_000_000: return 15
    if ca >= 1_000_000: return 10
    if ca >= 500_000: return 5
    return 0

def _score_contact(contacts: list[dict]) -> int:
    if not contacts:
        return 0
    c1 = contacts[0]
    has_tel = bool(c1.get("tel"))
    has_email = bool(c1.get("email"))
    if has_tel and has_email:
        return 10
    if has_tel or has_email:
        return 5
    return 0

def _tier(score: int) -> str:
    if score >= 71: return "High"
    if score >= 31: return "Medium"
    return "Low"


def compute_score(firme: dict, contacts: list[dict], nb_marches: int) -> tuple[int, str]:
    raw = (
        _score_effectif(firme.get("effectif", 0))
        + _score_ca(firme.get("ca_annuel", 0))
        + sub_agent_piete._score_marches(nb_marches)
        + _score_contact(contacts)
    )
    # Scalat la 100 (max raw = 70)
    scaled = round(raw * 100 / 70)
    return scaled, _tier(scaled)


# ---------- Orchestrare ----------

class Principal:
    def __init__(self) -> None:
        self.sheets = SheetsClient()
        self._last_action: dict | None = None

    async def setup(self) -> None:
        await self.sheets.ensure_structure()

    async def process_siren(self, siren: str, source: str = "Manual") -> dict:
        """Cascadă completă: Firme → (Contacte ‖ Piete) → scoring → Sheets."""
        if await self.sheets.find_siren(siren):
            return {"siren": siren, "status": "skip_duplicate"}

        firme = await sub_agent_firme.run(siren=siren)
        if not firme.get("eligible"):
            return {"siren": siren, "status": "non_eligible", "raison": firme.get("exclusion_raison")}

        contacts_task = sub_agent_contacte.run(
            siren=siren,
            dirigeant=firme.get("dirigeant", ""),
            site=firme.get("site", ""),
            societe=firme.get("societe", ""),
        )
        # Mode réactif: vérifie chantiers actifs de CETTE firme
        piete_task = sub_agent_piete.check_company(
            siren=siren, societe=firme.get("societe", "")
        )
        contacts_res, piete_res = await asyncio.gather(contacts_task, piete_task)

        contacts = contacts_res.get("contacts", [])
        nb_santiere = piete_res.get("nb_santiere_active", 0)
        luni_santier = piete_res.get("luni_pe_santier_max", "0 / 0")
        score, tier = compute_score(firme, contacts, nb_santiere)

        c1 = contacts[0] if contacts else {}
        flags = list(firme.get("flags", []))
        if contacts_res.get("flags"):
            flags.extend(contacts_res["flags"])

        c2 = contacts[1] if len(contacts) > 1 else {}
        DEPT_LABELS = {"08":"Ardennes","10":"Aube","51":"Marne","52":"Haute-Marne",
                       "54":"Meurthe-et-Moselle","55":"Meuse","57":"Moselle",
                       "67":"Bas-Rhin","68":"Haut-Rhin","88":"Vosges"}
        dept = firme.get("dept", "")
        row = [
            firme.get("siren", siren), firme.get("societe", ""), firme.get("adresse", ""),
            firme.get("cp", ""), firme.get("ville", ""), dept, DEPT_LABELS.get(dept, ""),
            "" if dept in ("52","55","10","08") else "tournée_ok",
            "", firme.get("naf", ""), firme.get("forme", ""),
            firme.get("effectif", 0), firme.get("ca_annuel", 0), firme.get("date_creation", ""),
            firme.get("dirigeant", ""), c1.get("fonction", "Gérant"),
            c1.get("tel", ""), c1.get("email", ""), "true" if c1.get("wa") else "false",
            c2.get("nom", ""), c2.get("fonction", ""), c2.get("tel", ""),
            firme.get("site", ""), "",
            score, tier, nb_santiere, luni_santier, luni_santier,
            source, "À qualifier",
            "Haute" if tier == "High" else ("Moyenne" if tier == "Medium" else "Basse"),
            "", "",
            fmt_date(), "", fmt_date(),
            "", "",
            "", "",
            "", "true" if firme.get("recrutement") else "false",
            ",".join(flags), "",
        ]
        await self.sheets.append("Prospecți", row)
        self._last_action = {"type": "append", "sheet": "Prospecți", "siren": siren}
        return {
            "siren": siren,
            "societe": firme.get("societe"),
            "score": score,
            "tier": tier,
            "nb_santiere": nb_santiere,
            "luni_pe_santier": luni_santier,
            "nb_marches": nb_marches,
            "status": "added",
        }

    async def process_batch(self, sirens: list[str], source: str = "Manual") -> list[dict]:
        sem = asyncio.Semaphore(5)
        async def _one(s):
            async with sem:
                return await self.process_siren(s, source)
        return await asyncio.gather(*[_one(s) for s in sirens])

    async def process_telegram_payload(self, payload: dict, source: str = "Telegram") -> list[dict]:
        """Primește JSON OCR (panneau/carte/vehicul) → procesează firmele."""
        firmes = payload.get("firmes", []) or []
        results = []
        for f in firmes:
            siren = (f.get("siren") or "").replace(" ", "")
            if siren and len(siren) == 9:
                results.append(await self.process_siren(siren, source))
            else:
                results.append({"nom": f.get("nom"), "status": "siren_manquant"})
        return results

    # ---------- Interogări ----------

    async def query(self, filt: dict) -> list[dict]:
        rows = await self.sheets.all_prospects()
        def _match(r):
            for k, v in filt.items():
                rv = (r.get(k) or "").lower()
                if v.lower() not in rv:
                    return False
            return True
        return [r for r in rows if _match(r)]

    async def feedback_terrain(self, action: str, societe: str) -> dict:
        """vizitat/callback/nerelevant/interesat/client + nume firmă."""
        prospects = await self.sheets.all_prospects()
        match = next((p for p in prospects if societe.lower() in (p.get("Société") or "").lower()), None)
        if not match:
            return {"status": "not_found", "societe": societe}
        siren = match["SIREN"]
        row_idx = await self.sheets.find_siren(siren)
        if not row_idx:
            return {"status": "not_found"}
        mapping = {
            "vizitat": ("Contacté", True),
            "callback": ("Callback", True),
            "interesat": ("Interesat", True),
            "client": ("Client", True),
            "nerelevant": ("Exclus", True),
        }
        if action not in mapping:
            return {"status": "action_invalid"}
        statut, set_date = mapping[action]
        # Statut = col AC (29), Date_contact = col AH (34) în noua schemă
        await self.sheets.update_cell("Prospecți", row_idx, "AC", statut)
        if set_date:
            await self.sheets.update_cell("Prospecți", row_idx, "AH", fmt_date())
        self._last_action = {"type": "update", "siren": siren, "field": "Statut"}
        return {"status": "updated", "siren": siren, "statut": statut}

    async def undo_last(self) -> dict:
        if not self._last_action:
            return {"status": "no_action"}
        # Implementare minimă: marchează ca Exclus dacă append; nu rollback profund.
        if self._last_action["type"] == "append":
            siren = self._last_action["siren"]
            row_idx = await self.sheets.find_siren(siren)
            if row_idx:
                await self.sheets.update_cell("Prospecți", row_idx, "AC", "Exclus")
            self._last_action = None
            return {"status": "undone", "siren": siren}
        return {"status": "not_supported"}

    async def tournee(self, ville: str, n: int = 6) -> dict:
        return await sub_agent_teren.run(ville, n)

    async def relance(self) -> list[str]:
        return await sub_agent_teren.relance_alerts(self.sheets)
