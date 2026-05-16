# Mapping Excel — 38 colonnes de la feuille « Prospects »

Fichier : `D:\MY CLAUDE\EXEL\outil_prospection_ACTERIM_v4_FINAL.xlsx`
Feuille : **Prospects** (PAS « Tableau de bord » qui est la feuille active par défaut).

| # | Nom colonne | Source dans la donnée extraite |
|---|---|---|
| 1 | Date_création | `today_str` (YYYY-MM-DD) |
| 2 | SIREN | `insee.siren` |
| 3 | Société | `data.societe` |
| 4 | Adresse | `data.adresse` |
| 5 | Code_postal | `data.code_postal` |
| 6 | Ville | `data.ville` |
| 7 | Département_code | dérivé du CP (2 premiers chiffres) |
| 8 | Département_label | DEPT_LABELS[code] |
| 9 | Zone_tournée | `None` (rempli manuellement) |
| 10 | Métier_cible | `NAF_TO_METIER[naf]` si dispo, sinon `"NAF XXXX — à qualifier"`, sinon vu sur la photo |
| 11 | Effectif | `insee.effectif_label` (libellé tranche INSEE) |
| 12 | CA_annuel | `insee.ca` (€ si publié, sinon `None`) |
| 13 | Code_NAF | `insee.naf` (sans point : `4321A` pas `43.21A`) |
| 14 | Forme_juridique | label français (voir `references/forme_juridique.md`) |
| 15 | Personne_contactée | `insee.dirigeant_nom` |
| 16 | Fonction | `insee.dirigeant_fonction` |
| 17 | Téléphone | `data.telephone` |
| 18 | Email | `data.email` |
| 19-21 | Contact_2_* | `None` |
| 22 | Source | `"Terrain"` |
| 23 | Statut | mot-clé légende (Visite/Offre/Contacté/RDV/Négo/Gagné/Perdu) — défaut `"Visite terrain"` |
| 24 | Priorité | mot-clé légende (Haute/Moyenne/Basse) — défaut `"Haute"` |
| 25-26 | Garantie | `None` |
| 27 | Score_qualification | `None` |
| 28-30 | Dates garantie | `None` |
| 31-32 | Besoin / Phrase_accroche | `None` |
| 33-34 | Lat / Long | `None` |
| 35 | Site_web | `data.site_web` |
| 36 | LinkedIn_URL | `None` |
| 37 | Dernier_contact | `today_str` |
| 38 | Nb_actions_total | `0` |

## Règles d'écriture

- Toujours ouvrir avec `openpyxl.load_workbook(EXCEL_PATH)` puis `wb["Prospects"]`.
- Toujours créer une copie horodatée dans `D:\MY CLAUDE\backup\` AVANT `wb.save()`.
- Ne pas écrire si Excel est ouvert dans une autre application (PermissionError [Errno 13]) — informer l'utilisateur de fermer le fichier.
- Détection doublon : clé (`societe.lower().strip()`, `siren`) OU téléphone normalisé (`only_digits`).
