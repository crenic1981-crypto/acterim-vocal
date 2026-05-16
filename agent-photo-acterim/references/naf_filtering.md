# Filtres NAF — référence complète

## Liste blanche (NAF_CIBLE — 19 codes)

Seuls ces codes NAF sont acceptés comme cible commerciale ACTERIM.

| Code NAF | Métier (mapping NAF_TO_METIER) |
|---|---|
| 4311Z | Électricité |
| 4312A | Travaux de terrassement courants (⚠ rare en cible — à confirmer cas par cas) |
| 4312B | Travaux de terrassement spécialisés (idem) |
| 4313Z | Plomberie / CVC |
| 4321A | Charpente |
| 4321B | Structures métalliques (mais ⚠ aussi dans NAF_EXCLU_CODES selon contexte voie publique) |
| 4322Z | Équipements thermiques |
| 4323Z | Équipements électriques |
| 4324Z | Équipements de sécurité |
| 4329A | Équipements fluides |
| 4329B | Équipements spécialisés |
| 4330Z | Plâtrerie / Cloisons |
| 4334Z | Peinture / Vitrerie |
| 4339Z | Finition (autre) |
| 4391A | Revêtements / Carrelage |
| 4391B | Couverture / Étanchéité |

## Exclusions par préfixe (NAF_EXCLU_PREFIX)

Tout NAF commençant par ces préfixes est rejeté automatiquement :

- `16` — Industrie du bois (sciage, panneaux, charpente industrielle préfab)
- `23` — Fabrication d'autres produits minéraux (béton préfab, plâtre, carrelage industriel)
- `25` — Métallurgie / chaudronnerie industrielle
- `42` — TP / génie civil / voirie / réseaux / ouvrages d'art
- `431` — Démolition, terrassement, sondage, forage
- `71` — Activités d'architecture, BET, contrôle technique
- `81` — Services aux bâtiments / espaces verts / paysagisme

## Exclusions par code spécifique (NAF_EXCLU_CODES)

- `4321B` — Travaux d'installation électrique sur la voie publique (≠ bâtiment)
- `4332C` — Agencement de lieux de vente (commerce ≠ BTP exécutant)
- `4399E` — Location avec opérateur de matériel BTP (loueur ≠ exécutant)

## Ordre d'application

```
1. État administratif ≠ "A" → REJET ("État C — pas actif")
2. NAF préfixe ∈ NAF_EXCLU_PREFIX → REJET
3. NAF ∈ NAF_EXCLU_CODES → REJET
4. NAF connu ET NAF ∉ NAF_CIBLE → REJET ("hors cible bâtiment")
5. Âge < 5 ans → REJET
6. effectif_code ∉ {"11", "12", "NN"} → REJET
7. CA publié ET CA < 1 000 000€ → REJET
8. Sinon → VALIDE
```

## Pourquoi ces filtres

- **Effectif 10-49** : taille où l'intérim BTP est rentable (entreprise structurée mais pas assez grosse pour avoir un service RH interne).
- **Âge ≥ 5 ans** : élimine les startups/coquilles vides, garde les entreprises avec historique.
- **CA ≥ 1 M€** : seuil de viabilité économique (en dessous, rarement clients potentiels).
- **Bâtiment uniquement (pas TP)** : ACTERIM a un autre canal pour les TP/VRD.
