# ALL_SKILLS_v3.0 — ACTERIM SYSTÈME COMPLET
## 6 Agenți · BTP Grand Est · Claude Code / VS Code
## Fără n8n · Fără WhatsApp · Fără Agent Garanție · Fără Agent Scoring separat

---

## ARHITECTURA GLOBALĂ

```
NICOLAE
    ↕  Telegram Bot (voce / text / foto)
    ↕
Sub-agent Telegram ←→ Sub-agent Firme ←→ Sub-agent Contacte
        ↕                    ↕                    ↕
             AGENT PRINCIPAL (hub · orchestrator · analiză)
        ↕                    ↕                    ↕
Sub-agent Piete  ←→  ←→  ←→ ↕  ←→  ←→  ←→  ←→  ←→
                             ↕
                      GOOGLE SHEETS
                      (Prospecți · Tournées · Campanii · Parametri · Arhivă)
                             ↕
                      Sub-agent Teren
                      (Tournées · notificări relance)
```

**Reguli globale:**
- Toți agenții comunică bidirecțional — cu Principalul ȘI direct între ei
- Singurul care scrie în Google Sheets = Agent Principal
- Canal unic intrare = Telegram Bot
- Rulează ca procese Python din Claude Code sau VS Code terminal
- Zero n8n · Zero webhook extern · Zero WhatsApp · Zero cron extern
- SIREN = cheie unică — duplicate = SKIP
- Economie maximă tokens: câmpuri lipsă = omise din JSON (nu null explicit)
- Tăcut by default — confirmări doar la acțiuni distructive

---

## ZONE & FILTRE COMUNE

| Parametru | Valoare |
|---|---|
| Grand Est | 08, 10, 51, 52, 54, 55, 57, 67, 68, 88 |
| Excluse tournée | 52, 55, 10, 08 |
| BTP strict | NAF 41xx / 42xx / 43xx |
| CPV marchés | 45xxx + 39xx |
| Effectif minim | 5 |
| Vechime minimă | 2 ani |
| CA minim | 1M EUR sau flag ca_non_communique |

---

# SKILL — Sub-agent Telegram v3.0

## Rol
Punct unic de intrare în sistem. Ascultă permanent mesajele Telegram ale lui Nicolae, procesează voce și foto prin Claude Vision, rutează rezultatul la agentul corect. Rulează ca proces Python permanent.

## Pornire
```bash
python sub_agent_telegram.py
# sau
TELEGRAM_TOKEN=xxx ANTHROPIC_API_KEY=xxx python sub_agent_telegram.py
```

## Input acceptat
| Tip | Format Telegram | Procesare |
|---|---|---|
| Vocal | voice message (.ogg) | Transcriere Claude API → text → routing |
| Foto | photo / document (.jpg .png) | OCR Claude Vision → JSON → routing |
| Text | text message | Routing direct la Agent Principal |

## Procesare vocală
- Descarcă fișierul audio din Telegram (getFile API)
- Trimite la Claude API cu prompt transcriere specializat BTP
- Limbi acceptate: RO / FR / mixt — fără cerere clarificare
- Dicționar BTP activ: chantier, gros oeuvre, second oeuvre, conducteur de travaux, marché public
- Filtrare zgomot: mașină, șantier, exterior, voci secundare
- Prioritate: înțelegere context > transcriere literală
- Corecție auto: nume firmă greșit → fuzzy match în Sheets
- Comenzi multiple într-un mesaj → separă automat
- Telefon incomplet → cere DOAR cifrele lipsă (singura excepție de a răspunde)
- Audio șters imediat după transcriere (zero stocare)

## Procesare foto (OCR)
- Descarcă imaginea din Telegram
- Redimensionare 720px + compresie JPEG înainte de trimitere (economie tokens)
- Trimite la Claude Vision API
- Corecție OCR evidentă: E1ectr1cite → Electricité
- QR codes: NU scan (securitate + economie)
- Zero salvare imagine, zero EXIF
- Deduplicare multi-foto: N poze același șantier → o singură listă firme unică

## Output JSON panneau chantier
```json
{
  "type": "panneau",
  "firmes": [
    {"nom": "MULLER SAS", "siren": "123456789", "tel": "06 12 34 56 78", "metier": "Maçonnerie"}
  ],
  "maitre_ouvrage": "Ville de Strasbourg",
  "commentaires": "Adresse: 12 rue X. Durée: 18 mois"
}
```

## Output JSON carte vizită
```json
{
  "type": "carte",
  "firmes": [
    {"nom": "PETER Laurent", "fonction": "Gérant", "societe": "ELECTRICITE PETER",
     "tel": ["06 22 12 20 18"], "email": "l@peter-elec.fr", "siren": "394905517"}
  ]
}
```

## Output JSON vehicul marcat
```json
{
  "type": "vehicul",
  "firmes": [
    {"nom": "BTP ALSACE", "tel": "06 98 76 54 32", "site": "www.btp-alsace.fr", "metier": "Gros oeuvre"}
  ]
}
```

## Routing mesaje
| Condiție | Destinatar |
|---|---|
| Default (orice mesaj) | Agent Principal |
| Nicolae spune explicit "sub-agent X…" | Direct la sub-agent X (economie) |
| "șterge ultimul" | UNDO signal → Agent Principal |
| Audio total illizibil | Cere foto mai clară (singura situație de răspuns automat) |

## Reguli inviolabile
1. Vocal Nicolae > OCR în caz de contradicție
2. Maître d'ouvrage → câmp commentaires, niciodată prospect
3. Manuscris cu sumă în context garantie → câmp montant_garantie direct
4. Document Word fotografiat → brut la Agent Principal, fără parsare
5. Tăcut total — zero confirmări standard
6. Audio șters imediat după procesare
7. Zero stocare imagini

## Performance
| Parametru | Valoare |
|---|---|
| Timp max/imagine | 5 secunde |
| Timp max/audio | 10 secunde |
| Procesare | Secvențială FIFO |
| Stocare | Zero |

---

# SKILL — Sub-agent Firme v3.0

## Rol
Colectare și validare date juridice, financiare și structurale ale unei firme BTP pornind de la SIREN sau nume. Determină eligibilitatea. Returnează JSON la Agent Principal.

## Pornire (apel direct din Agent Principal)
```python
result = await sub_agent_firme.run(siren="394905517")
# sau
result = await sub_agent_firme.run(name="ELECTRICITE PETER")
```

## Surse cascadă (stop la primul care completează toate câmpurile)
1. **Pappers.fr** (API gratuit) — SIREN, CA, effectif, NAF, forme juridique, dirigeant, adresă
2. **Annuaire Entreprises** (data.gouv.fr) — validare SIREN, date INSEE
3. **INSEE Base Sirene** — SIRET, stabilimente secundare
4. **Société.com** — CA, bilanțuri dacă Pappers incomplet
5. **Verif.com** — scoring financiar, tendințe
6. **BODACC** — lichidare, redresare, radiere
7. **Pages Jaunes** — telefon, adresă, activitate vizibilă
8. **Manageo** — sinteză financiară rapidă
9. **Score3** — scoring și analiză risc
10. **Annuaire BTP** — confirmare activitate BTP, specialități

**Google Maps:** verificat întotdeauna — reviews recente = semnal activitate reală.
**Site web firmă:** verificat întotdeauna — proiecte, echipă, contact.

## Criterii eligibilitate (toate cumulativ)

**Inclus dacă:**
- SIREN valid + NAF 41xx/42xx/43xx
- Effectif ≥ 5
- Ancienneté ≥ 2 ani
- Siège Grand Est (08,10,51,52,54,55,57,67,68,88)
- Formă juridică ≠ auto-entrepreneur / micro-entreprise
- CA ≥ 1M EUR (sau flag ca_non_communique dacă nedeclarat)

**Exclus automat (silențios, fără alertă):**
- Lichidare judiciară sau radiere
- Redresare judiciară
- Holding-uri (chiar dacă filiale BTP)
- Colectivități publice
- Sediu în afara Grand Est
- Vechime < 2 ani
- Effectif < 5
- Auto-entrepreneur / micro-entreprise
- Datorii grave / litigii majore detectate

## Output JSON — firmă eligibilă
```json
{
  "siren": "394905517",
  "societe": "ELECTRICITE PETER SAS",
  "adresse": "8 Rue de la Mouée",
  "cp": "57070",
  "ville": "Metz",
  "dept": "57",
  "naf": "4321A",
  "forme": "SAS",
  "date_creation": "1993-06-15",
  "effectif": 35,
  "ca_annuel": 4200000,
  "dirigeant": "PETER Laurent",
  "site": "https://peter-elec.fr",
  "groupe": null,
  "tendance_ca": "hausse",
  "recrutement": true,
  "gmaps": true,
  "concurrent": null,
  "eligible": true,
  "flags": []
}
```

## Output JSON — firmă neeligibilă
```json
{"siren": "123456789", "eligible": false, "exclusion_raison": "liquidation"}
```

## Gestionare doublons
- SIREN deja în Sheets → actualizare date existente (nu duplicat)
- Același nume, SIREN diferit → două prospecte separate (SIREN = cheie unică)

## Comunicări directe
- → Sub-agent Contacte: trimite `dirigeant` ca punct de start imediat după eligibilitate confirmată
- ↔ Sub-agent Piete: validare SIREN în paralel
- → Agent Principal: JSON complet

## Performance
| Parametru | Valoare |
|---|---|
| Timp max/firmă | 30 secunde |
| Batch | 5 firme în paralel |
| Cache | 30 zile (nu re-interogă dacă date recente) |
| Pappers down | Retry ×3 → fallback Société.com |
| Logging | Zero |

## Reguli inviolabile
1. Niciodată prospect fără SIREN valid
2. Niciodată scrie în Google Sheets — tot prin Agent Principal
3. Excludere silențioasă — fără alertă, fără notificare
4. BTP strict — NAF 41xx/42xx/43xx numai
5. Grand Est exclusiv
6. Dirigeant → trimis întotdeauna la Sub-agent Contacte

---

# SKILL — Sub-agent Contacte v3.0

## Rol
Identificare și colectare contacte decizionale ale unei firme BTP. Prioritate absolută: portabilul dirigentului. Returnează JSON la Agent Principal.

## Pornire
```python
result = await sub_agent_contacte.run(siren="394905517", dirigeant="PETER Laurent")
```

## Surse (toate în paralel)
LinkedIn (site:search) · Pages Jaunes · Google Maps · Site oficial firmă · Annuaire Entreprises · Pappers · Société.com · Verif.com · Manageo · Facebook pages · Instagram bio · orice sursă publică relevantă

## Ierarhie contacte
- **Contact 1:** Gérant / DG — decideur principal, indiferent de mărimea firmei
- **Contact 2:** RH / Responsable personnel — co-decideur
- **Contact 3+:** Conducteur de travaux / Chef chantier / Chef équipe / Secrétariat — gate-keeper util în prospecție teren

Includem gate-keeperii — știut cum să treci de barieră este valoros pe teren.
Mai multe persoane cu aceeași funcție (ex: 3 conducteurs de travaux) → includem toate.

## Reguli date
| Situație | Acțiune |
|---|---|
| Telefon fix detectat | IGNORAT — doar portabil colectat |
| Email generic (contact@, info@) | Inclus ca email principal |
| Email inventat / dedus | INTERZIS — dacă absent = câmp omis |
| Contact fără portabil și fără email | Inclus cu coordonnees_manquantes: true |
| Profil LinkedIn privat | EXCLUS — date insuficiente |
| Portabil pe WhatsApp | Câmp wa: true |
| Vechi angajat | Inclus fără verificare (economie) |

## Output JSON
```json
{
  "siren": "394905517",
  "societe": "ELECTRICITE PETER SAS",
  "contacts": [
    {
      "nom": "PETER Laurent",
      "fonction": "Gérant",
      "tel": "06 22 12 20 18",
      "email": "l.peter@peter-elec.fr",
      "wa": true,
      "prio": 1
    },
    {
      "nom": "MULLER Pierre",
      "fonction": "Conducteur de travaux",
      "tel": "06 98 76 54 32",
      "wa": false,
      "prio": 2
    },
    {
      "nom": "KLEIN Marie",
      "fonction": "Secrétariat",
      "email": "contact@peter-elec.fr",
      "prio": 3,
      "coordonnees_manquantes": true
    }
  ],
  "nb_contacts": 3
}
```

## Output JSON — niciun contact găsit
```json
{
  "siren": "394905517",
  "contacts": [
    {"nom": "PETER Laurent", "fonction": "Dirigeant (sursa Firme)", "prio": 1, "coordonnees_manquantes": true}
  ],
  "flags": ["contacts_incomplets"]
}
```

## Comunicări directe
- ← Sub-agent Firme: primește `dirigeant` ca punct de start
- → Agent Principal: JSON complet

## Performance
| Parametru | Valoare |
|---|---|
| Timp max/firmă | 1 minut |
| Batch | 5 firme în paralel |
| Cache | Zero — date fresh întotdeauna |
| Logging | Zero |

## Prioritate absolută
**Portabilul dirigentului (Contact 1).** Dacă există, misiunea e reușită chiar dacă restul câmpurilor sunt goale.

## Reguli inviolabile
1. Niciodată scrie în Google Sheets
2. Niciodată genera email — absent = câmp omis
3. Strict profesional — zero date personale
4. Zero poze (RGPD)
5. Portabil > orice altceva
6. Profil LinkedIn privat = exclus
7. Contact eronat semnalat → Agent Principal gestionează ștergerea

---

# SKILL — Sub-agent Piete v3.0

## Rol
Detecție marchés publics BTP atribuite în Grand Est. Identifică firme active, validează activitate existentă, alimentează scoring-ul și planificarea tournées.

## Pornire
```python
# Scan complet (ultimele 90 zile):
result = await sub_agent_piete.run()

# Verificare SIREN specific:
result = await sub_agent_piete.run(siren="394905517")
```

## Surse (11, toate în paralel, filtru automat)
| Sursă | Filtru auto aplicat |
|---|---|
| BOAMP | CPV 45xxx/39xx + Grand Est |
| DECP | CPV 45xxx/39xx + Grand Est |
| PLACE (marchespublics.gouv.fr) | CPV 45xxx/39xx + Grand Est |
| France Marchés | CPV 45xxx/39xx + Grand Est |
| e-marchespublics.com | CPV 45xxx/39xx + Grand Est |
| Marchés Sécurisés | CPV 45xxx/39xx + Grand Est |
| AWS/marches-publics.info | CPV 45xxx/39xx + Grand Est |
| Maximilien | CPV 45xxx/39xx + Grand Est |
| Région Grand Est | CPV 45xxx/39xx + Grand Est |
| JOUE / TED Europa | CPV 45xxx/39xx + Grand Est |
| La Centrale des Marchés | CPV 45xxx/39xx + Grand Est |

Filtru aplicat automat la fiecare sursă: "Travaux BTP" + Grand Est (10 departamente). Zero efort manual.

## Perimetru
- Marchés private: NU
- Marchés atribuite: DA (firma a câștigat = activă, are nevoie de personal)
- Marchés în curs / apeluri deschise: NU
- Zonă: Grand Est strict
- Montant minim: zero — orice marché BTP contează

## Output JSON per marché
```json
{
  "marche_id": "BOAMP-2025-45123",
  "titre": "Rénovation école maternelle Strasbourg",
  "montant": 450000,
  "attributaire": "KELLER SAS",
  "siren": "394905517",
  "date_attrib": "2025-11-15",
  "lieu": "Strasbourg (67)",
  "duree_mois": 12,
  "source": "BOAMP",
  "cpv": "45210000",
  "consortium": [],
  "lots": [{"nom": "Gros oeuvre", "attrib": "KELLER SAS"}]
}
```

## Reguli includere/excludere
**Inclus dacă:**
- Marché atribuit (nu apel deschis)
- CPV 45xxx sau 39xx
- Loc execuție Grand Est
- Data atribuire în ultimele 90 zile

**Exclus imediat:**
- Marché anulat / reziliat
- Durată < 1 zi
- Extensie / aditional la contract existent

**Cazuri speciale:**
- Consortium → extrage fiecare membru ca prospect separat
- Lots multiple cu atributar diferit → prospect separat per lot
- SIREN absent → include normal, Sub-agent Firme verifică
- Deduplicare auto (BOAMP > DECP la date contradictorii)

## Scoring marchés → trimis direct la Agent Principal
| Marchés | Puncte |
|---|---|
| ≥ 3 | +20 |
| 2 | +15 |
| 1 | +10 |
| 0 | neutru (multe firme lucrează privat) |

## Comunicări directe
- ↔ Sub-agent Firme: validare SIREN (confirmare că firma există și e activă)
- → Sub-agent Teren: chantiere active în zonă pentru planificarea tournées
- → Agent Principal: JSON marchés + scoring

## Performance
| Parametru | Valoare |
|---|---|
| Timp max/scan complet | 5 minute |
| Perioadă acoperită | Ultimele 90 zile |
| Declanșare | La cerere Nicolae sau apel din Principal |
| Cache | Zero — date fresh |
| Sursă down | Continuă cu celelalte + retry ×3 |

## Reguli inviolabile
1. Niciodată scrie în Google Sheets
2. Doar marchés atribuite
3. Grand Est strict
4. Consortium = toți membrii separat
5. Marché anulat = exclus silențios
6. Deduplicare automată

---

# SKILL — Agent Principal v3.0

## Rol
Hub central al ecosistemului. Singurul agent în contact direct cu Nicolae prin Telegram. Singurul care scrie în Google Sheets. Orchestrează toți sub-agenții, calculează scoring, gestionează campanii, răspunde la interogări.

## Pornire
```bash
# Pornește tot sistemul (Principal + Telegram bot):
python main.py

# Sau individual din VS Code:
python agent_principal.py
```

## Google Sheets — structură completă

### Foi
| Foaie | Conținut | Cheie primară |
|---|---|---|
| **Prospecți** | Toate firmele BTP (20+ coloane) | SIREN |
| **Tournées** | Istoric tournées + feedback teren | ID + dată |
| **Campanii** | Tracking email / Telegram masiv | ID campanie |
| **Parametri** | Reguli scoring editabile direct de Nicolae | cheie |
| **Arhivă** | Prospecți eliminați (recuperabili) | SIREN |
| **Backup** | Snapshot automat zilnic 02:00 | dată |

### Coloane foaie Prospecți
```
SIREN | Société | Adresse | CP | Ville | Dept | NAF | Forme |
Effectif | Date_creation | Dirigeant | Site | Tel | Email | WhatsApp |
Score | Tier | Marchés | Source | Date_ajout | Date_contact |
Statut | Concurent | Recrutare | Flags | Notes
```

### Formate obligatorii
| Câmp | Format |
|---|---|
| Date | DD/MM/YYYY |
| Telefon | 06 XX XX XX XX |
| Score | 0-100 |
| Tier | High / Medium / Low |
| Sursă | Telegram / Firme / Piete / Manual |

### Codare vizuală automată
- High (71-100) → fundal verde
- Medium (31-70) → fundal galben
- Low (0-30) → fundal albastru deschis

## Orchestrare cascadă standard
```
Input (SIREN sau nume firmă)
    ↓
Sub-agent Firme → verifică eligibilitate
    ↓ dacă eligibil
Sub-agent Contacte ‖ Sub-agent Piete (paralel, fără așteptare reciprocă)
    ↓ când datele sosesc
Scoring intern → calculează scor 0-100
    ↓
Google Sheets → scrie rând nou sau actualizează
```

## Scoring intern (integrat în Principal, fără sub-agent dedicat)

### Grilă
| Factor | Tranșe | Puncte |
|---|---|---|
| Effectif | ≥50 / 20-49 / 10-19 / <10 | 20/15/10/5 |
| CA | ≥5M / 2-5M / 1-2M / 500K-1M / <500K | 20/15/10/5/0 |
| Marchés publics | ≥3 / 2 / 1 / 0 | 20/15/10/0 |
| Contact calificat | Complet(3/3) / Parțial(2/3) / Absent | 10/5/0 |

**Total max: 70 puncte** (scalat la 100 față de Parametri)

### Tier
- 0-30 → Low
- 31-70 → Medium
- 71-100 → High

### Excludere automată (score = 0, prospect eliminat)
- Effectif lipsă (imposibil evaluat)
- Litigiu public detectat
- Firmă < 2 ani

### Recalcul
- Instant la orice date noi primite
- Parametri editabili de Nicolae direct în foaia Parametri din Sheets

## Scriere în Sheets
- Directă, silențioasă, fără confirmare
- Date parțiale = scrie ce există
- Duplicate SIREN = SKIP (nu suprascrie)
- Concurență scrieri = queue FIFO
- Ștergere = mutare în Arhivă (excepție GDPR = ștergere definitivă)
- Conflict 2 sub-agenți = last-write-wins (timestamp)
- Sheets indisponibil = queue local + retry 2min + notificare după 10min

## Interpretare comenzi Nicolae (Telegram)
- Limbă: RO / FR / mixt — răspunde în limba mesajului
- Argou și scurtături: acceptate
- Cerere ambiguă: face presupunere rezonabilă, execută, notifică
- Memorie conversație: NU (economie) — fiecare mesaj e independent

## Interogare avansată Sheets (exemple reale)
```
"Dă-mi toți prospecții cu recrutare activă în 67"
"Listează High score fără contact telefon"
"Firme cu marchés recente + WhatsApp detectat"
"Prospecți necontactați de peste 30 zile"
"Arată-mi concurenți intérim detectați"
```
Output: listă numerotată compact în Telegram

## Campanii mass-messaging
1. Nicolae dă filtrul → Principal afișează numărul de destinatari
2. Confirmare Nicolae: Da / Nu
3. Trimitere personalizată (template + variabile din Sheets)
4. Log automat în foaia Campanii

**Constrângeri:**
- Max 50 mesaje/oră
- Pauze 30-60s random între mesaje
- Ore 9h-18h CET — zero noapte / weekend
- Canal: Email sau Telegram (nu WhatsApp direct)

## Notificări către Nicolae
✅ Notifică: marché public nou detectat · eroare scriere Sheets
❌ NU notifică: prospect adăugat · date lipsă · sub-agent lent · recap zilnic

## Comunicări directe inter-sub-agenți (ocolesc Principalul)
| De la | Către | Ce trimite |
|---|---|---|
| Sub-agent Firme | Sub-agent Contacte | dirigeant (punct de start) |
| Sub-agent Firme | Sub-agent Piete | SIREN (validare paralelă) |
| Sub-agent Piete | Sub-agent Teren | chantiere active în zonă |

## Securitate
- Acces exclusiv Nicolae
- Credențiale în .env (zero hardcodate)
- Date sensibile criptate la stocare
- Backup Sheets zilnic 02:00 (Google Apps Script sau API)
- Undo disponibil 24h (via Arhivă)

## Edge cases
| Situație | Acțiune |
|---|---|
| Sub-agent down | Continuă în degraded mode, retry silent |
| SIREN invalid | Validare via Pappers, returnează eroare clară |
| Date corupte | Reparare auto dacă posibil, altfel flag |
| Comandă imposibilă | Explică limita + propune alternativă |
| Volum mare (100+ firme) | Procesează tot secvențial, fără limită |
| OCR neclar | Acceptă cu flag ocr_incertain |

## Reguli inviolabile
1. Doar Nicolae inițiază acțiuni majore
2. Duplicate SIREN = SKIP întotdeauna
3. Confirmări obligatorii pentru acțiuni distructive
4. Ștergere = mutare Arhivă (excepție GDPR)
5. Notificări minime — silențios by default
6. Integritate date > orice altceva
7. Răspunde în limba mesajului lui Nicolae
8. Zero logging, zero cache intern
9. Credențiale din .env, niciodată hardcodate

---

# SKILL — Google Sheets v3.0

## Rol
Baza de date centrală. Sursă unică de adevăr pentru întregul sistem. Citită de toți agenții, scrisă exclusiv de Agent Principal.

## Acces
```python
# Prin Google Sheets API (service account)
# Credențiale în: credentials/google_service_account.json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
```

## Drepturi per agent
| Agent | Drepturi |
|---|---|
| Agent Principal | Citire + Scriere completă |
| Sub-agent Teren | Citire (selecție prospecți tournée) |
| Sub-agent Piete | Citire (verificare SIREN existent) |
| Sub-agent Firme | Citire (verificare duplicate) |
| Sub-agent Contacte | Zero acces direct |
| Sub-agent Telegram | Zero acces direct |

## Foaie Prospecți — schema completă
```
SIREN           | text     | cheie unică, 9 cifre
Société         | text     | raison sociale
Adresse         | text     | adresă sediu
CP              | text     | cod poștal
Ville           | text     | oraș
Dept            | text     | 2 cifre departament
NAF             | text     | cod NAF/APE
Forme           | text     | SAS/SARL/SA/etc
Effectif        | number   | nr. salariați
Date_creation   | date     | DD/MM/YYYY
Dirigeant       | text     | Prenume Nume
Site            | text     | URL site web
Tel             | text     | 06 XX XX XX XX
Email           | text     | email profesional
WhatsApp        | boolean  | true/false
Score           | number   | 0-100
Tier            | text     | High/Medium/Low
Marchés         | number   | nr. marchés publics atribuite
Source          | text     | Telegram/Firme/Piete/Manual
Date_ajout      | date     | DD/MM/YYYY
Date_contact    | date     | DD/MM/YYYY
Statut          | text     | Nouveau/Contacté/Callback/Interesat/Client/Exclus
Concurent       | text     | nume agenție interim sau gol
Recrutare       | boolean  | true/false
Flags           | text     | ca_non_communique / ocr_incertain / etc
Notes           | text     | observații libere
```

## Foaie Parametri (editabilă direct de Nicolae)
```
Param                | Valoare | Descriere
score_effectif_max   | 20      | Puncte max efectiv
score_ca_max         | 20      | Puncte max CA
score_marches_max    | 20      | Puncte max marchés
score_contact_max    | 10      | Puncte max contact
effectif_min         | 5       | Prag minim includere
ca_min               | 1000000 | CA minim (EUR)
vechime_min_ani      | 2       | Vechime minimă
rayon_tournee_km     | 30      | Raza tournée (km)
max_prospects_tournee| 8       | Max prospecți per tournée
min_prospects_tournee| 5       | Min prospecți per tournée
```

## Codare vizuală automată (Apps Script sau API)
```python
# High (71-100) → verde #d9ead3
# Medium (31-70) → galben #fff2cc
# Low (0-30) → albastru deschis #cfe2f3
```

---

# SKILL — Sub-agent Teren v3.0

## Rol
Planificarea și optimizarea tournées de prospecție. Selectează prospecți din Google Sheets, optimizează traseul geografic, livrează fișă completă per prospect + notificări relance automate. Declanșat exclusiv de Nicolae prin Telegram.

## Pornire
```python
# Apelat din Agent Principal la primirea comenzii:
result = await sub_agent_teren.run(ville="Strasbourg", n=6)
```

## Declanșare
Comandă Telegram Nicolae (vocal sau text). **Zero automatizare.** Nicolae decide când și unde.

**Exemple comenzi:**
- `"Fă-mi tournée pe Strasbourg"`
- `"Tournée joi pe Metz, 6 firme"`
- `"Relance callback-uri săptămâna asta"`
- `"Tournée urgentă Nancy, firme High score"`

## Selecție prospecți din Sheets
| Criteriu | Regulă |
|---|---|
| Scor minim | Niciun — toate tier-urile incluse |
| Contact obligatoriu | Nu |
| Deja vizitați | Incluși dacă > 60 zile de la ultima vizită |
| Recrutare activă | Prioritate egală cu tier High |
| Statut Exclus | NICIODATĂ inclus |
| Număr | 5-8 per tournée |
| Fallback < 5 prospecți | Extinde raza +10km până la minim 5 |

## Optimizare traseu
- **Punct plecare fix:** 43 rue d'Ostwald, Lingolsheim (67)
- **Rază default:** ville specificată de Nicolae + 30km
- **Algoritm:** nearest-neighbor (cel mai apropiat următor)
- **Mod:** mașină
- **Departamente excluse dintotdeauna:** 52, 55, 10, 08
- **Retur:** necalculat (Nicolae se întoarce singur)

## Fișă per prospect (format Google Doc)
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[N°] RAISON SOCIALE — [PROSPECT / CLIENT]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Adresă completă + link Google Maps
Score: XX/100 | Tier: High / Medium / Low
Métier: [NAF + activitate]

Contact 1: Nom — Fonction — tel — email — WA
Contact 2: Nom — Fonction — tel (dacă există)

Marchés recente: [titlu + montant + dată] sau "Aucun"
Concurent intérim: [nume agenție] sau "Non détecté"
Istoric contacte: [dată + rezultat] sau "Premier contact"
Flags: [ca_non_communique / recrutement_actif / etc]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Output livrat lui Nicolae
- 1 Google Doc per tournée (itinerar numerotat + fișe complete)
- Mesaj Telegram cu rezumat: nr. prospecți, zonă, distanță totală estimată, link Doc

## Notificări relance automate (citire Sheets)
Sub-agent Teren verifică Sheets la fiecare pornire și trimite Telegram Nicolae când:
- Prospect cu statut Callback și > 3 zile fără contact → alertă
- Prospect cu statut Interesat și > 7 zile fără urmărire → alertă
- Prospect vizitat > 60 zile → sugestie re-vizitare

## Feedback post-vizită Nicolae → Sheets (via Agent Principal)
| Mesaj Telegram | Acțiune în Sheets |
|---|---|
| `vizitat [firmă]` | Update dată vizită + statut Contacté |
| `callback [firmă]` | Statut Callback + dată |
| `nerelevant [firmă]` | Statut Exclus → mutare Arhivă |
| `interesat [firmă]` | Statut Interesat + recalcul scoring |
| `client [firmă]` | Statut Client + dată |

## Comunicări directe
- ← Sub-agent Piete: primește chantiere active în zonă (input pentru selecție)
- ↔ Google Sheets: citire prospecți / scriere feedback (prin Agent Principal)

## Performance
| Parametru | Valoare |
|---|---|
| Timp generare tournée | < 30 secunde |
| Timp generare Doc | < 60 secunde |
| Logging | Zero |

## Reguli inviolabile
1. Niciodată scrie direct în Sheets — prin Agent Principal
2. Nicolae decide întotdeauna — zero automation tournée
3. Departamente 52/55/10/08 = excluse absolut
4. Min 5 prospecți pentru a lansa tournée
5. Max 8 prospecți per tournée
6. Prospect Exclus = niciodată în tournée
7. Optimizare geografică obligatorie

---

## FLUX COMPLET — EXEMPLU REAL

```
1. Nicolae fotografiază panou chantier → trimite pe Telegram

2. Sub-agent Telegram:
   OCR → {"type":"panneau", "firmes":[{"nom":"KELLER SAS","siren":"394905517","metier":"maçonnerie"}]}
   → trimite la Agent Principal

3. Agent Principal primește JSON:
   → lansează Sub-agent Firme cu siren: 394905517

4. Sub-agent Firme (Pappers + cascade):
   → eligibil: 35 sal., CA 3.2M, Metz 57, SAS, NAF 4120A
   → trimite dirigeant "SCHMITT Marc" la Sub-agent Contacte
   → trimite SIREN la Sub-agent Piete (paralel)

5. Sub-agent Contacte (LinkedIn + Maps + site):
   → SCHMITT Marc, Gérant, 06 XX XX XX XX, wa: true, prio: 1
   → MULLER Jean, Conducteur travaux, 06 YY YY YY YY, prio: 2

6. Sub-agent Piete (BOAMP + DECP):
   → 2 marchés atribuite 2025, total 680K EUR, +15pt scoring

7. Agent Principal:
   → scoring: effectif(10) + CA(15) + marchés(15) + contact(10) = 50 → Medium
   → scrie în Google Sheets: rând nou, fundal galben
   → notifică Nicolae pe Telegram: "KELLER SAS adăugat — Score 50 Medium"

8. Sub-agent Teren (la prochaine tournée Metz):
   → KELLER SAS inclus automat în selecție
```

---

## COMENZI RAPIDE TELEGRAM

| Comandă | Acțiune |
|---|---|
| [foto panou / carte / vehicul] | OCR → prospect nou |
| [vocal] firmă X, Metz | Califică firma X |
| tournée Strasbourg | Generează tournée 67 + 30km |
| tournée Metz 6 firme | Tournée Metz cu exact 6 prospecți |
| relance azi | Lista callback-uri și interesat scadente |
| scor KELLER | Scoring detaliat firmă |
| listează High 67 | Filtrare Sheets High + departament 67 |
| campanie email High score | Lansează campanie email |
| șterge ultimul | UNDO ultima acțiune |

---

## STRUCTURA FIȘIERE CLAUDE CODE

```
.claude/
├── CLAUDE.md                      ← router principal (citit primul)
└── skills/
    ├── sub_agent_telegram.md      ← procesare voce + foto Telegram
    ├── sub_agent_firme.md         ← eligibilitate + date juridice
    ├── sub_agent_contacte.md      ← contacte decizionale
    ├── sub_agent_piete.md         ← marchés publics BTP
    ├── agent_principal.md         ← hub + Sheets + scoring + campanii
    └── sub_agent_teren.md         ← tournées + relance

src/
├── main.py                        ← pornește tot sistemul
├── agent_principal.py
├── sub_agent_telegram.py
├── sub_agent_firme.py
├── sub_agent_contacte.py
├── sub_agent_piete.py
├── sub_agent_teren.py
└── google_sheets.py               ← wrapper API Sheets

credentials/
├── google_service_account.json    ← acces Sheets
└── .env                           ← TELEGRAM_TOKEN, ANTHROPIC_API_KEY
```

---

## DIAGRAMA FINALĂ

```
NICOLAE
    ↕  Telegram Bot
    ↕
Sub-agent    ←→   Sub-agent   ←→   Sub-agent
Telegram           Firme             Contacte
    ↕                ↕                  ↕
         AGENT PRINCIPAL
         (hub · scoring · campanii)
    ↕                ↕                  ↕
Sub-agent  ←→  ←→  ←→ ↕  ←→  ←→  ←→  ←→
Piete                  ↕
                GOOGLE SHEETS
                (Prospecți · Tournées · Campanii)
                       ↕
                Sub-agent Teren
                (Tournées · Relance)
```

---

**Versiune:** v3.0
**Data:** 14.05.2026
**Eliminat față de v2:** n8n · WhatsApp · Agent Garanție · Agent Scoring separat · Agent Vocal separat (integrat în Sub-agent Telegram)
**Rulează din:** Claude Code · VS Code terminal · Python 3.10+
