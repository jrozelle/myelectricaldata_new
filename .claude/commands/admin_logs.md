# Page Administration - Logs

Tu travailles sur la page `/admin/logs` de l'application MyElectricalData.

## Description de la page

Cette page permet aux **administrateurs de consulter les logs système** pour le monitoring et le débogage.

## Fonctionnalités principales

1. **Affichage des logs**
   - Liste en temps réel des logs système
   - Colonnes affichées :
     - Timestamp
     - Niveau (DEBUG, INFO, WARNING, ERROR, CRITICAL)
     - Module/Source
     - Message
     - Utilisateur (si applicable)
     - Détails supplémentaires

2. **Filtrage**
   - Filtre par niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
   - Filtre par module/source
   - Filtre par utilisateur
   - Filtre par période (date de début/fin)
   - Recherche dans les messages

3. **Tri et pagination**
   - Tri par date (ascendant/descendant)
   - Pagination avec nombre de résultats par page configurable
   - Affichage du nombre total de logs

4. **Code couleur**
   - DEBUG : Gris
   - INFO : Bleu
   - WARNING : Orange
   - ERROR : Rouge
   - CRITICAL : Rouge foncé

5. **Actions**
   - Rafraîchissement manuel
   - Rafraîchissement automatique (toutes les 10s)
   - Export des logs en CSV ou JSON
   - Vidage des logs anciens (avec confirmation)

6. **Détails d'un log**
   - Clic sur un log pour afficher les détails complets
   - Stack trace pour les erreurs
   - Contexte additionnel (requête HTTP, paramètres, etc.)

## Permissions requises

- **Rôle** : Administrateur
- **Permission** : `logs:view`

## Technologies utilisées

- React avec TypeScript
- React Query pour le polling automatique
- Tailwind CSS pour le style
- Support du mode sombre

## Fichiers liés

- **Frontend** : `apps/web/src/pages/AdminLogs.tsx`
- **API** : `apps/web/src/api/admin.ts`
- **Types** : `apps/web/src/types/api.ts`
- **Backend** : `apps/api/src/routers/admin.py`, logging system

## Navigation

Cette page est accessible via le **menu de navigation supérieur** : **Admin → Logs**

Le menu Admin regroupe toutes les pages d'administration :
- Tableau de bord, Utilisateurs, Offres, TEMPO, EcoWatt, Contributions, Rôles, Logs, Ajouter PDL

## Notes importantes

- Les logs sont critiques pour diagnostiquer les problèmes en production
- Les logs sensibles (mots de passe, tokens) sont automatiquement masqués
- Les logs anciens sont archivés et supprimés automatiquement après 90 jours
- Le niveau DEBUG génère beaucoup de logs, à utiliser avec parcimonie
