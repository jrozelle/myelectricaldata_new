# Production

**Route:** `/production`

Voir la spécification complète dans `.claude/commands/production.md` pour tous les détails techniques.

## Description

Page équivalente à `/consumption` mais pour la **production d'énergie solaire**.

## Différences avec /consumption

### Retiré
- ❌ Puissance maximum
- ❌ HC/HP (heures creuses/pleines)
- ❌ Section PowerPeaks
- ❌ Composants HcHpDistribution et MonthlyHcHp

### Conservé
- ✅ Données journalières (3 ans max)
- ✅ Données détaillées (2 ans max, intervalles 30min)
- ✅ Graphiques annuels (production par année)
- ✅ Courbe de charge détaillée (par jour)
- ✅ Cache day-by-day
- ✅ Auto-load pour démo
- ✅ Sections always-visible

## Fonctionnalités principales

### 1. Configuration
- Sélecteur PDL (filtrés sur `has_production = true`)
- Bouton "Récupérer 3 ans d'historique de production"
- LoadingProgress (2 tâches : Quotidien + Détaillé)

### 2. Statistiques de production
- Cartes par année (kWh produits)
- Total production sur 3 périodes glissantes

### 3. Graphiques de production
- Production mensuelle par année
- Courbe annuelle de production

### 4. Courbe de production détaillée
- Graphique 30min par jour
- Navigation par semaine
- Total journalier en kWh

## Technologies

- React avec TypeScript
- React Query
- Recharts
- Tailwind CSS

## Fichiers liés

- **Frontend** : `apps/web/src/pages/Production/`
- **Hooks** : `useProductionData.ts`, `useProductionFetch.ts`, `useProductionCalcs.ts`
- **API** : `apps/web/src/api/enedis.ts`
- **Backend** : `apps/api/src/routers/enedis.py`

## État actuel

✅ Structure créée et complète
✅ Hooks implémentés (sans puissance ni HC/HP)
✅ Page principale fonctionnelle
✅ Route et navigation configurées (icône Sun ☀️)
⚠️ Graphiques détaillés à implémenter
