# SKILL — Sub-agent Piete v3.0

**Implementare:** `src/sub_agent_piete.py` + `src/piete_sources/` (11 module)

## Rol
Scanează 11 surse marchés publics franceze în paralel, filtrează BTP (CPV 45xxx+39xx) atribuite Grand Est, deduplică, returnează JSON la Agent Principal.

## Filtre globale
```python
CPV_BTP = ["45", "39"]
GRAND_EST_DEPT = ["08","10","51","52","54","55","57","67","68","88"]
PERIODE_JOURS = 90
TYPE_MARCHE = "attribué"
```

## Surse — 3 categorii

### Categoria A — API publice (prioritate maximă)
| # | Sursă | URL |
|---|---|---|
| 1 | BOAMP | boamp-datadila.opendatasoft.com API v2.1 |
| 2 | DECP | data.economie.gouv.fr decp-v3 |
| 10 | TED/JOUE | ted.europa.eu API v3 |

### Categoria B — HTML scraping
PLACE · France Marchés · Marchés Sécurisés · AWS · Maximilien · Région GE · La Centrale

### Categoria C — Cont opțional (skip dacă 401/403)
e-marchespublics.com

## Orchestrare
Toate 11 surse lansate în paralel (`asyncio.gather`). O sursă eșuată → skip silent, restul continuă. Timeout 60s/sursă.

## Deduplicare
Cheie: `(siren, montant, date_attrib)`. Conflict → prioritate: BOAMP > DECP > TED > restul.

## Consortium
Fiecare membru extras ca prospect separat.

## Cache
`data/piete_cache.json` · TTL 6h · `force=True` bypass.

## Scoring → Principal
≥3 marchés = +20 · 2 = +15 · 1 = +10 · 0 = neutru.

## Comenzi
```python
await run()                         # scan complet 90 zile
await run(siren="394905517")        # verificare SIREN specific
await run(jours=30, force=True)     # 30 zile, bypass cache
```
Telegram: `"Scanare marchés complet"` · `"Verifică marchés KELLER"`

## Test
```bash
python test_sub_agent_piete.py
```

## Output JSON
```json
{
  "scan_date": "2026-05-14",
  "periode_jours": 90,
  "surse_active": 9,
  "surse_eshuate": 2,
  "total_marches": 47,
  "nb": 47,
  "score_bonus": 20,
  "marches": [{"marche_id":"BOAMP-...","titre":"...","montant":450000,...}]
}
```

## Reguli inviolabile
Niciodată scrie în Sheets · surse eșuate = skip silent · doar atribuite · deduplicare obligatorie · Grand Est strict · CPV 45/39 · consortium = toți separat · cache 6h · apel paralel mereu.
