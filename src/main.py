"""Punct de intrare unic. Pornește bot Telegram + Agent Principal."""
from __future__ import annotations
import asyncio, io, re
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters
from . import config
from .agent_principal import Principal
from . import sub_agent_telegram

SIREN_RE = re.compile(r"\b(\d{9})\b")


def _authorized(update: Update) -> bool:
    if not config.TELEGRAM_USER_ID:
        return True  # dev mode
    return update.effective_user and update.effective_user.id == config.TELEGRAM_USER_ID


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    await update.message.reply_text(
        "ACTERIM v3.0 prêt.\n"
        "Foto panou / carte / vehicul → prospect nou.\n"
        "Comenzi: tournée [ville], relance, scor [firmă], listează [filtru], șterge ultimul."
    )


async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    principal: Principal = ctx.application.bot_data["principal"]
    photo = update.message.photo[-1]
    f = await photo.get_file()
    buf = io.BytesIO()
    await f.download_to_memory(buf)
    payload = await sub_agent_telegram.parse_image(buf.getvalue())
    if "error" in payload:
        await update.message.reply_text(f"OCR échec: {payload.get('error')}")
        return
    results = await principal.process_telegram_payload(payload)
    summary = []
    for r in results:
        if r.get("status") == "added":
            summary.append(f"✅ {r['societe']} — Score {r['score']} {r['tier']}")
        elif r.get("status") == "non_eligible":
            summary.append(f"❌ {r.get('siren','?')} — {r.get('raison')}")
        elif r.get("status") == "skip_duplicate":
            summary.append(f"↩ {r['siren']} déjà présent")
        elif r.get("status") == "siren_manquant":
            summary.append(f"⚠ {r.get('nom','?')} — SIREN manquant")
    await update.message.reply_text("\n".join(summary) or "Aucune firme exploitable.")


async def handle_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    voice = update.message.voice
    f = await voice.get_file()
    buf = io.BytesIO()
    await f.download_to_memory(buf)
    text = await sub_agent_telegram.transcribe_voice(buf.getvalue())
    if text.startswith("[AUDIO_NEPROCESAT") or text.startswith("[STT_"):
        await update.message.reply_text(text)
        return
    update.message.text = text
    await handle_text(update, ctx)


async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return
    principal: Principal = ctx.application.bot_data["principal"]
    text = (update.message.text or "").strip()
    low = text.lower()

    # UNDO
    if low in ("șterge ultimul", "sterge ultimul", "undo"):
        r = await principal.undo_last()
        await update.message.reply_text(f"UNDO: {r.get('status')}")
        return

    # Tournée
    m = re.match(r"tourn[ée]+\s+([\w\-\s]+?)(?:\s+(\d+)\s*firme[s]?)?$", low)
    if m:
        ville = m.group(1).strip().title()
        n = int(m.group(2)) if m.group(2) else 6
        res = await principal.tournee(ville, n)
        await update.message.reply_text(
            f"Tournée {ville}: {res['nb']} prospects.\n\n{res['doc'][:3500]}"
        )
        return

    # Relance
    if low.startswith("relance"):
        alerts = await principal.relance()
        await update.message.reply_text("\n".join(alerts) or "Aucune relance scadentă.")
        return

    # Feedback terrain
    for action in ("vizitat", "callback", "interesat", "client", "nerelevant"):
        if low.startswith(action + " "):
            societe = text[len(action) + 1:].strip()
            r = await principal.feedback_terrain(action, societe)
            await update.message.reply_text(f"{action} → {r.get('status')} ({r.get('siren','')})")
            return

    # Scor
    m = re.match(r"scor\s+(.+)", low)
    if m:
        q = m.group(1).strip()
        rows = await principal.query({"Société": q})
        if not rows:
            await update.message.reply_text("Negăsit.")
            return
        r = rows[0]
        await update.message.reply_text(
            f"{r['Société']} — Score {r['Score']}/{r['Tier']}\n"
            f"Effectif {r['Effectif']} · CA: {r.get('Notes','')} · Marchés {r['Marchés']}\n"
            f"Contact: {r['Dirigeant']} {r['Tel']} {r['Email']}"
        )
        return

    # Listează
    m = re.match(r"list[eé]az[aă]\s+(.+)", low)
    if m:
        parts = m.group(1).split()
        filt = {}
        for p in parts:
            if p.title() in ("High", "Medium", "Low"):
                filt["Tier"] = p.title()
            elif p.isdigit() and len(p) == 2:
                filt["Dept"] = p
        rows = await principal.query(filt)
        msg = "\n".join(f"{i+1}. {r['Société']} ({r['Ville']}) — {r['Tier']}" for i, r in enumerate(rows[:30]))
        await update.message.reply_text(msg or "Niciun rezultat.")
        return

    # SIREN direct
    m = SIREN_RE.search(text)
    if m:
        r = await principal.process_siren(m.group(1), source="Telegram")
        await update.message.reply_text(json_summary(r))
        return

    await update.message.reply_text("Comandă nerecunoscută. Trimite foto, SIREN, sau 'tournée [oraș]'.")


def json_summary(r: dict) -> str:
    if r.get("status") == "added":
        return f"✅ {r['societe']} ajouté — Score {r['score']} {r['tier']} — {r['nb_marches']} marchés"
    if r.get("status") == "non_eligible":
        return f"❌ {r['siren']} non éligible: {r.get('raison')}"
    if r.get("status") == "skip_duplicate":
        return f"↩ {r['siren']} déjà dans Sheets"
    return str(r)


async def _async_main():
    principal = Principal()
    await principal.setup()
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()
    app.bot_data["principal"] = principal
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("ACTERIM v3.0 — bot pornit.")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


def main():
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
