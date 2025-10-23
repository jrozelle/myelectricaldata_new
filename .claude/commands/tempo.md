# Page Tempo

Tu travailles sur la page `/tempo` de l'application MyElectricalData.

## Description de la page

Cette page affiche le **calendrier TEMPO** d'EDF avec les couleurs des jours (Bleu, Blanc, Rouge) et les statistiques associées.

## Fonctionnalités principales

1. **Calendrier TEMPO**
   - Affichage mensuel des jours TEMPO
   - Couleurs par jour :
     - 🔵 Bleu : jours les moins chers (300 jours/an)
     - ⚪ Blanc : jours intermédiaires (43 jours/an)
     - 🔴 Rouge : jours les plus chers (22 jours/an)
   - Navigation entre les mois et les années
   - Jour actuel mis en évidence

2. **Statistiques**
   - Compteur de jours par couleur pour l'année en cours
   - Jours restants pour chaque couleur
   - Progression visuelle avec barres de couleur

3. **Légende**
   - Explication des couleurs TEMPO
   - Nombre de jours autorisés par couleur

4. **Informations**
   - Explication du tarif TEMPO
   - Avantages et contraintes
   - Lien vers la documentation EDF

## Technologies utilisées

- React avec TypeScript
- React Query pour récupérer les données TEMPO
- Tailwind CSS pour le style
- Support du mode sombre

## Fichiers liés

- **Frontend** : `apps/web/src/pages/Tempo.tsx`
- **API** : `apps/web/src/api/tempo.ts`
- **Types** : `apps/web/src/types/api.ts`
- **Backend** : `apps/api/src/routers/tempo.py`

## Notes importantes

- Les données TEMPO sont mises à jour quotidiennement
- Les couleurs futures ne sont connues que la veille pour le lendemain
- Le système gère automatiquement les années de transition (septembre à août)
- Les données historiques sont stockées en base de données
