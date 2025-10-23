# Page Administration - Gestion EcoWatt

Tu travailles sur la page `/admin/ecowatt` de l'application MyElectricalData.

## Description de la page

Cette page permet aux **administrateurs de gérer les données EcoWatt** et de synchroniser avec l'API RTE.

## Fonctionnalités principales

1. **Synchronisation avec l'API RTE**
   - Bouton pour forcer la synchronisation immédiate
   - Configuration de la synchronisation automatique
   - Fréquence de synchronisation (par défaut : toutes les heures)
   - Historique des dernières synchronisations

2. **Visualisation des données**
   - Signal EcoWatt actuel (Vert/Orange/Rouge)
   - Prévisions sur les 4 prochains jours
   - Historique des signaux EcoWatt
   - Graphique de tendance sur le mois

3. **Gestion manuelle des données**
   - Ajout manuel d'un signal EcoWatt
   - Modification d'un signal existant
   - Suppression de données erronées
   - Correction des anomalies

4. **Configuration de l'API RTE**
   - Clé API RTE
   - URL de l'endpoint
   - Timeout de requête
   - Retry policy
   - Test de connexion

5. **Statistiques**
   - Nombre de jours Vert/Orange/Rouge sur le mois
   - Nombre de jours Vert/Orange/Rouge sur l'année
   - Comparaison avec les années précédentes
   - Tendance d'évolution

6. **Logs de synchronisation**
   - Historique des synchronisations
   - Erreurs rencontrées
   - Nombre de données mises à jour
   - Temps de réponse de l'API RTE

7. **Alertes et notifications**
   - Alerte si signal rouge prévu
   - Notification si échec de synchronisation
   - Email aux utilisateurs en cas de signal orange/rouge

## Permissions requises

- **Rôle** : Administrateur
- **Permission** : `ecowatt:manage`

## Technologies utilisées

- React avec TypeScript
- React Query pour les mutations et le cache
- Recharts pour les graphiques
- Tailwind CSS pour le style
- Support du mode sombre

## Fichiers liés

- **Frontend** : `apps/web/src/pages/AdminEcoWatt.tsx`
- **API** : `apps/web/src/api/ecowatt.ts`, `apps/web/src/api/admin.ts`
- **Types** : `apps/web/src/types/api.ts`
- **Backend** : `apps/api/src/routers/ecowatt.py`

## Navigation

Cette page est accessible via le **menu de navigation supérieur** : **Admin → EcoWatt**

Le menu Admin regroupe toutes les pages d'administration :
- Tableau de bord, Utilisateurs, Offres, TEMPO, EcoWatt, Contributions, Rôles, Logs, Ajouter PDL

## Notes importantes

- Les données EcoWatt sont fournies par RTE (Réseau de Transport d'Électricité)
- La synchronisation doit se faire régulièrement pour avoir des données à jour
- Les signaux orange/rouge sont critiques et doivent être communiqués aux utilisateurs
- L'API RTE peut avoir des limites de taux, à surveiller
- Les données historiques sont importantes pour les analyses de tendance
