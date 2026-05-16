# SKILL — Sub-agent Piete v3.0

**Implementare:** `src/sub_agent_piete.py`

## Rol
Detecție marchés publics BTP **atribuite** Grand Est. Alimentează scoring + tournées.

## Surse (paralel, filtru auto CPV 45xxx/39xx + Grand Est)
BOAMP (activ) · DECP · PLACE · France Marchés · e-marchespublics · Marchés Sécurisés · AWS · Maximilien · Région Grand Est · JOUE/TED · La Centrale.

## Perimetru
Doar marchés atribuite, ultimele 90 zile, Grand Est strict, montant minim zero. NU apeluri deschise, NU private, NU anulate.

## Cazuri speciale
Consortium → fiecare membru prospect separat · lots cu atributari diferiți → separat · SIREN absent → include (Firme verifică) · deduplicare auto (BOAMP > DECP).

## Scoring → Principal
≥3 = +20 · 2 = +15 · 1 = +10 · 0 = neutru.

## Comunicări
↔ Firme (SIREN) · → Teren (chantiere active) · → Principal (JSON + scoring).

## Performance
5min/scan complet · 90 zile · la cerere/apel Principal · zero cache · sursă down → continuă + retry ×3.

## Reguli inviolabile
Niciodată scrie în Sheets · doar atribuite · Grand Est strict · consortium = toți separat · anulat = exclus silențios · deduplicare auto.
