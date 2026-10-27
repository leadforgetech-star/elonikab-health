# Elonikab Health - Documentation technique

## Architecture

    main.py             -> routes FastAPI, startup, middleware
    database.db         -> SQLite (toutes les tables)
    v3_modules/         -> modules metier
    static/             -> frontend (HTML/CSS/JS vanilla)
    uploads/            -> fichiers sensibles

## Roles

- PATIENT : commande, paie, suit sa commande
- PROFESSIONNEL : commande en gros (B2B)
- PHARMACIEN : traite les commandes, valide paiements
- ADMIN : acces total, gere les utilisateurs

## Verrous metier

Voir DOC_TRANSITIONS.md pour la reference complete.

## Journalisation (audit_logs)

Table : id, user_id, action, target_type, target_id, details, created_at

Actions instrumentees :

- order.status_change
- payment.verify, payment.reject, payment.refund
- file.access
- driver.create, driver.toggle
- settings.update
- prescription.review

## Securite

- Endpoints admin : require_role PHARMACIEN/ADMIN
- POST /api/orders : authentification obligatoire
- Fichiers sensibles : /api/files avec rattachement verifie
- Chunked upload : checks refused sur 3 endpoints

## Tests

- test_e2e_complet.py : 12 scenarios
- test_lot2_e2e.py : 5 scenarios

## Restauration

Backups dans _backup_* et _closure_backup_*.
Copier le fichier souhaite vers son emplacement d'origine.

## Historique

- Lot 1 : 5 failles securite + bonus SSE + drawer paiement
- Lot 2 p1 : audit_logs etendus + 15 champs settings + fix reloads
- Lot 2 p2 : a venir (coherence front/back, tests etendus)
