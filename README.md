# ACTERIM BTP — Sistem agenți v3.0

Prospectare automatizată BTP Grand Est. 6 sub-agenți Python coordonați de un hub central. Intrare exclusivă: Telegram. Bază de date: Google Sheets.

## Pornire rapidă

```bash
cd acterim-btp
python -m venv .venv
.venv\Scripts\activate           # Windows
pip install -r requirements.txt

# Completează credentials/.env și credentials/google_service_account.json
copy credentials\.env.example credentials\.env

python src/main.py
```

## Arhitectură

```
Nicolae ─ Telegram
            │
       Sub-agent Telegram (voce/foto/text)
            │
       AGENT PRINCIPAL ──── Google Sheets
       /     │     \
    Firme  Contacte  Piete  Teren
```

- **Singurul care scrie în Sheets:** Agent Principal
- **SIREN = cheie unică**, duplicate = SKIP
- **Zero logging**, zero cache (excepție: Firme 30 zile)
- **Tăcut by default**, confirmări doar la acțiuni distructive

## Variabile mediu (`credentials/.env`)

```
TELEGRAM_TOKEN=...
ANTHROPIC_API_KEY=...
PAPPERS_API_KEY=...
GOOGLE_SHEET_ID=...
TELEGRAM_USER_ID=...          # ID-ul lui Nicolae, restul ignorați
```

## Filtre globale

- Grand Est: 08, 10, 51, 52, 54, 55, 57, 67, 68, 88
- BTP strict: NAF 41xx / 42xx / 43xx
- Effectif ≥ 5, vechime ≥ 2 ani, CA ≥ 1M€ (sau flag `ca_non_communique`)
- Excluse tournée: 52, 55, 10, 08

## Comenzi Telegram

| Comandă | Acțiune |
|---|---|
| [foto panou / carte] | OCR → prospect nou |
| `tournée Strasbourg` | Tournée 67 + 30km |
| `scor KELLER` | Scoring detaliat |
| `listează High 67` | Filtrare Sheets |
| `relance azi` | Callback-uri scadente |
| `șterge ultimul` | UNDO |

Versiune: v3.0 · Data: 14.05.2026
