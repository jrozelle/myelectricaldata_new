# Page Administration - Ajouter un PDL

Tu travailles sur la page `/admin/add-pdl` de l'application MyElectricalData.

## Description de la page

Cette page permet aux **administrateurs d'ajouter manuellement un PDL** (Point De Livraison) à un utilisateur sans passer par le consentement Enedis.

## Fonctionnalités principales

1. **Sélection de l'utilisateur**
   - Liste déroulante de tous les utilisateurs
   - Recherche par email ou client_id
   - Affichage des informations de l'utilisateur sélectionné
   - Nombre de PDL existants pour cet utilisateur

2. **Informations du PDL**
   - **Numéro de PDL** (usage_point_id)
     - Validation du format (14 chiffres)
     - Vérification que le PDL n'existe pas déjà
   - **Nom personnalisé** (optionnel)
     - Nom convivial pour identifier le PDL
   - **Puissance souscrite** (en kVA)
     - Sélection parmi les valeurs standard : 3, 6, 9, 12, 15, 18, 24, 30, 36
   - **Heures creuses** (optionnel)
     - Configuration des plages horaires HC
     - Format : tableau de chaînes (ex: ["02:00-07:00", "14:00-16:00"])

3. **Options avancées**
   - **Statut** : Actif/Inactif
   - **Type de consommation**
     - Consommation uniquement
     - Production uniquement
     - Consommation + Production
   - **Date d'activation du contrat** (optionnel)
     - Date à laquelle le contrat a été activé
   - **Date de données la plus ancienne** (optionnel)
     - Permet de limiter les requêtes API

4. **Validation**
   - Vérification du format du numéro PDL
   - Vérification de l'unicité du PDL
   - Validation des heures creuses (format et cohérence)
   - Confirmation avant ajout

5. **Actions post-création**
   - Redirection vers la page du PDL
   - Option pour ajouter un autre PDL
   - Notification de succès

## Cas d'usage

- **Test et développement** : Ajouter des PDL de test
- **Migration de données** : Import de PDL existants
- **Support utilisateur** : Résoudre des problèmes de consentement
- **Situations exceptionnelles** : Cas où le consentement Enedis ne fonctionne pas

## Différences avec le consentement Enedis

| Aspect | Consentement Enedis | Ajout admin |
|--------|-------------------|-------------|
| Données récupérées | Automatique depuis Enedis | Aucune (manuel) |
| Validation | Par Enedis | Par l'admin |
| Puissance souscrite | Auto-détectée | Saisie manuelle |
| Heures creuses | Auto-détectées | Saisie manuelle |

## Permissions requises

- **Rôle** : Administrateur uniquement
- **Permission** : `pdl:create`, `admin:manage`

## Technologies utilisées

- React avec TypeScript
- React Query pour les mutations
- Tailwind CSS pour le style
- Support du mode sombre

## Fichiers liés

- **Frontend** : `apps/web/src/pages/AdminAddPDL.tsx`
- **API** : `apps/web/src/api/admin.ts`, `apps/web/src/api/pdl.ts`
- **Types** : `apps/web/src/types/api.ts`
- **Backend** : `apps/api/src/routers/admin.py`, `apps/api/src/routers/pdl.py`

## Navigation

Cette page est accessible via le **menu de navigation supérieur** : **Admin → Ajouter PDL**

Le menu Admin regroupe toutes les pages d'administration :
- Tableau de bord, Utilisateurs, Offres, TEMPO, EcoWatt, Contributions, Rôles, Logs, Ajouter PDL

## Notes importantes

- Cette fonctionnalité est réservée aux administrateurs et doit être utilisée avec précaution
- Les PDL ajoutés manuellement n'ont pas de données de consommation automatiques
- Il faut ensuite déclencher manuellement la récupération des données via l'API Enedis
- Le numéro de PDL doit être valide et existant chez Enedis
- Les heures creuses doivent correspondre au contrat réel de l'utilisateur
