"""Sub-agent Telegram — voce + foto + text. Punct unic intrare. Claude Vision pentru OCR."""
from __future__ import annotations
import asyncio, base64, io, json, re
from anthropic import AsyncAnthropic
from PIL import Image
from . import config

_anthropic = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY) if config.ANTHROPIC_API_KEY else None


VOICE_PROMPT = """Transcrie acest mesaj vocal BTP în limba originalului (RO/FR/mixt).
Dicționar BTP activ: chantier, gros oeuvre, second oeuvre, conducteur de travaux, marché public.
Prioritate înțelegere context > transcriere literală. Filtrează zgomot. Returnează DOAR textul transcris, fără comentarii."""

VISION_PROMPT = """Analizează imaginea (panou chantier / carte vizită / vehicul marcat BTP).
Returnează STRICT un JSON valid cu structura:
{
  "type": "panneau" | "carte" | "vehicul",
  "firmes": [{"nom": "...", "siren": "...", "tel": "...", "metier": "...", "email": "..."}],
  "maitre_ouvrage": "...",
  "commentaires": "..."
}
Reguli:
- Maître d'ouvrage NICIODATĂ ca prospect — doar comentariu
- Corecție OCR evidentă: E1ectr1cite → Electricité
- NU scana QR codes
- Câmpuri lipsă = omise (nu null)
- Deduplicare firme
Returnează DOAR JSON-ul, fără markdown fără comentarii."""


def _compress_image(data: bytes, max_size: int = 720) -> bytes:
    img = Image.open(io.BytesIO(data))
    img.thumbnail((max_size, max_size))
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue()


async def transcribe_voice(ogg_bytes: bytes) -> str:
    """Transcriere via OpenAI Whisper (whisper-1). Necesită OPENAI_API_KEY."""
    import os, httpx
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return "[AUDIO_NEPROCESAT — setează OPENAI_API_KEY în .env]"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            files = {"file": ("voice.ogg", ogg_bytes, "audio/ogg")}
            data = {"model": "whisper-1", "language": "fr",
                    "prompt": "Vocabulaire BTP français/roumain: chantier, gros oeuvre, conducteur de travaux, marché public, SIREN, effectif."}
            r = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files=files, data=data,
            )
            if r.status_code != 200:
                return f"[STT_ERROR {r.status_code}]"
            return r.json().get("text", "").strip()
    except Exception as e:
        return f"[STT_EXC {e}]"


async def parse_image(jpeg_bytes: bytes) -> dict:
    if not _anthropic:
        return {"error": "ANTHROPIC_API_KEY absent"}
    compressed = _compress_image(jpeg_bytes)
    b64 = base64.standard_b64encode(compressed).decode()
    resp = await _anthropic.messages.create(
        model=config.CLAUDE_MODEL_FAST,
        max_tokens=1500,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": VISION_PROMPT},
            ],
        }],
    )
    text = resp.content[0].text.strip()
    # Strip markdown fence if present
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text, "error": "json_invalid"}


def route_text(text: str) -> dict:
    """Routing inițial pe baza textului. Default → Agent Principal."""
    t = text.strip().lower()
    if t.startswith("șterge ultimul") or t.startswith("sterge ultimul") or t == "undo":
        return {"signal": "undo"}
    m = re.match(r"sub-agent\s+(\w+)\s+(.*)", t)
    if m:
        return {"target": m.group(1), "payload": m.group(2)}
    return {"target": "principal", "payload": text}
