# Page EcoWatt

Tu travailles sur la page `/ecowatt` de l'application MyElectricalData.

## Description de la page

Cette page affiche les **informations EcoWatt de RTE** sur l'état du réseau électrique français en temps réel et les prévisions.

## Fonctionnalités principales

1. **Signal EcoWatt actuel**
   - Indicateur visuel de l'état du réseau :
     - 🟢 Vert : Pas de tension sur le réseau
     - 🟠 Orange : Système électrique tendu
     - 🔴 Rouge : Système électrique très tendu, coupures possibles
   - Message explicatif selon le niveau
   - Heure de dernière mise à jour

2. **Prévisions sur 4 jours**
   - Tableau avec les prévisions jour par jour
   - État pour chaque tranche horaire (matin, après-midi, soir)
   - Code couleur selon le niveau de tension

3. **Statistiques**
   - Nombre de jours verts/orange/rouge sur le mois
   - Nombre de jours verts/orange/rouge sur l'année
   - Graphiques de répartition

4. **Recommandations**
   - Conseils d'EcoGestes selon le niveau du signal
   - Actions à entreprendre en cas de tension sur le réseau

5. **Informations complémentaires**
   - Explication du système EcoWatt
   - Pourquoi et quand économiser l'électricité
   - Lien vers le site officiel RTE

## Technologies utilisées

- React avec TypeScript
- React Query pour récupérer les données EcoWatt
- Tailwind CSS pour le style
- Support du mode sombre

## Fichiers liés

- **Frontend** : `apps/web/src/pages/EcoWatt.tsx`
- **API** : `apps/web/src/api/ecowatt.ts`
- **Types** : `apps/web/src/types/api.ts`
- **Backend** : `apps/api/src/routers/ecowatt.py`

## Notes importantes

- Les données EcoWatt sont fournies par l'API RTE
- Les prévisions sont mises à jour plusieurs fois par jour
- Le signal est particulièrement important en hiver
- Les coupures sont évitées grâce à la mobilisation citoyenne
