---
globs: apps/web/**/*
---

# Notifications Frontend

**IMPORTANT : Les notifications sont gerees par un module dedie. Ne JAMAIS creer de systeme de notification ad-hoc.**

## Module existant

| Fichier                                    | Role                                   |
| ------------------------------------------ | -------------------------------------- |
| `apps/web/src/stores/notificationStore.ts` | Store Zustand + helpers `toast.*`      |
| `apps/web/src/components/Toast.tsx`        | Composant d'affichage (ToastContainer) |

## Utilisation OBLIGATOIRE

```tsx
// Import
import { toast } from "@/stores/notificationStore";

// Notifications simples
toast.success("Operation reussie");
toast.error("Une erreur est survenue");
toast.warning("Attention");
toast.info("Information");
toast.loading("Chargement en cours...");

// Avec options
toast.success("Sauvegarde effectuee", { duration: 3000 });
toast.error("Erreur critique", { dismissible: false });

// Gestion manuelle (loading -> success/error)
const loadingId = toast.loading("Traitement...");
// ... operation async
toast.dismiss(loadingId);
toast.success("Termine !");
```

## Types disponibles

| Type      | Duree par defaut | Auto-dismiss |
| --------- | ---------------- | ------------ |
| `success` | 4000ms           | Oui          |
| `error`   | 6000ms           | Oui          |
| `warning` | 5000ms           | Oui          |
| `info`    | 4000ms           | Oui          |
| `loading` | -                | Non (manuel) |

## Anti-patterns (INTERDIT)

```tsx
// NE PAS faire
const [showSuccess, setShowSuccess] = useState(false)  // INTERDIT
alert('Operation reussie')                              // INTERDIT
console.log('Erreur:', error)                          // INTERDIT (pour feedback user)
window.alert(...)                                       // INTERDIT

// FAIRE
toast.success('Operation reussie')
toast.error('Erreur: ' + error.message)
```

## Setup

Le `ToastContainer` est deja integre dans `Layout.tsx`. Aucune configuration supplementaire n'est necessaire.

## Bonnes pratiques

1. **Messages clairs** : Utiliser des messages comprehensibles par l'utilisateur final
2. **Type adapte** : `error` pour erreurs, `warning` pour alertes, `info` pour informations
3. **Loading pattern** : Pour operations longues, utiliser `loading` puis `dismiss` + `success/error`
4. **Pas de duplication** : Ne pas afficher plusieurs notifications pour la meme action
