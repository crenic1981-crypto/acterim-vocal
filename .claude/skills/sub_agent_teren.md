# SKILL — Sub-agent Teren v3.0

**Implementare:** `src/sub_agent_teren.py`

## Rol
Planificare + optimizare tournées prospecție + notificări relance. Declanșat exclusiv de Nicolae via Telegram.

## Selecție prospecți
Niciun scor minim · vizitați incluși dacă > 60 zile · recrutare activă = prioritate High · statut Exclus NICIODATĂ · 5-8/tournée · fallback < 5 → rază +10km.

## Optimizare traseu
Plecare fixă: 43 rue d'Ostwald, Lingolsheim (67) · rază ville + 30km · nearest-neighbor · mașină · excluse 52/55/10/08 · retur necalculat.

## Fișă per prospect
Raison sociale, adresă+Maps, Score/Tier, métier, Contact 1/2, marchés recente, concurent intérim, istoric, flags.

## Output
1 Google Doc/tournée + mesaj Telegram (nr prospecți, zonă, distanță, link).

## Relance automate (citire Sheets la pornire)
Callback > 3 zile fără contact → alertă · Interesat > 7 zile → alertă · vizitat > 60 zile → sugestie re-vizitare.

## Feedback teren → Sheets (via Principal)
vizitat → Contacté · callback → Callback · nerelevant → Exclus/Arhivă · interesat → Interesat+recalcul · client → Client.

## Reguli inviolabile
Niciodată scrie direct în Sheets · Nicolae decide mereu (zero automation) · 52/55/10/08 excluse absolut · min 5 / max 8 · Exclus = niciodată · optimizare geografică obligatorie.
