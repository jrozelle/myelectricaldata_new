# Page Administration - Logs

## 🎯 Directives d'agent

- **Pour l'UX/UI** (interface, composants, design) : Utiliser l'agent **frontend-specialist**
- **Pour le backend** (API, base de données, logique métier) : Utiliser l'agent **backend-specialist**

Tu travailles sur la page `/admin/logs` de l'application MyElectricalData.

## Description de la page

Cette page permet aux **administrateurs de consulter les logs système** pour le monitoring et le débogage.

## Fonctionnalités principales

1. **Affichage des logs**

   - Liste en temps réel des logs système
   - Colonnes affichées (configurables) :
     - Timestamp
     - Niveau (DEBUG, INFO, WARNING, ERROR)
     - Module/Source
     - Message
   - Identification PDL : tous les logs liés à un PDL affichent le préfixe `[XXXXXXXXXXXXXX]`
   - Expansion des logs pour voir les détails complets (pathname, line number, exception)

2. **Panneau de filtres intelligent**

   - **Header réduit interactif** : contrôles essentiels toujours visibles
     - Champ de recherche (Ctrl+K) qui prend toute la largeur disponible
     - Boutons de filtrage rapide par niveau (INFO, WARNING, ERROR, DEBUG)
     - Badge indicateur de filtres modules actifs (cliquable pour déplier le panneau)
   - **Panneau détaillé** (dépliable) :
     - Sélection multiple des niveaux de log avec boutons Tous/Aucun
     - Filtrage par modules organisés par catégories (src, uvicorn, fastapi, sqlalchemy)
     - Boutons "Seul" et "Tous/Aucun" par catégorie pour une sélection rapide
     - Affichage en grille (5 colonnes) des modules par catégorie
   - Recherche textuelle dans tous les champs des logs
   - Sélection des colonnes visibles (Timestamp, Niveau, Module, Message)
     - Le colSpan des lignes étendues s'adapte automatiquement au nombre de colonnes visibles
   - Choix du nombre de lignes affichées (50, 100, 200, 500, 1000)
   - **Filtres par défaut** : INFO, WARNING, ERROR (DEBUG exclu pour réduire le bruit)
   - Tous les filtres sont sauvegardés automatiquement dans localStorage

3. **Tri et navigation**

   - Tri par timestamp (ascendant/descendant)
   - Nombre de logs configurables par page (50 à 1000)
   - Préservation automatique de la position de scroll lors du refresh
     - Protection contre les erreurs après unmount du composant
     - Gestion des timestamps vus avec pruning automatique (max 2x linesCount) pour éviter les fuites mémoire
   - Scroll fluide avec barre de défilement personnalisée

4. **Code couleur**

   - DEBUG : Gris (`bg-gray-100/200`)
   - INFO : Bleu (`bg-blue-100/600`)
   - WARNING : Orange (`bg-yellow-100/500`)
   - ERROR : Rouge (`bg-red-100/600`)
   - Support complet du dark mode avec couleurs adaptées

5. **Actions et rafraîchissement**

   - Rafraîchissement manuel avec bouton dédié
   - Rafraîchissement automatique configurable (5s, 10s, 30s, 60s, ou désactivé)
   - Indicateur de refresh en cours avec animation
   - Bouton "Haut de page" pour navigation rapide
   - Timestamp de dernière mise à jour affiché

6. **Détails d'un log**
   - Clic sur un log pour afficher les détails complets
   - Informations étendues : pathname, lineno, funcName
   - Stack trace formatée pour les exceptions
   - Support des logs multi-lignes avec préservation de la mise en forme
   - **Copie vers presse-papier** : boutons pour copier timestamp, niveau, module, message ou JSON complet
     - Gestion d'erreur avec message de feedback (succès/échec)
     - Toast notification pour confirmer l'action

## Permissions requises

- **Rôle** : Administrateur
- **Permission** : `logs:view`

## Technologies utilisées

- React avec TypeScript pour l'interface
- React hooks (useState, useEffect, useRef) pour la gestion d'état
- Axios pour les appels API
- Tailwind CSS pour le style et les animations
- Lucide React pour les icônes
- Support complet du dark mode
- LocalStorage pour la persistance des préférences utilisateur

## Architecture backend des logs

### Stockage et rétention
- **Redis** : Stockage des logs avec TTL de 24 heures
- **Thread pool** : 8 workers pour l'écriture async non-bloquante
- **Encryption** : Non chiffrés (accessibles uniquement aux admins)
- **Format de clé** : `logs:{level}:{timestamp_ms}` pour tri chronologique

### Optimisations
- Timeouts courts (1s) pour éviter les blocages
- Thread pool dédié pour isolation des opérations Redis
- **Filtrage intelligent des logs HTTP** : patterns spécifiques (GET /admin/logs, POST /admin/logs, etc.)
  - Évite les faux positifs (ex: message contenant "/admin/logs" sans être une requête HTTP)
  - Couvre tous les verbes HTTP : GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS
- Format JSON compact avec tous les champs nécessaires
- Gestion silencieuse des erreurs Redis avec fallback stderr pour debugging

### Logging avec identification PDL
- Fonction helper `log_with_pdl(level, pdl, message)` pour préfixer les logs
- Fonction `log_if_debug(user, level, message, pdl)` pour logs conditionnels
- Format standardisé : `[XXXXXXXXXXXXXX] [TAG] message`
- Application systématique dans `enedis.py` (28+ appels) et `pdl.py` (4+ appels)

## Fichiers liés

- **Frontend** : `apps/web/src/pages/AdminLogs.tsx` (interface principale)
- **API Client** : `apps/web/src/api/admin.ts` (appels API)
- **Types** : `apps/web/src/types/api.ts` (définitions TypeScript)
- **Backend Router** : `apps/api/src/routers/admin.py` (endpoint `/admin/logs`)
- **Logging Config** : `apps/api/src/logging_config.py` (configuration Redis, formatters)
- **Business Logic** : `apps/api/src/routers/enedis.py`, `apps/api/src/routers/pdl.py` (logs avec PDL)

## Navigation

Cette page est accessible via le **menu de navigation supérieur** : **Admin → Logs**

Le menu Admin regroupe toutes les pages d'administration :

- Tableau de bord, Utilisateurs, Offres, TEMPO, EcoWatt, Contributions, Rôles, Logs, Ajouter PDL

## Notes importantes

- Les logs sont critiques pour diagnostiquer les problèmes en production
- Les logs sensibles (mots de passe, tokens) sont automatiquement masqués
- **Rétention** : Les logs sont stockés dans Redis avec un TTL de 24 heures
- Le niveau DEBUG génère beaucoup de logs, à utiliser avec parcimonie (exclu des filtres par défaut)
- **Identification PDL** : Tous les logs liés à un PDL (Point de Livraison) affichent le numéro du PDL en préfixe pour faciliter le debugging
- **Performance** : Le refresh automatique préserve la position de scroll pour ne pas perdre sa place lors de la consultation
  - Protection contre les fuites mémoire avec pruning automatique des timestamps
  - Gestion robuste du cycle de vie du composant (pas d'erreurs après unmount)
- **UX optimisée** : Le header réduit permet d'accéder rapidement aux filtres essentiels sans déplier le panneau complet
- **Badge indicateur** : Un badge animé signale quand des filtres modules sont actifs pour ne pas oublier de les vérifier
- **Copie robuste** : La fonctionnalité de copie vers le presse-papier gère les erreurs avec feedback utilisateur
- **Code quality** : Code conforme aux recommandations Copilot (typage, gestion d'erreurs, optimisations)
