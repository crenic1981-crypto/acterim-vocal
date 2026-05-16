# SKILL — Sub-agent Piete v3.2

**Implementare:** `src/sub_agent_piete.py` + `src/piete_sources/` (11 module)

## Rol
**Reactiv** — nu face scan proactiv. Primit SIREN + societe de la Sub-agent Firme, caută șantierele active ale firmei în 11 surse. Firma NU e exclusă dacă rezultatul e zero.

## Entry point principal

```python
result = await sub_agent_piete.check_company(siren="394905517", societe="KELLER SAS")
```

## Criteriu "șantier activ"
- Marché atribuit firmei
- Data atribuirii ≥ 3 luni în urmă
- Șantierul încă în curs (date_attrib + duree > azi)
- Durată necunoscută → prezumăm 12 luni

## Output

```json
{
  "siren": "394905517",
  "societe": "KELLER SAS",
  "santiere_active": [{"marche_id":"...","titre":"...","luni_pe_santier":"17 / 24",...}],
  "nb_santiere_active": 1,
  "luni_pe_santier_max": "17 / 24",
  "scan_date": "2026-05-14",
  "surse_consultate": 11,
  "surse_eshuate": 2
}
```
Firma fără șantiere → `nb_santiere_active: 0`, `luni_pe_santier_max: "0 / 0"` → rămâne prospect activ.

## Surse (11, paralele)

**Categoria A (API, ~85% acoperire):**
- BOAMP — search by titulaire (nom société)
- DECP — search by `titulaire_id LIKE siren%` (cel mai precis)
- TED Europa — search by SIREN sau nom

**Categoria B (HTML scraping):**
PLACE · France Marchés · Marchés Sécurisés · AWS · Maximilien · Région GE · La Centrale

**Categoria C (skip dacă 401/403):**
e-marchespublics.com

## Filtre
```python
CPV_BTP = ["45", "39"]
GRAND_EST_DEPT = ["08","10","51","52","54","55","57","67","68","88"]
PERIODE_RECHERCHE_JOURS = 365
MIN_LUNI_PE_SANTIER = 3
```

## Integrare Agent Principal

```python
piete_res = await sub_agent_piete.check_company(siren=siren, societe=societe)
# Columns Sheets: Santiere_active + Luni_pe_santier
```

## Mode scan global (backward compat)

```python
result = await scan_all_sources(jours=90, force=True)
```

## Cache
Dezactivat by default (fresh la fiecare apel). Mode scan: cache 6h.

## Performance
15-60s/firmă · batch 5 paralel · timeout 60s/firmă · skip silent la eșec.

## Comenzi Telegram
```
"Verifică șantiere KELLER"        → check_company din Sheets
"Șantiere active 394905517"       → check_company direct SIREN
"Re-verifică toți High score"     → loop pe High → check_company
```

## Test
```bash
python test_sub_agent_piete.py
```

## Reguli inviolabile
Reactiv (nu scan automat) · firma NU e exclusă dacă zero șantiere · niciodată scrie în Sheets · apel paralel · skip silent la eșec · deduplicare DECP > BOAMP > TED.
