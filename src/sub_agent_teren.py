"""Sub-agent Teren — planificare tournées + relance. Citește Sheets, returnează plan."""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any
from . import config
from .google_sheets import SheetsClient


def _parse_score(s: str) -> int:
    try:
        return int(s)
    except (TypeError, ValueError):
        return 0


def _parse_date(s: str) -> datetime | None:
    if not s:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


async def select_for_tournee(sheets: SheetsClient, ville: str, n: int = 6) -> list[dict]:
    prospects = await sheets.all_prospects()
    today = datetime.now()
    candidates = []
    for p in prospects:
        if p.get("Statut") == "Exclus":
            continue
        dept = (p.get("Dept") or "").zfill(2)
        if dept in config.DEPT_EXCLUS_TOURNEE:
            continue
        v = (p.get("Ville") or "").lower()
        if ville and ville.lower() not in v:
            continue
        last_visit = _parse_date(p.get("Date_contact", ""))
        if last_visit and (today - last_visit).days < 60:
            continue
        candidates.append(p)
    candidates.sort(key=lambda p: (
        -1 if p.get("Recrutare", "").lower() in ("true", "1", "oui") else 0,
        -_parse_score(p.get("Score", "0")),
    ))
    n = max(config.MIN_PROSPECTS_TOURNEE, min(n, config.MAX_PROSPECTS_TOURNEE))
    return candidates[:n]


def format_tournee_doc(prospects: list[dict], ville: str) -> str:
    lines = [
        f"TOURNÉE — {ville} — {datetime.now().strftime('%d/%m/%Y')}",
        f"Départ : {config.POINT_DEPART}",
        f"Nombre prospects : {len(prospects)}",
        "",
    ]
    for i, p in enumerate(prospects, start=1):
        statut = "CLIENT" if p.get("Statut") == "Client" else "PROSPECT"
        lines.extend([
            "━" * 50,
            f"[{i}] {p.get('Société','?')} — {statut}",
            "━" * 50,
            f"{p.get('Adresse','')}, {p.get('CP','')} {p.get('Ville','')}",
            f"Score: {p.get('Score','0')}/100 | Tier: {p.get('Tier','?')}",
            f"Métier (NAF): {p.get('NAF','?')}",
            f"Contact: {p.get('Dirigeant','?')} — {p.get('Tel','')} — {p.get('Email','')}",
            f"WhatsApp: {p.get('WhatsApp','?')}  |  Recrutement: {p.get('Recrutare','non')}",
            f"Concurent: {p.get('Concurent','aucun')}",
            f"Notes: {p.get('Notes','')}",
            "",
        ])
    return "\n".join(lines)


async def relance_alerts(sheets: SheetsClient) -> list[str]:
    out: list[str] = []
    today = datetime.now()
    for p in await sheets.all_prospects():
        statut = p.get("Statut", "")
        last = _parse_date(p.get("Date_contact", ""))
        if not last:
            continue
        days = (today - last).days
        if statut == "Callback" and days > 3:
            out.append(f"⏰ Callback en retard ({days}j) — {p.get('Société','?')}")
        elif statut == "Interesat" and days > 7:
            out.append(f"🔥 Intéressé sans suivi ({days}j) — {p.get('Société','?')}")
        elif statut == "Contacté" and days > 60:
            out.append(f"🔁 Revisite suggérée ({days}j) — {p.get('Société','?')}")
    return out


async def run(ville: str, n: int = 6) -> dict[str, Any]:
    sheets = SheetsClient()
    prospects = await select_for_tournee(sheets, ville, n)
    doc = format_tournee_doc(prospects, ville)
    return {
        "ville": ville,
        "nb": len(prospects),
        "prospects": prospects,
        "doc": doc,
    }
