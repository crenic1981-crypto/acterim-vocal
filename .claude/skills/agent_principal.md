# SKILL — Agent Principal v3.0

**Implementare:** `src/agent_principal.py` · `src/google_sheets.py` · `src/main.py`

## Rol
Hub central. Singurul în contact cu Nicolae (Telegram) și singurul care scrie în Sheets. Orchestrare, scoring, campanii, interogări.

## Foi Sheets
Prospecți (43 col, cheie SIREN) · Tournées · Actions · Scripts · Campanii · Parametri (editabil) · Arhivă · Backup.

## Orchestrare cascadă
Input → Firme (eligibilitate) → Contacte ‖ Piete (paralel) → scoring 0-100 → Sheets (append/skip).

## Scoring (max raw 70 → scalat 100)
Effectif ≥50/20-49/10-19/≥5 = 20/15/10/5 · CA ≥5M/2-5M/1-2M/500K = 20/15/10/5 · marchés ≥3/2/1 = 20/15/10 · contact 3/3·2/3 = 10/5.
Tier: 0-30 Low · 31-70 Medium · 71-100 High. Codare vizuală auto (verde/galben/albastru) via conditional formatting.

## Scriere Sheets
Directă, silențioasă · date parțiale OK · duplicate SIREN = SKIP · ștergere = Arhivă (GDPR = definitiv) · conflict = last-write-wins.

## Comenzi Nicolae
tournée [ville] · relance · scor X · listează [Tier/Dept] · feedback teren (vizitat/callback/interesat/client/nerelevant) · șterge ultimul. RO/FR/mixt, fără memorie conversație.

## Campanii
Filtru → nr destinatari → confirmare → trimitere personalizată · max 50/oră · pauze 30-60s · 9h-18h CET · log Campanii.

## Notificări
✅ marché nou · eroare Sheets. ❌ prospect adăugat · date lipsă · agent lent.

## Reguli inviolabile
Doar Nicolae acțiuni majore · duplicate SIREN = SKIP · confirmare la distructiv · ștergere = Arhivă · silențios by default · zero logging/cache · credențiale .env.
