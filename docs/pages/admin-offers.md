# Page Administration - Offres d'énergie

## 🎯 Directives d'agent

- **Pour l'UX/UI** (interface, composants, design) : Utiliser l'agent **frontend-specialist**
- **Pour le backend** (API, base de données, logique métier) : Utiliser l'agent **backend-specialist**

Tu travailles sur la page `/admin/offers` de l'application MyElectricalData.

## Description de la page

Cette page permet aux **administrateurs de gérer les offres d'électricité** proposées par les différents fournisseurs d'énergie.

## Fonctionnalités principales

1. **Liste des offres**

   - Tableau avec toutes les offres disponibles
   - Colonnes affichées :
     - Fournisseur
     - Nom de l'offre
     - Type (BASE, HP/HC, TEMPO)
     - Puissance(s) souscrite(s) compatible(s)
     - Prix de l'abonnement
     - Prix du kWh
     - Statut (actif/inactif)
     - Actions

2. **Filtrage et recherche**

   - Filtre par fournisseur
   - Filtre par type d'offre
   - Filtre par puissance souscrite
   - Recherche par nom d'offre

3. **Création d'offre**

   - Formulaire de création d'une nouvelle offre
   - Sélection du fournisseur
   - Configuration des tarifs selon le type :
     - **BASE** : prix unique du kWh
     - **HP/HC** : prix HP et prix HC
     - **TEMPO** : 6 prix (Bleu HP/HC, Blanc HP/HC, Rouge HP/HC)
   - Prix de l'abonnement
   - Puissances compatibles

4. **Modification d'offre**

   - Édition des tarifs
   - Modification du statut actif/inactif
   - Mise à jour de la puissance souscrite

5. **Suppression d'offre**

   - Désactivation ou suppression définitive
   - Confirmation avant suppression

6. **Import/Export**
   - Import en masse depuis un fichier JSON/CSV
   - Export de toutes les offres

## Permissions requises

- **Rôle** : Administrateur
- **Permission** : `offers:manage`

## Technologies utilisées

- React avec TypeScript
- React Query pour les mutations et le cache
- Tailwind CSS pour le style
- Support du mode sombre

## Fichiers liés

- **Frontend** : `apps/web/src/pages/AdminOffers.tsx`
- **API** : `apps/web/src/api/energy.ts`, `apps/web/src/api/admin.ts`
- **Types** : `apps/web/src/types/api.ts`
- **Backend** : `apps/api/src/routers/energy.py`

## Navigation

Cette page est accessible via le **menu de navigation supérieur** : **Admin → Offres**

Le menu Admin regroupe toutes les pages d'administration :

- Tableau de bord, Utilisateurs, Offres, TEMPO, EcoWatt, Contributions, Rôles, Logs, Ajouter PDL

## Notes importantes

- Les offres désactivées ne sont plus proposées dans le simulateur
- Les tarifs doivent être mis à jour régulièrement
- Les puissances souscrites sont en kVA (3, 6, 9, 12, 15, 18, 24, 30, 36)
- Les offres TEMPO ont 6 tarifs différents (3 couleurs × 2 périodes)
