# Page Tableau de bord

Tu travailles sur la page `/dashboard` de l'application MyElectricalData.

## Description de la page

Cette page est le **tableau de bord principal** où les utilisateurs peuvent gérer leurs Points De Livraison (PDL) et accéder à leurs données Enedis.

## Fonctionnalités principales

1. **Gestion des PDL**
   - Liste de tous les PDL de l'utilisateur
   - Affichage des PDL actifs et inactifs
   - Filtrage : afficher/masquer les PDL inactifs
   - Tri par ordre personnalisé (drag & drop)
   - Informations affichées par PDL :
     - Nom personnalisé ou numéro de PDL
     - Puissance souscrite
     - Heures creuses configurées
     - Statut (actif/inactif)

2. **Actions sur les PDL**
   - Éditer le nom, la puissance souscrite et les heures creuses
   - Activer/Désactiver un PDL
   - Supprimer un PDL (avec confirmation)
   - Réorganiser l'ordre d'affichage (drag & drop)

3. **Consentement Enedis**
   - Bouton "Démarrer le consentement Enedis"
   - Redirection vers le portail OAuth Enedis
   - Gestion du callback après autorisation
   - Ajout automatique du PDL après consentement réussi

4. **Notifications**
   - Messages de succès/erreur pour les actions
   - Affichage automatique après redirection OAuth
   - Disparition automatique après 10 secondes

5. **Statistiques**
   - Nombre de PDL actifs
   - Nombre de PDL inactifs
   - Nombre total de PDL

## Composants utilisés

- **PDLCard** : Carte affichant les informations d'un PDL
- **PDLEditModal** : Modal pour éditer un PDL
- **DeleteConfirmModal** : Modal de confirmation de suppression

## Technologies utilisées

- React avec TypeScript
- React Query pour les mutations et le cache
- React Beautiful DnD pour le drag & drop
- Tailwind CSS pour le style
- Support du mode sombre

## Fichiers liés

- **Frontend** : `apps/web/src/pages/Dashboard.tsx`
- **Composants** : `apps/web/src/components/PDLCard.tsx`, `apps/web/src/components/PDLEditModal.tsx`
- **API** : `apps/web/src/api/pdl.ts`, `apps/web/src/api/oauth.ts`
- **Types** : `apps/web/src/types/api.ts`
- **Backend** : `apps/api/src/routers/pdl.py`, `apps/api/src/routers/oauth.py`

## Notes importantes

- Les PDL peuvent être activés/désactivés sans être supprimés
- L'ordre d'affichage est persistant et synchronisé avec le backend
- Le consentement Enedis est requis pour ajouter un nouveau PDL
- Les heures creuses peuvent être au format tableau ou objet (legacy)
- Le champ `is_active` est optionnel (par défaut considéré comme `true`)
