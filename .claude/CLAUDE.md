# ACTERIM BTP — Router principal v3.0

Sistem 6 agenți Python · BTP Grand Est · Travail temporaire.

## Reguli absolute
- Execuție autonomă, fără confirmare (excepție: distructive)
- Limba mesajului (RO / FR / mixt)
- Zero logging, zero cache (excepție: Firme 30 zile)
- Câmpuri lipsă = omise din JSON (nu null)
- SIREN = cheie unică, duplicate = SKIP

## Arhitectură
- `src/main.py` — entry point (Telegram polling + Principal)
- `src/agent_principal.py` — hub, scoring, Sheets writer
- `src/sub_agent_telegram.py` — OCR Claude Vision + routing
- `src/sub_agent_firme.py` — Pappers/Annuaire/INSEE cascadă
- `src/sub_agent_contacte.py` — extragere contacte site + sociale
- `src/sub_agent_piete.py` — BOAMP marchés BTP Grand Est
- `src/sub_agent_teren.py` — selecție tournée + relance alerts
- `src/google_sheets.py` — wrapper API Sheets

## Filtre
- Grand Est: 08,10,51,52,54,55,57,67,68,88
- BTP: NAF 41xx/42xx/43xx
- CPV marchés: 45xxx + 39xx
- Effectif ≥ 5, vechime ≥ 2 ani, CA ≥ 1M€
- Excluse tournée: 52,55,10,08

## Skills detaliate
Vezi `.claude/skills/*.md`.
