# Page Administration - Tableau de bord

Tu travailles sur la page `/admin` de l'application MyElectricalData.

## Description de la page

Cette page est le **tableau de bord principal d'administration** qui donne une vue d'ensemble du système.

## Fonctionnalités principales

1. **Statistiques générales**

   - **Utilisateurs**

     - Nombre total d'utilisateurs
     - Nouveaux utilisateurs ce mois
     - Utilisateurs actifs (dernière connexion < 30 jours)
     - Utilisateurs inactifs

   - **PDL (Points De Livraison)**

     - Nombre total de PDL
     - PDL actifs
     - PDL créés ce mois
     - Répartition par utilisateur

   - **Données**

     - Volume de données stockées (consommation, puissance)
     - Requêtes API Enedis ce mois
     - Taux de cache hit/miss
     - Espace disque utilisé

   - **Offres d'énergie**
     - Nombre total d'offres
     - Offres actives
     - Fournisseurs référencés
     - Dernière mise à jour des tarifs

2. **Graphiques et visualisations**

   - Évolution du nombre d'utilisateurs (30 derniers jours)
   - Répartition des types d'offres
   - Activité système (requêtes par jour)
   - Utilisation du cache

3. **Alertes et notifications**

   - Contributions en attente de validation
   - Erreurs API récentes
   - Espace disque faible
   - Certificats SSL à renouveler
   - Mises à jour système disponibles

4. **Raccourcis vers les pages admin**

   - 👥 Gestion des utilisateurs
   - 📋 Gestion des offres
   - 🎨 Gestion TEMPO
   - 📊 Logs système
   - ⚡ Gestion EcoWatt
   - 💡 Contributions
   - 🔐 Gestion des rôles

5. **Informations système**

   - Version de l'application (frontend + backend)
   - Environnement (production/développement)
   - Dernière mise à jour
   - Base de données (type, taille, connexions actives)
   - API externes (status Enedis, RTE)

6. **Actions rapides**
   - Vider le cache Redis
   - Forcer la synchronisation TEMPO
   - Forcer la synchronisation EcoWatt
   - Backup de la base de données
   - Redémarrer les workers

## Permissions requises

- **Rôle** : Administrateur uniquement
- **Permission** : `admin:view`

## Technologies utilisées

- React avec TypeScript
- React Query pour les requêtes en temps réel
- Recharts pour les graphiques
- Tailwind CSS pour le style
- Support du mode sombre

## Fichiers liés

- **Frontend** : `apps/web/src/pages/Admin.tsx`
- **API** : `apps/web/src/api/admin.ts`
- **Types** : `apps/web/src/types/api.ts`
- **Backend** : `apps/api/src/routers/admin.py`

## Navigation

Cette page est accessible via le **menu de navigation supérieur** qui regroupe toutes les pages d'administration :

- 👥 Admin → Tableau de bord
- 👥 Admin → Utilisateurs
- 📋 Admin → Offres
- 🎨 Admin → Tempo
- ⚡ Admin → EcoWatt
- 💡 Admin → Contributions
- 🔐 Admin → Rôles
- 📊 Admin → Logs
- ➕ Admin → Ajouter PDL

## Notes importantes

- Le tableau de bord se rafraîchit automatiquement toutes les 30 secondes
- Seuls les administrateurs peuvent accéder à cette page
- Les statistiques sont calculées en temps réel
- Les actions sensibles nécessitent une confirmation
- Les graphiques sont interactifs avec tooltip au survol
