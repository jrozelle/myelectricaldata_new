# Vérification de Design

## 🎯 Directives d'agent

- **Pour l'UX/UI** (interface, composants, design) : Utiliser l'agent **frontend-specialist**
- **Pour le backend** (API, base de données, logique métier) : Utiliser l'agent **backend-specialist**

Utilise l'agent **frontend-specialist** pour vérifier que toutes les pages de l'application respectent les guidelines de design.

## Instructions

1. Lire le guide de design : `@docs/design`
2. Lister toutes les pages dans `apps/web/src/pages/`
3. Pour chaque page, vérifier la conformité avec les guidelines
4. Produire un rapport avec :
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
