---
name: admin_add-pdl
slug: /admin/add-pdl
description: Ajout manuel d'un PDL a un utilisateur
mode_client: false
mode_server: true
menu: Administration
subMenu: Ajouter PDL
tab: Ajouter PDL
---

# Page Administration - Ajouter un PDL

Fichier : `apps/web/src/pages/Admin/AddPDL.tsx`

## Features

| Feature               | Statut |
| --------------------- | ------ |
| Selection utilisateur | FAIT   |
| Informations PDL      | FAIT   |
| Options avancees      | FAIT   |
| Validation            | FAIT   |
| Notifications         | FAIT   |

## Details implementation

### Selection utilisateur avec auto-completion (FAIT)

- Recherche interactive temps reel
- Recherche par email ou Client ID
- Dropdown avec resultats filtres
- Navigation clavier (fleches, Enter, Esc)
- Surbrillance element actif
- Affichage infos : email, client ID, date creation, statut admin
- Bouton reinitialisation (x)

**Comportement** :

- Aucun utilisateur selectionne : PDL ajoute au compte admin connecte
- Utilisateur selectionne : PDL ajoute a son compte

### Informations du PDL (FAIT)

- **Numero PDL** (usage_point_id) - Requis
  - Validation format (14 chiffres exactement)
  - Filtre automatique chiffres uniquement
  - Police monospace
- **Nom personnalise** (optionnel)
  - Nom convivial pour identifier le PDL
  - Limite 100 caracteres

### Options avancees (FAIT)

- Puissance souscrite (menu 3-36 kVA)
- Configuration heures creuses (ajout/suppression plages)
- Type consommation (consommation/production/mixte)
- Statut actif/inactif
- Dates (activation contrat, donnees anciennes)

### Validation (FAIT)

- Format numero PDL (14 chiffres)
- Format email si fourni
- Messages d'erreur specifiques

### Notifications (FAIT)

- **Succes** : Confirmation ajout avec precision compte cible
- **Erreur** : Message erreur API
- Toast dismissible avec bouton fermeture

### Actions post-creation (FAIT)

- Reinitialisation formulaire apres succes
- Option "Ajouter un autre PDL" pour creations multiples
- Redirection automatique vers PDL cree (2 secondes)
- Compteur caracteres pour PDL

## Cas d'usage

- **Test et developpement** : Ajouter PDL de test
- **Migration donnees** : Import PDL existants
- **Support utilisateur** : Resoudre problemes consentement
- **Situations exceptionnelles** : Consentement Enedis ne fonctionne pas

## Differences avec consentement Enedis

| Aspect              | Consentement Enedis | Ajout admin     |
| ------------------- | ------------------- | --------------- |
| Donnees recuperees  | Auto depuis Enedis  | Aucune          |
| Validation          | Par Enedis          | Format PDL seul |
| Puissance souscrite | Auto-detectee       | Saisie manuelle |
| Heures creuses      | Auto-detectees      | Saisie manuelle |
| Consentement        | Requis              | Non requis      |

## Permissions requises

- **Role** : Administrateur
- **Permission** : `pdl:create`, `admin:manage`

## Technologies

- React avec TypeScript
- React Query pour mutations
- Tailwind CSS + dark mode

## API utilisee

- **Sans email** : `pdlApi.create()` - Ajoute au compte connecte
- **Avec email** : `pdlApi.adminAddPdl()` - Ajoute au compte specifie

## Composants UI

- Card : Structure formulaire
- Input : Champs saisie
- Button : Bouton ajout avec etat chargement
- Toast : Notifications dismissibles
- Alert : Avertissement admin (orange) + section info (bleue)
- Icons : Lucide React (Activity, CheckCircle, XCircle, AlertCircle, ArrowLeft)

## Notes

- Fonctionnalite reservee administrateurs
- PDL ajoutes n'ont pas de donnees consommation automatiques
- Declenchement manuel recuperation donnees via API Enedis
- Numero PDL doit etre valide et existant chez Enedis
- Interface affiche avertissement orange (fonction administrative)
- Utilisateur peut lier son compte Enedis normalement ensuite
