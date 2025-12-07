# Synchronisation Fournisseur PDL - staleTime

## 🎯 Problème

Le fournisseur d'énergie sélectionné pour un PDL n'apparaît pas immédiatement après avoir été configuré dans le Dashboard. L'utilisateur doit rafraîchir la page manuellement pour voir le fournisseur sur les pages `/consumption_euro` et `/dashboard`.

**Symptômes:**
- Fournisseur configuré dans le Dashboard mais absent sur `/consumption_euro`
- Rafraîchissement manuel (F5) nécessaire pour voir les changements
- Problème intermittent selon la navigation

## 🔍 Cause Root

La configuration globale de React Query dans `main.tsx` avait un `staleTime` de **24 heures** :

```typescript
// main.tsx - Configuration globale
defaultOptions: {
  queries: {
    staleTime: 1000 * 60 * 60 * 24, // 24 hours
    refetchOnWindowFocus: false,
  }
}
```

Cela signifie que les données en cache sont considérées comme "fraîches" pendant 24h et ne se re-fetchent pas automatiquement.

### Séquence du problème

1. **Dashboard** : L'utilisateur modifie le fournisseur dans `PDLCard`
2. **Mutation** : `updateSelectedOfferMutation` appelle `queryClient.invalidateQueries({ queryKey: ['pdls'] })`
3. **Navigation** : L'utilisateur va sur `/consumption_euro`
4. **Cache stale** : La requête `['pdls']` dans `ConsumptionEuro` hérite du `staleTime` global de 24h
5. **Pas de refetch** : Même si le cache est invalidé, React Query ne refetch pas car les données sont encore dans le `staleTime`
6. **Ancien fournisseur affiché** : L'utilisateur voit les anciennes données

### Pourquoi Dashboard fonctionnait ?

Dashboard avait déjà un override explicite :

```typescript
// Dashboard.tsx
const { data: pdlsData } = useQuery({
  queryKey: ['pdls'],
  // ...
  staleTime: 30 * 1000, // 30 seconds - Override explicite
})
```

## ✅ Solution

Ajouter `staleTime: 30 * 1000` (30 secondes) à toutes les requêtes `['pdls']` pour assurer une cohérence :

```typescript
const { data: pdlsData } = useQuery({
  queryKey: ['pdls'],
  queryFn: async () => {
    const response = await pdlApi.list()
    if (response.success && Array.isArray(response.data)) {
      return response.data as PDL[]
    }
    return []
  },
  staleTime: 30 * 1000, // 30 seconds - same as Dashboard for consistency
})
```

## 📁 Fichiers Corrigés

| Fichier | Description |
|---------|-------------|
| `apps/web/src/pages/ConsumptionEuro/index.tsx` | Page coûts en euros |
| `apps/web/src/pages/ConsumptionKwh/index.tsx` | Page consommation kWh |
| `apps/web/src/pages/ConsumptionKwh/hooks/useConsumptionData.ts` | Hook données consommation |
| `apps/web/src/pages/Production/hooks/useProductionData.ts` | Hook données production |
| `apps/web/src/pages/Simulator.tsx` | Simulateur d'offres |

## 🧪 Validation

1. Aller sur `/dashboard`
2. Sélectionner un fournisseur pour un PDL via `OfferSelector`
3. Naviguer vers `/consumption_euro` sans rafraîchir
4. ✅ Le fournisseur doit apparaître immédiatement

## 💡 Bonnes Pratiques

### Quand utiliser un staleTime court ?

| Cas d'usage | staleTime recommandé |
|-------------|---------------------|
| Données utilisateur modifiables (PDLs, settings) | 30 secondes |
| Données de référence (providers, offers) | 5 minutes |
| Données read-only persistées | Infinity |
| Données temps réel (admin stats) | 0 (toujours refetch) |

### Pattern recommandé pour les PDLs

```typescript
// Toujours utiliser ce pattern pour les queries ['pdls']
const { data: pdlsData } = useQuery({
  queryKey: ['pdls'],
  queryFn: async () => {
    const response = await pdlApi.list()
    if (response.success && Array.isArray(response.data)) {
      return response.data as PDL[]
    }
    return []
  },
  staleTime: 30 * 1000, // Cohérent avec Dashboard
})
```

## 🔗 Références

- [React Query staleTime](https://tanstack.com/query/latest/docs/react/guides/important-defaults)
- [React Query invalidateQueries](https://tanstack.com/query/latest/docs/reference/QueryClient#queryclientinvalidatequeries)
- Configuration globale : `apps/web/src/main.tsx`
