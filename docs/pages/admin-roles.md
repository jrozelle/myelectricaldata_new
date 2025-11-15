# Page Administration - Gestion des rôles

## 🎯 Directives d'agent

- **Pour l'UX/UI** (interface, composants, design) : Utiliser l'agent **frontend-specialist**
- **Pour le backend** (API, base de données, logique métier) : Utiliser l'agent **backend-specialist**

Tu travailles sur la page `/admin/roles` de l'application MyElectricalData.

## Description de la page

Cette page permet aux **administrateurs de gérer les rôles et permissions** du système RBAC (Role-Based Access Control).

## Fonctionnalités principales

1. **Liste des rôles**

   - Tableau avec tous les rôles du système
   - Colonnes affichées :
     - Nom du rôle
     - Nom d'affichage
     - Description
     - Nombre d'utilisateurs
     - Nombre de permissions
     - Type (système/personnalisé)
     - Actions

2. **Création de rôle**

   - Formulaire de création d'un nouveau rôle
   - Champs :
     - Nom technique (identifier unique)
     - Nom d'affichage
     - Description
     - Sélection des permissions
   - Validation des noms uniques

3. **Modification de rôle**

   - Édition du nom d'affichage
   - Modification de la description
   - Ajout/retrait de permissions
   - Aperçu des utilisateurs affectés
   - Impossible de modifier les rôles système (admin, user)

4. **Gestion des permissions**

   - Liste de toutes les permissions disponibles
   - Regroupement par catégorie :
     - **users** : Gestion des utilisateurs
     - **pdl** : Gestion des PDL
     - **offers** : Gestion des offres
     - **tempo** : Gestion TEMPO
     - **ecowatt** : Gestion EcoWatt
     - **contributions** : Gestion des contributions
     - **logs** : Consultation des logs
     - **admin** : Administration système

5. **Permissions par action**

   - **view** : Consultation
   - **create** : Création
   - **update** : Modification
   - **delete** : Suppression
   - **manage** : Gestion complète

6. **Attribution de rôles**

   - Liste des utilisateurs avec leur rôle actuel
   - Changement de rôle pour un utilisateur
   - Recherche d'utilisateurs
   - Filtrage par rôle

7. **Suppression de rôle**

   - Impossible de supprimer un rôle système
   - Vérification qu'aucun utilisateur n'a ce rôle
   - Réaffectation automatique au rôle par défaut si nécessaire
   - Confirmation avant suppression

8. **Rôles prédéfinis**
   - **admin** : Accès complet à tout le système
   - **user** : Utilisateur standard (gestion de ses PDL)
   - **contributor** : Peut soumettre des contributions
   - **moderator** : Peut modérer les contributions

## Matrice de permissions par défaut

### Admin

- Toutes les permissions (\*)

### User

- `pdl:view`, `pdl:create`, `pdl:update`, `pdl:delete`
- `consumption:view`
- `offers:view`
- `tempo:view`
- `ecowatt:view`

### Contributor

- Toutes les permissions User +
- `contributions:create`, `contributions:view`

### Moderator

- Toutes les permissions Contributor +
- `contributions:manage`
- `offers:create`, `offers:update`

## Permissions requises

- **Rôle** : Administrateur
- **Permission** : `roles:manage`

## Technologies utilisées

- React avec TypeScript
- React Query pour les mutations et le cache
- Tailwind CSS pour le style
- Support du mode sombre

## Fichiers liés

- **Frontend** : `apps/web/src/pages/AdminRoles.tsx`
- **API** : `apps/web/src/api/admin.ts`, `apps/web/src/api/roles.ts`
- **Types** : `apps/web/src/types/api.ts`
- **Backend** : `apps/api/src/routers/roles.py`, `apps/api/src/routers/admin.py`

## Navigation

Cette page est accessible via le **menu de navigation supérieur** : **Admin → Rôles**

Le menu Admin regroupe toutes les pages d'administration :

- Tableau de bord, Utilisateurs, Offres, TEMPO, EcoWatt, Contributions, Rôles, Logs, Ajouter PDL

## Notes importantes

- Le système RBAC est au cœur de la sécurité de l'application
- Les rôles système (admin, user) ne peuvent pas être supprimés
- Chaque utilisateur doit avoir exactement un rôle
- Les permissions sont vérifiées côté backend pour chaque requête
- Les modifications de rôles prennent effet immédiatement
- Un utilisateur peut avoir un rôle personnalisé avec des permissions spécifiques
