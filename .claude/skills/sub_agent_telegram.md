# SKILL — Sub-agent Telegram v3.0

**Implementare:** `src/sub_agent_telegram.py` · `src/main.py`

## Rol
Punct unic de intrare. Ascultă Telegram (voce/foto/text), procesează prin Claude Vision + Whisper, rutează la Agent Principal.

## Input
| Tip | Format | Procesare |
|---|---|---|
| Vocal | .ogg | Whisper STT (OpenAI) → text → routing |
| Foto | .jpg/.png | Claude Vision OCR → JSON → routing |
| Text | string | Routing direct la Principal |

## Procesare vocală
- Whisper-1, language=fr, prompt glosar BTP (chantier, gros oeuvre, conducteur de travaux, marché public)
- RO/FR/mixt fără clarificare · filtrare zgomot · audio șters imediat
- Telefon incomplet → cere doar cifrele lipsă (singura excepție de răspuns)

## Procesare foto (OCR)
- Redimensionare 720px + JPEG q85 înainte de trimitere
- Corecție OCR evidentă (E1ectr1cite → Electricité) · QR codes NU · zero stocare/EXIF
- Deduplicare multi-foto → o singură listă firme

## Output JSON
`panneau` / `carte` / `vehicul` — câmpuri lipsă omise. Maître d'ouvrage → `commentaires`, niciodată prospect.

## Routing
Default → Principal · "sub-agent X…" → direct X · "șterge ultimul" → UNDO.

## Reguli inviolabile
Vocal > OCR la contradicție · maître d'ouvrage ≠ prospect · tăcut total · audio/imagini = zero stocare.
