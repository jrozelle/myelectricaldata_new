# Vérification de Design

## 🎯 Directives d'agent

- **Pour l'UX/UI** (interface, composants, design) : Utiliser l'agent **frontend-specialist**
- **Pour le backend** (API, base de données, logique métier) : Utiliser l'agent **backend-specialist**

Utilise l'agent **frontend-specialist** pour vérifier que toutes les pages de l'application respectent les guidelines de design.

## ⚠️ IMPORTANT : Header centralisé

**Le header H1 avec icône et sous-titre est géré de manière centralisée** via :

- `apps/web/src/components/PageHeader.tsx` : Composant de header
- `apps/web/src/components/Layout.tsx` : Intégration du header dans le layout

**NE PAS ajouter de header H1 dans les composants de page** sauf si :

- La page n'est pas listée dans `PDL_SELECTOR_PAGES` de `PageHeader.tsx`
- La page n'a pas de configuration dans `PAGE_CONFIG` de `PageHeader.tsx`

**Vérifier** : Le composant de page doit commencer directement par le contenu, sans header dupliqué.

## Instructions

1. Lire le guide de design : `@docs/design`
2. **Vérifier le header centralisé** : Lire `apps/web/src/components/PageHeader.tsx` pour comprendre la configuration
3. Lister toutes les pages dans `apps/web/src/pages/`
4. Pour chaque page, vérifier la conformité avec les guidelines
5. Produire un rapport avec :
   - Points conformes ✅
   - Points à améliorer ⚠️
   - Problèmes critiques ❌
   - Score de conformité (%)

## Format du Rapport

Pour chaque page :

- Nom et lien vers le fichier
- Numéros de ligne pour les problèmes détectés
- Recommandations de correction avec extraits de code

Résumé final :

- Statistiques globales
- Top 3 des problèmes récurrents
- Priorités de correction
