# Forme juridique — mapping INSEE → français

Source : codes INSEE (table `FORME_JURIDIQUE` dans `bot_telegram.py`).

| Code | Label français |
|---|---|
| 1000 | Entrepreneur individuel |
| 1100 | Artisan |
| 1200 | Exploitant agricole |
| 2110 | Indivision |
| 2120 | Société en participation |
| 2210 | Société en nom collectif (SNC) |
| 2220 | Société en commandite simple |
| 2310 | SARL |
| 2320 | SARL unipersonnelle (SUARL) |
| 2400 | Société par actions simplifiée (SAS) |
| 2430 | SAS unipersonnelle (SASU) |
| 5210 | Société anonyme |
| 5220 | SA avec conseil d'administration |
| 5221 | SA avec directoire |
| 5498 | EURL |
| 5499 | SARL |
| 5500 | Société civile |
| 5510 | Société civile immobilière (SCI) |
| 5530 | Société civile d'exploitation agricole |
| 5580 | Groupement d'intérêt économique (GIE) |
| 5710 | SAS |
| 5720 | SASU |

Codes inconnus → renvoyer le code brut sous forme de chaîne. **Jamais** laisser le chiffre nu en Excel — toujours convertir via `format_forme_juridique(code)`.
