# Page Simulateur

Tu travailles sur la page `/simulator` de l'application MyElectricalData.

## Description de la page

Cette page permet aux utilisateurs de **comparer automatiquement toutes les offres d'électricité disponibles** en utilisant leurs données de consommation réelles sur les 12 derniers mois.

## Fonctionnalités principales

1. **Configuration**
   - Sélection du PDL (Point De Livraison)
   - Affichage automatique des offres correspondant à la puissance souscrite
   - Bouton "Lancer la simulation"

2. **Récupération des données**
   - Chargement automatique des données de consommation horaires sur 12 mois
   - Barre de progression avec pourcentage et phase actuelle
   - Messages informatifs pendant le chargement

3. **Résultats de simulation**
   - Tableau comparatif de toutes les offres classées par coût total
   - Détails pour chaque offre :
     - Fournisseur et nom de l'offre
     - Type d'offre (BASE, HP/HC, TEMPO)
     - Coût de l'abonnement annuel
     - Coût de l'énergie annuel
     - Coût total annuel
   - Possibilité d'étendre chaque ligne pour voir le détail du calcul

4. **Détails par offre**
   - Répartition par type d'heure (HC/HP pour les offres doubles tarifs)
   - Répartition par couleur de jour (pour TEMPO : Bleu/Blanc/Rouge)
   - Calcul détaillé : kWh × prix = coût

5. **Export PDF**
   - Génération d'un PDF complet avec tous les résultats
   - Classement des offres
   - Détails de chaque offre
   - Nom du fichier : `comparatif-offres-{PDL}-{date}.pdf`

6. **Informations additionnelles**
   - Consommation totale sur la période
   - Économies potentielles entre l'offre la moins chère et la plus chère

## Technologies utilisées

- React avec TypeScript
- React Query pour la gestion des requêtes API
- jsPDF pour la génération de PDF
- Tailwind CSS pour le style
- Support du mode sombre

## Fichiers liés

- **Frontend** : `apps/web/src/pages/Simulator.tsx`
- **API** : `apps/web/src/api/enedis.ts`, `apps/web/src/api/energy.ts`
- **Types** : `apps/web/src/types/api.ts`
- **Backend** : `apps/api/src/routers/enedis.py`, `apps/api/src/routers/energy.py`

## Notes importantes

- Les données sont récupérées mois par mois pour respecter les limites de l'API Enedis
- Le cache est automatiquement activé pour améliorer les performances
- Les données en cache expirent après 24 heures
- La simulation utilise les tarifs réels stockés en base de données
- Les offres sont automatiquement filtrées selon la puissance souscrite du PDL
