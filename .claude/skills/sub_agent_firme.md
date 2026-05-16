# SKILL — Sub-agent Firme v3.0

**Implementare:** `src/sub_agent_firme.py`

## Rol
Colectare + validare date juridice/financiare BTP din SIREN/nume. Determină eligibilitate. JSON → Principal.

## Surse cascadă (stop la primul complet)
Pappers.fr (API) → Annuaire Entreprises (data.gouv) → INSEE Sirene → Société.com → Verif.com → BODACC → Pages Jaunes → Manageo → Score3 → Annuaire BTP. Google Maps + site firmă verificate mereu.

## Eligibilitate (cumulativ)
SIREN valid + NAF 41xx/42xx/43xx + effectif ≥ 5 + vechime ≥ 2 ani + siège Grand Est + forme ≠ auto/micro + CA ≥ 1M€ (sau flag `ca_non_communique`).

**Exclus silențios:** lichidare · redresare · holding · colectivitate · hors Grand Est · vechime/effectif sub prag · auto-entrepreneur · litigii grave.

## Output
`eligible:true` cu date complete, sau `{siren, eligible:false, exclusion_raison}`.

## Comunicări
→ Contacte (dirigeant) · ↔ Piete (SIREN) · → Principal (JSON).

## Performance
30s/firmă · batch 5 · cache 30 zile · Pappers down → retry ×3 → fallback Société.com · zero logging.

## Reguli inviolabile
Niciodată prospect fără SIREN valid · niciodată scrie în Sheets · excludere silențioasă · BTP strict · Grand Est exclusiv · dirigeant → mereu la Contacte.
