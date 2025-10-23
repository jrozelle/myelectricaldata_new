# Page Consommation

Tu travailles sur la page `/consumption` de l'application MyElectricalData.

## Description de la page

Cette page permet aux utilisateurs de **visualiser et analyser leur consommation électrique** récupérée depuis l'API Enedis.

## Fonctionnalités principales

1. **Sélection du PDL** (Point De Livraison)
   - Sélecteur de PDL si l'utilisateur en a plusieurs
   - Affichage d'un message d'information si le PDL a des données limitées

2. **Récupération des données**
   - Bouton "Récupérer l'historique" pour charger les données
   - Chargement automatique depuis le cache si disponible
   - Indicateurs de progression pour 3 types de données :
     - Données quotidiennes (3 ans)
     - Puissance maximum (3 ans)
     - Données détaillées (2 ans)

3. **Statistiques de consommation**
   - Consommation par année avec graphiques
   - Comparaison mensuelle sur plusieurs années
   - Répartition HC/HP (Heures Creuses/Heures Pleines) si disponible

4. **Graphiques**
   - Courbe annuelle de consommation
   - Comparaison année par année

5. **Courbe de charge détaillée**
   - Données par intervalle de 30 minutes
   - Navigation par semaine et par jour
   - Comparaison avec l'année précédente si disponible
   - Détection automatique des heures creuses/pleines

6. **Pics de puissance maximale**
   - Graphiques des pics de puissance par année
   - Ligne de référence pour la puissance souscrite
   - Information sur les dépassements autorisés par le Linky

## Technologies utilisées

- React avec TypeScript
- React Query pour la gestion du cache et des requêtes API
- Recharts pour les graphiques
- Tailwind CSS pour le style
- Support du mode sombre

## Fichiers liés

- **Frontend** : `apps/web/src/pages/Consumption.tsx`
- **API** : `apps/web/src/api/enedis.ts`, `apps/web/src/api/pdl.ts`
- **Types** : `apps/web/src/types/api.ts`
- **Backend** : `apps/api/src/routers/enedis.py`, `apps/api/src/routers/pdl.py`

## Notes importantes

- Les données sont mises en cache pendant 24 heures pour limiter les appels à l'API Enedis
- Le système gère automatiquement les limites de dates (activation_date et oldest_available_data_date)
- Les graphiques s'adaptent automatiquement au mode sombre
- Toutes les sections s'auto-expandent une fois le chargement terminé
