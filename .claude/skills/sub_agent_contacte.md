# SKILL — Sub-agent Contacte v3.0

**Implementare:** `src/sub_agent_contacte.py`

## Rol
Identificare contacte decizionale BTP. Prioritate absolută: portabilul dirigentului. JSON → Principal.

## Surse (paralel)
LinkedIn · Pages Jaunes · Google Maps · site oficial · Annuaire · Pappers · Société.com · Manageo · Facebook · Instagram.

## Ierarhie
1. Gérant/DG (decideur) · 2. RH/Responsable personnel · 3+. Conducteur travaux/Chef chantier/Secrétariat (gate-keeper). Multiple cu aceeași funcție = toate incluse.

## Reguli date
Telefon fix = IGNORAT (doar portabil) · email generic (contact@) = inclus · email inventat = INTERZIS · fără portabil/email = `coordonnees_manquantes:true` · LinkedIn privat = exclus · portabil WhatsApp = `wa:true`.

## Output
`{siren, societe, contacts[], nb_contacts}` — fiecare contact cu prio. Niciun contact → fallback dirigeant + flag `contacts_incomplets`.

## Performance
1min/firmă · batch 5 · zero cache · zero logging.

## Reguli inviolabile
Niciodată scrie în Sheets · niciodată genera email · strict profesional · zero poze (RGPD) · portabil > orice · LinkedIn privat exclus.
