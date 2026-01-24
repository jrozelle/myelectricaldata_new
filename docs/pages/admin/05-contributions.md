---
name: admin_contributions
slug: /admin/contributions
description: Moderation des contributions d'offres d'energie
mode_client: false
mode_server: true
menu: Administration
subMenu: Contributions
tab: Contributions
---

# Page Administration - Gestion des contributions

Fichier : `apps/web/src/pages/Admin/Contributions.tsx`

## Features

| Feature               | Statut |
| --------------------- | ------ |
| Statistiques          | FAIT   |
| Filtrage et recherche | FAIT   |
| Liste contributions   | FAIT   |
| Messagerie WhatsApp   | FAIT   |
| Actions individuelles | FAIT   |
| Actions en masse      | FAIT   |
| Auto-refresh          | FAIT   |

## Details implementation

### Statistiques (FAIT)

Cards affichant :

- **En attente** : Contributions a traiter (icone Clock, bleu)
- **Validees ce mois** : Approuvees ce mois (icone CheckCircle, vert)
- **Rejetees** : Total rejetees (icone XCircle, rouge)
- **Total validees** : Total approuvees (icone Users, violet)

**Top contributeurs** : 5 meilleurs avec avatar, email, badge contributions

### Filtrage et recherche (FAIT)

- Recherche par nom offre ou email contributeur
- Filtre par type : Tous, BASE, HC/HP, TEMPO, EJP
- Tri par date : Plus recent / Plus ancien

### Liste des contributions (FAIT)

Chaque contribution affiche :

- Checkbox de selection
- Nom offre + badge type (Nouvelle offre, Nouveau fournisseur, Mise a jour)
- Email contributeur + date soumission
- Informations fournisseur
- Tarification proposee
- Documentation (lien fiche prix, screenshot)

### Messagerie style WhatsApp (FAIT)

Composant partage `ChatWhatsApp` :

- Bouton "Voir les echanges" (toggle)
- Indicateur message non lu (point orange clignotant)
- Bulles avec queues orientees selon expediteur
- Messages admin : a droite, fond vert/bleu
- Messages contributeur : a gauche, fond blanc/gris
- Horodatage "JJ/MM HH:MM"
- Double checkmark pour messages lus
- Auto-refresh silencieux toutes les 5 secondes
- Reponse rapide avec envoi via Entree

### Actions individuelles (FAIT)

- **Approuver** (vert) : Modal confirmation
- **Demander des infos** (bleu) : Modal avec messages rapides
- **Rejeter** (rouge) : Modal avec raisons predefinies :
  - Offre non valide, Lien invalide, Offre introuvable
  - Offre expiree, Doublon, Donnees incompletes

### Actions en masse (FAIT)

- Selection multiple avec checkboxes
- Selectionner tout (checkbox en entete)
- Barre d'actions flottante :
  - Compteur selection
  - Bouton "Approuver" (vert)
  - Bouton "Rejeter" (rouge)
  - Bouton "Annuler"

### Auto-refresh (FAIT)

- Rafraichissement toutes les 30 secondes
- Rafraichissement au focus fenetre
- Invalidation cache apres chaque action

## Permissions requises

- **Permission** : `contributions` (via `require_permission('contributions')`)

## Technologies

- React avec TypeScript
- React Query pour mutations, cache, auto-refresh
- Tailwind CSS + dark mode
- localStorage pour contributions lues

## API utilisee

| Endpoint                                  | Methode | Description         |
| ----------------------------------------- | ------- | ------------------- |
| `/energy/contributions/pending`           | GET     | Liste en attente    |
| `/energy/contributions/stats`             | GET     | Statistiques        |
| `/energy/contributions/{id}/approve`      | POST    | Approuver           |
| `/energy/contributions/{id}/reject`       | POST    | Rejeter             |
| `/energy/contributions/{id}/request-info` | POST    | Demander infos      |
| `/energy/contributions/{id}/messages`     | GET     | Historique messages |
| `/energy/contributions/bulk-approve`      | POST    | Approbation masse   |
| `/energy/contributions/bulk-reject`       | POST    | Rejet masse         |

## Workflow moderation

1. Utilisateur soumet via `/contribute`
2. Contribution en statut "En attente"
3. Indicateur clignote si contributeur repond
4. Administrateur examine
5. Dialogue via reponse rapide
6. Validation ou rejet
7. Notification email a l'utilisateur
8. Si validee, offre ajoutee en base

## Notes

- Messages non lus detectes cote backend (`has_unread_messages`)
- Contributions lues stockees dans localStorage
- Cache React Query invalide apres chaque action
