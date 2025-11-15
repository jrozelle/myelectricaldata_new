# Page Administration - Utilisateurs

## 🎯 Directives d'agent

- **Pour l'UX/UI** (interface, composants, design) : Utiliser l'agent **frontend-specialist**
- **Pour le backend** (API, base de données, logique métier) : Utiliser l'agent **backend-specialist**

Tu travailles sur la page `/admin/users` de l'application MyElectricalData.

## Description de la page

Cette page permet aux **administrateurs de gérer tous les utilisateurs** de la plateforme.

## Fonctionnalités principales

1. **Liste des utilisateurs**

   - Tableau avec tous les utilisateurs de la plateforme
   - Colonnes affichées :
     - Email
     - Client ID
     - Rôle
     - Statut (actif/inactif)
     - Mode debug (oui/non)
     - Date de création
     - Actions

2. **Recherche et filtrage**

   - Barre de recherche par email
   - Filtre par rôle (admin, user, etc.)
   - Filtre par statut (actif/inactif)
   - Tri par colonne

3. **Actions sur les utilisateurs**

   - Activer/Désactiver un utilisateur
   - Modifier le rôle d'un utilisateur
   - Activer/Désactiver le mode debug
   - Réinitialiser le mot de passe
   - Supprimer un utilisateur (avec confirmation)

4. **Création d'utilisateur**

   - Formulaire de création rapide
   - Attribution d'un rôle
   - Génération automatique d'un mot de passe temporaire

5. **Statistiques**
   - Nombre total d'utilisateurs
   - Nombre d'utilisateurs actifs
   - Nombre d'administrateurs
   - Utilisateurs créés ce mois

## Permissions requises

- **Rôle** : Administrateur uniquement
- **Permission** : `users:manage`

## Technologies utilisées

- React avec TypeScript
- React Query pour les mutations et le cache
- Tailwind CSS pour le style
- Support du mode sombre

## Fichiers liés

- **Frontend** : `apps/web/src/pages/AdminUsers.tsx`
- **API** : `apps/web/src/api/admin.ts`
- **Types** : `apps/web/src/types/api.ts`
- **Backend** : `apps/api/src/routers/admin.py`

## Navigation

Cette page est accessible via le **menu de navigation supérieur** : **Admin → Utilisateurs**

Le menu Admin regroupe toutes les pages d'administration :

- Tableau de bord, Utilisateurs, Offres, TEMPO, EcoWatt, Contributions, Rôles, Logs, Ajouter PDL

## Notes importantes

- Seuls les administrateurs peuvent accéder à cette page
- La désactivation d'un utilisateur ne supprime pas ses données
- Les modifications sont immédiatement répercutées dans le système
- Les actions sensibles nécessitent une confirmation
