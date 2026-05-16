# Prompt d'extraction — règles complètes

## Contexte

ACTERIM = intérim BTP. La cible commerciale = entreprises qui **exécutent physiquement** des travaux de bâtiment.

## ❌ EXCLUSIONS STRICTES — ne JAMAIS extraire

### Acteurs intellectuels / non-exécutants
- Architectes / cabinets d'architecture (« archi », « architectes »)
- Bureaux d'études / BET (structure, fluides, économie de la construction, ingénierie)
- OPC (Ordonnancement Pilotage Coordination)
- Coordination SPS / sécurité chantier
- Contrôle technique : Qualiconsult, Apave, Veritas, Socotec, etc.
- Maître d'ouvrage : mairies, collectivités, promoteurs, SCI
- Financeurs / institutionnels : Région, Préfet, État, Europe, banques
- Géomètres, notaires, juristes

### Hors champ bâtiment
- TP / Travaux publics / VRD / Voirie / Réseaux / Ouvrages d'art / Tunnels
- Génie civil / Travaux fluviaux ou maritimes
- Démolition / Terrassement / Forage / Sondage
- Espaces verts / Paysagisme
- Location de matériel BTP
- Agencement de magasins / lieux de vente
- Industries de matériaux (béton préfab, plâtre préfab, carrelage préfab)
- Chaudronnerie industrielle / métallerie d'usine

## ✅ CIBLES VALIDES — entreprises bâtiment

- Gros œuvre / Maçonnerie / Béton (bâtiment)
- Couverture / Étanchéité / Bardage / Zinguerie
- Charpente (bois ou métallique)
- Menuiserie extérieure et intérieure (bois, PVC, alu)
- Électricité / Courants faibles (en bâtiment, hors voie publique)
- Plomberie / Sanitaire / CVC / Chauffage / Ventilation / Climatisation
- Plâtrerie / Plafonds suspendus / Cloisons sèches
- Peinture / Vitrerie / Revêtements de sol / Faïence / Carrelage
- Serrurerie / Métallerie de bâtiment
- Isolation / ITE / Désamiantage
- Échafaudage / Ravalement
- Structures métalliques de bâtiment
- Photovoltaïque (en toiture bâtiment) / Stores

## Format de sortie

Tableau JSON valide, **sans markdown**, **sans explication** :

```json
[
  {
    "societe": "NOM ENTREPRISE",
    "telephone": "0X XX XX XX XX",
    "email": "...",
    "site_web": "...",
    "adresse": "...",
    "code_postal": "...",
    "ville": "...",
    "metier": "..."
  }
]
```

Champs absents → `null`. Pas de chaîne vide, pas de « N/A ».

## Règle d'or

**Jamais la mention générique « Autre BTP ».** Si le métier n'est pas évident sur la photo, mets `null`. L'enrichissement INSEE remplira via le code NAF officiel.
