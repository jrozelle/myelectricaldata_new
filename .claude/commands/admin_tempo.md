# Page Administration - Gestion TEMPO

Tu travailles sur la page `/admin/tempo` de l'application MyElectricalData.

## Description de la page

Cette page permet aux **administrateurs de gérer les données TEMPO** (couleurs des jours) dans le système.

## Fonctionnalités principales

1. **Calendrier TEMPO éditable**

   - Affichage mensuel des jours TEMPO
   - Possibilité de modifier la couleur de chaque jour
   - Couleurs disponibles : Bleu, Blanc, Rouge, Non défini
   - Navigation entre les mois et les années

2. **Import de données**

   - Import en masse depuis un fichier JSON
   - Import depuis l'API RTE officielle
   - Format attendu : date → couleur

3. **Modification manuelle**

   - Clic sur un jour pour changer sa couleur
   - Sélection multiple pour appliquer une couleur à plusieurs jours
   - Annulation des modifications non sauvegardées

4. **Validation**

   - Vérification du nombre de jours par couleur :
     - Maximum 300 jours Bleu par an
     - Maximum 43 jours Blanc par an
     - Maximum 22 jours Rouge par an
   - Alertes si les limites sont dépassées

5. **Statistiques**

   - Compteur en temps réel par couleur
   - Jours restants pour chaque couleur
   - Comparaison avec les années précédentes

6. **Sauvegarde**
   - Bouton pour enregistrer les modifications
   - Confirmation avant sauvegarde
   - Synchronisation avec la base de données

## Permissions requises

- **Rôle** : Administrateur
- **Permission** : `tempo:manage`

## Technologies utilisées

- React avec TypeScript
- React Query pour les mutations et le cache
- Tailwind CSS pour le style
- Support du mode sombre

## Fichiers liés

- **Frontend** : `apps/web/src/pages/AdminTempo.tsx`
- **API** : `apps/web/src/api/tempo.ts`, `apps/web/src/api/admin.ts`
- **Types** : `apps/web/src/types/api.ts`
- **Backend** : `apps/api/src/routers/tempo.py`

## Navigation

Cette page est accessible via le **menu de navigation supérieur** : **Admin → EDF Tempo**

Le menu Admin regroupe toutes les pages d'administration :

- Tableau de bord, Utilisateurs, Offres, Tempo, EcoWatt, Contributions, Rôles, Logs, Ajouter PDL

## Notes importantes

- Les données TEMPO sont critiques pour les calculs du simulateur
- Les limites annuelles doivent être respectées (EDF contract)
- L'année TEMPO va de septembre à août (année N-1 → année N)
- Les données futures ne sont généralement pas connues à l'avance
