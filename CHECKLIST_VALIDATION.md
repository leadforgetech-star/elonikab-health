# Checklist de validation manuelle

## Lot 1 - Securite

- [ ] Patient -> GET /api/drivers = 403
- [ ] Patient -> PATCH /api/settings = 403
- [ ] Patient -> GET /api/settings = 200
- [ ] Non connecte -> POST /api/orders = 401
- [ ] Pharmacien -> GET /api/drivers = 200
- [ ] Pharmacien -> PATCH /api/settings = 200

## Lot 1 - Temps reel

- [ ] Visiteur : pas de stream 401 en boucle
- [ ] Patient sur /suivi : SSE s'ouvre
- [ ] Pharmacien change un statut -> patient recoit toast
- [ ] Pharmacien valide un paiement -> drawer se recharge

## Lot 1 - Drawer paiement

- [ ] Boutons Valider/Refuser visibles
- [ ] Cliquer Valider -> modale -> toast -> refresh
- [ ] Boutons disparaissent apres validation

## Lot 2 p1 - Audit

- [ ] Creer un livreur -> driver.create
- [ ] Desactiver un livreur -> driver.toggle
- [ ] Modifier un tarif -> settings.update
- [ ] Changer statut commande -> order.status_change

## Lot 2 p1 - Parametres

- [ ] Modifier Tarifs VOITURE Frais de base -> Enregistrer -> F5 -> persiste
- [ ] Tarifs MOTO, Paiement, WhatsApp -> idem

## Lot 2 p1 - UI

- [ ] Pas de sous-onglets Pharmacie/Tarifs/Paiement
- [ ] Section Livreurs visible
- [ ] Pas de reload en cliquant Desactiver
- [ ] Pas de reload auto apres 1 min
