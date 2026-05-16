---
name: agent-photo-acterim
description: Pipeline complet ACTERIM (agence d'intérim BTP) pour traiter les photos de panneaux de chantier, camions, véhicules pro ou listes imprimées d'entreprises de bâtiment — ET maintenir/faire évoluer le bot Telegram associé (D:\MY CLAUDE\agent_photo\bot_telegram.py). Utilise ce skill DÈS QUE l'utilisateur (a) envoie ou mentionne une photo de chantier/camion/panneau BTP/note manuscrite à analyser, (b) demande d'ajouter des prospects dans le fichier Excel ACTERIM (outil_prospection_ACTERIM_v4_FINAL.xlsx), (c) parle du bot Telegram photo, des filtres NAF, de l'enrichissement INSEE, ou de la qualification des entreprises bâtiment. À utiliser même si l'utilisateur ne nomme pas explicitement « ACTERIM » ou « bot photo » — toute mention de panneau de chantier + extraction d'entreprises doit déclencher ce skill.
---

# Agent Photo ACTERIM — Skill complet

## Contexte métier

ACTERIM est une agence d'intérim BTP. La cible commerciale = **entreprises qui exécutent physiquement des travaux de bâtiment** (finition, installation, second œuvre, gros œuvre bâtiment) — celles qui ont besoin de main-d'œuvre intérimaire.

Le pipeline complet est implémenté dans `D:\MY CLAUDE\agent_photo\bot_telegram.py`. Ce skill couvre deux usages :

1. **Traitement d'une photo** (mode opérationnel) — extraire les entreprises, enrichir INSEE, filtrer, ajouter en Excel.
2. **Maintenance du bot** (mode développeur) — modifier filtres NAF, mapping métiers, prompt d'extraction, structure Excel, etc.

## Fichiers clés du projet

| Fichier | Rôle |
|---|---|
| `D:\MY CLAUDE\agent_photo\bot_telegram.py` | Bot Telegram principal (handlers, filtres, INSEE, Excel) |
| `D:\MY CLAUDE\agent_photo\config.env` | Clés API (Anthropic, Telegram token, allowed users) |
| `D:\MY CLAUDE\agent_photo\reprocess_excel.py` | Re-traitement du fichier Excel avec les filtres courants |
| `D:\MY CLAUDE\EXEL\outil_prospection_ACTERIM_v4_FINAL.xlsx` | Base prospects (feuille « Prospects », 38 colonnes) |
| `D:\MY CLAUDE\backup\` | Sauvegardes horodatées avant écriture |
| `D:\MY CLAUDE\Lancer_Bot_Telegram.bat` | Lanceur Windows |

## Mode 1 — Traiter une photo

### Étape 1 : Extraction par Claude Vision

Quand une photo est fournie (ou un document imprimé), extrais les entreprises **uniquement bâtiment finition/installation/second œuvre/gros œuvre**. La liste exhaustive des inclusions et exclusions est dans [references/extraction_prompt.md](references/extraction_prompt.md) — lis ce fichier avant toute extraction.

Réponds **uniquement** par un tableau JSON valide (sans markdown, sans explication) :

```json
[
  {
    "societe": "NOM ENTREPRISE",
    "telephone": "0X XX XX XX XX ou null",
    "email": "email@ex.com ou null",
    "site_web": "www.ex.com ou null",
    "adresse": "12 rue exemple ou null",
    "code_postal": "57000 ou null",
    "ville": "METZ ou null",
    "metier": "Électricité / Plomberie / Maçonnerie… ou null"
  }
]
```

**Ne jamais écrire « Autre BTP »** — si tu hésites sur le métier, mets `null` (l'enrichissement INSEE le remplira via le NAF).

### Étape 2 : Enrichissement INSEE

Pour chaque entreprise extraite, appelle l'API publique `https://recherche-entreprises.api.gouv.fr/search?q=<nom>&code_postal=<cp>&per_page=1`. Récupère :

- `siren`, `naf` (sans point), `effectif_code` + `effectif_label`, `date_creation`, `etat_administratif`
- `forme_juridique_code` → label français via la table [references/forme_juridique.md](references/forme_juridique.md)
- Dirigeant principal (nom + fonction)
- `chiffre_affaires` (dernière année publiée si dispo)

### Étape 3 : Qualification (filtres ACTERIM)

Applique les filtres dans l'ordre — détails dans [references/naf_filtering.md](references/naf_filtering.md) :

1. **État** = `A` (actif). Sinon → rejet.
2. **Préfixes NAF exclus** : `16` (bois), `23` (matériaux), `25` (métallurgie), `42` (TP/génie civil), `431` (démo/terrassement), `71` (architectes), `81` (paysage).
3. **Codes NAF exclus** : `4321B` (électricité voie publique), `4332C` (agencement), `4399E` (location matériel).
4. **NAF cible** : doit appartenir à la liste blanche (19 codes bâtiment).
5. **Âge** ≥ 5 ans depuis `date_creation`.
6. **Effectif** : codes INSEE `11` (10-19) ou `12` (20-49). `NN` (inconnu) accepté.
7. **CA** ≥ 1 M€ **si publié** (CA absent ou 0 → accepté).

Renvoie `(True, "Cible valide")` ou `(False, "raison précise")` pour log.

### Étape 4 : Doublons + écriture Excel

- **Doublons** : clé (`societe_lower`, `siren`) OU téléphone normalisé.
- **Backup horodaté** dans `D:\MY CLAUDE\backup\` AVANT toute écriture.
- **Mapping des 38 colonnes** : voir [references/excel_mapping.md](references/excel_mapping.md).
- Feuille cible : **« Prospects »** (pas « Tableau de bord »).

### Étape 5 : Réponse Telegram

**Pas de Markdown** (caractères `&`, `_`, `(` cassent le parseur Telegram). Texte brut uniquement. Format :

```
✅ N entreprise(s) ajoutée(s)
1. NOM | TÉL
   Métier (NAF XXXX) | Ville (Dept)
   SIREN XXX | Effectif X | CA X€
   Dirigeant : NOM
⚠️ N doublon(s) ignoré(s) : ...
🔍 N entreprise(s) filtrée(s)
💾 Backup : nom_fichier
```

Tronquer à 4000 caractères si dépassement (limite Telegram 4096).

## Mode 2 — Maintenir le bot

### Modifications fréquentes

| Besoin | Où intervenir |
|---|---|
| Ajouter/retirer un code NAF cible | `NAF_CIBLE` dans `bot_telegram.py` + même variable dans `reprocess_excel.py` |
| Changer la tranche d'effectif acceptée | `EFFECTIF_ACCEPTE` (codes INSEE `01`–`53`, table dans [references/effectif_codes.md](references/effectif_codes.md)) |
| Ajuster le prompt d'extraction | `EXTRACT_PROMPT` (toujours préserver la consigne « jamais Autre BTP ») |
| Ajouter un utilisateur Telegram autorisé | `config.env` → `TELEGRAM_ALLOWED_USERS` (CSV d'IDs) |
| Modifier le mapping métier NAF→français | `NAF_TO_METIER` |
| Changer la cible Excel | constante `EXCEL_PATH` |

### Règles non-négociables

- **Backups systématiques** : tout script qui écrit dans Excel crée d'abord une copie horodatée dans `D:\MY CLAUDE\backup\`. Pas de raccourci.
- **Jamais « Autre BTP »** dans aucun champ visible — préférer « NAF XXXX — à qualifier » si le code n'est pas dans la table métier.
- **Réponses Telegram en texte brut** — pas de `parse_mode="Markdown"`.
- **Garder `NAF_CIBLE` synchronisée** entre `bot_telegram.py` et `reprocess_excel.py`. Une divergence = entreprises supprimées par erreur.
- **Tester sur photo réelle** après toute modification de prompt ou de filtres — la photo de test type contient 10+ entreprises Metz/Moyenmoutier dans `D:\MY CLAUDE\agent_photo\` (si présente).

### Quand l'utilisateur demande un comportement nouveau

Avant de coder : vérifie si le besoin est déjà couvert par les filtres existants. Lis les fichiers ci-dessus. Si le changement touche `NAF_CIBLE` ou `EFFECTIF_ACCEPTE`, propose de re-traiter l'Excel existant (`reprocess_excel.py`) pour rester cohérent.

## Sécurité

- Le bot accepte uniquement les utilisateurs listés dans `TELEGRAM_ALLOWED_USERS`. Ne jamais publier le token Telegram ni la clé Anthropic dans des fichiers versionnés.
- L'API `recherche-entreprises.api.gouv.fr` est publique et gratuite — pas de quotas stricts mais 5s de timeout côté bot.
