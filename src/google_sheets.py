"""Wrapper Google Sheets API. Citire publică, scriere doar prin Agent Principal."""
from __future__ import annotations
import asyncio
from datetime import datetime
from typing import Any
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from . import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

PROSPECTS_HEADERS = [
    "SIREN", "Société", "Adresse", "CP", "Ville", "Dept", "Dept_label", "Zone_tournee",
    "Métier", "NAF", "Forme", "Effectif", "CA_annuel", "Date_creation",
    "Dirigeant", "Fonction", "Tel", "Email", "WhatsApp",
    "Contact2_nom", "Contact2_fonction", "Contact2_tel",
    "Site", "LinkedIn",
    "Score", "Tier", "Marchés", "Source", "Statut", "Priorité",
    "Garantie_credit", "Montant_garantie_K",
    "Date_ajout", "Date_contact", "Date_modification",
    "Besoin_detecte", "Phrase_accroche",
    "Latitude", "Longitude",
    "Concurent", "Recrutare", "Flags", "Notes",
]

ACTIONS_HEADERS = [
    "ID_Action", "SIREN", "Société", "Date_action", "Type_action", "Canal",
    "Objectif", "Message_angle", "Résultat", "Prochaine_action",
    "Date_prochaine_action", "Jours_avant_relance", "Statut_action",
    "Personne_contactée", "Fonction", "Nb_relances", "Source_action", "Commentaires",
]

SCRIPTS_HEADERS = [
    "ID_Script", "Type", "Canal", "Étape_pipeline", "Script", "Objectif",
    "Variables_dynamiques", "Dernière_MàJ",
]

PARAMETRI_DEFAULT = [
    ("score_effectif_max", 20, "Puncte max efectiv"),
    ("score_ca_max", 20, "Puncte max CA"),
    ("score_marches_max", 20, "Puncte max marchés"),
    ("score_contact_max", 10, "Puncte max contact"),
    ("effectif_min", 5, "Prag minim includere"),
    ("ca_min", 1000000, "CA minim (EUR)"),
    ("vechime_min_ani", 2, "Vechime minimă"),
    ("rayon_tournee_km", 30, "Raza tournée (km)"),
    ("max_prospects_tournee", 8, "Max prospecți per tournée"),
    ("min_prospects_tournee", 5, "Min prospecți per tournée"),
]


class SheetsClient:
    def __init__(self) -> None:
        creds = Credentials.from_service_account_file(str(config.GOOGLE_SA_FILE), scopes=SCOPES)
        self._svc = build("sheets", "v4", credentials=creds, cache_discovery=False)
        self._sid = config.GOOGLE_SHEET_ID

    # --- low-level ---
    def _values(self):
        return self._svc.spreadsheets().values()

    async def _run(self, fn, *a, **kw):
        return await asyncio.to_thread(lambda: fn(*a, **kw).execute())

    # --- read ---
    async def read(self, sheet: str, range_: str = "A1:Z10000") -> list[list[str]]:
        r = await self._run(self._values().get, spreadsheetId=self._sid, range=f"{sheet}!{range_}")
        return r.get("values", [])

    async def find_siren(self, siren: str) -> int | None:
        rows = await self.read("Prospecți", "A2:A10000")
        for i, row in enumerate(rows, start=2):
            if row and row[0].strip() == siren:
                return i
        return None

    async def all_prospects(self) -> list[dict[str, str]]:
        rows = await self.read("Prospecți")
        if not rows:
            return []
        return [dict(zip(PROSPECTS_HEADERS, r + [""] * (len(PROSPECTS_HEADERS) - len(r)))) for r in rows[1:]]

    async def get_params(self) -> dict[str, str]:
        rows = await self.read("Parametri", "A2:B100")
        return {r[0]: r[1] for r in rows if len(r) >= 2}

    # --- write ---
    async def append(self, sheet: str, row: list[Any]) -> None:
        await self._run(
            self._values().append,
            spreadsheetId=self._sid, range=f"{sheet}!A1",
            valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        )

    async def update_row(self, sheet: str, row_idx: int, row: list[Any]) -> None:
        await self._run(
            self._values().update,
            spreadsheetId=self._sid, range=f"{sheet}!A{row_idx}",
            valueInputOption="USER_ENTERED",
            body={"values": [row]},
        )

    async def update_cell(self, sheet: str, row_idx: int, col_letter: str, value: Any) -> None:
        await self._run(
            self._values().update,
            spreadsheetId=self._sid, range=f"{sheet}!{col_letter}{row_idx}",
            valueInputOption="USER_ENTERED",
            body={"values": [[value]]},
        )

    # --- bootstrap ---
    async def ensure_structure(self) -> None:
        meta = await asyncio.to_thread(
            lambda: self._svc.spreadsheets().get(spreadsheetId=self._sid).execute()
        )
        existing = {s["properties"]["title"] for s in meta.get("sheets", [])}
        needed = ["Prospecți", "Tournées", "Actions", "Scripts", "Campanii", "Parametri", "Arhivă", "Backup"]
        requests = [{"addSheet": {"properties": {"title": n}}} for n in needed if n not in existing]
        if requests:
            await asyncio.to_thread(
                lambda: self._svc.spreadsheets().batchUpdate(
                    spreadsheetId=self._sid, body={"requests": requests}
                ).execute()
            )
        # Headers
        await self._ensure_header("Prospecți", PROSPECTS_HEADERS)
        await self._ensure_header("Tournées", ["ID_Tournée", "SIREN", "Date", "Zone", "Heure",
                                                "Ordre_visite", "Priorité_visite", "Société", "Adresse",
                                                "CP", "Latitude", "Longitude", "Objectif_visite",
                                                "Contact_rencontré", "Statut_visite", "Résultat",
                                                "Action_suivante", "Date_relance", "Distance_km",
                                                "Temps_trajet_min", "Notes"])
        await self._ensure_header("Actions", ACTIONS_HEADERS)
        await self._ensure_header("Scripts", SCRIPTS_HEADERS)
        await self._ensure_header("Campanii", ["ID", "Date", "Filtru", "Nb", "Canal", "Statut"])
        await self._ensure_header("Arhivă", PROSPECTS_HEADERS + ["Raison_arhivare", "Date_arhivare"])
        await self._ensure_params()
        await self._ensure_conditional_formatting()

    async def _ensure_conditional_formatting(self) -> None:
        """Verde/galben/albastru pe coloana Score (col Y = index 24)."""
        meta = await asyncio.to_thread(
            lambda: self._svc.spreadsheets().get(spreadsheetId=self._sid).execute()
        )
        sheet_id = None
        for s in meta.get("sheets", []):
            if s["properties"]["title"] == "Prospecți":
                sheet_id = s["properties"]["sheetId"]
                break
        if sheet_id is None:
            return
        SCORE_COL = 24  # Y
        ranges = [{"sheetId": sheet_id, "startRowIndex": 1, "startColumnIndex": 0,
                   "endColumnIndex": len(PROSPECTS_HEADERS)}]
        rules = [
            (f"=$Y2>=71", {"red": 0.85, "green": 0.92, "blue": 0.83}),  # High vert
            (f"=AND($Y2>=31,$Y2<=70)", {"red": 1.0, "green": 0.95, "blue": 0.80}),  # Medium jaune
            (f"=AND($Y2>=0,$Y2<=30)", {"red": 0.81, "green": 0.89, "blue": 0.95}),  # Low bleu
        ]
        requests = []
        for i, (formula, color) in enumerate(rules):
            requests.append({"addConditionalFormatRule": {
                "rule": {"ranges": ranges,
                         "booleanRule": {
                             "condition": {"type": "CUSTOM_FORMULA",
                                           "values": [{"userEnteredValue": formula}]},
                             "format": {"backgroundColor": color}}},
                "index": i}})
        try:
            await asyncio.to_thread(
                lambda: self._svc.spreadsheets().batchUpdate(
                    spreadsheetId=self._sid, body={"requests": requests}
                ).execute()
            )
        except Exception:
            pass  # idempotent — formatarea poate exista deja

    async def _ensure_header(self, sheet: str, headers: list[str]) -> None:
        rows = await self.read(sheet, "A1:Z1")
        if not rows:
            await self.update_row(sheet, 1, headers)

    async def _ensure_params(self) -> None:
        rows = await self.read("Parametri", "A1:C100")
        if not rows:
            await self.update_row("Parametri", 1, ["Param", "Valoare", "Descriere"])
            for i, (k, v, d) in enumerate(PARAMETRI_DEFAULT, start=2):
                await self.update_row("Parametri", i, [k, v, d])


def fmt_date(dt: datetime | None = None) -> str:
    return (dt or datetime.now()).strftime("%d/%m/%Y")
