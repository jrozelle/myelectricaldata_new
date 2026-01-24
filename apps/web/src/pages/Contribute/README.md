# Page Contribuer - Structure

Cette page permet aux utilisateurs de contribuer en ajoutant ou mettant à jour des offres d'énergie.

## Structure des dossiers

```
Contribute/
├── components/          # Composants UI
│   ├── tabs/           # Composants des onglets
│   │   ├── NewContribution.tsx      # Formulaire de nouvelle contribution
│   │   ├── MyContributions.tsx      # Liste des contributions de l'utilisateur
│   │   └── AllOffers.tsx            # Édition inline des offres existantes
│   ├── forms/          # Composants de formulaires
│   │   └── PowerVariantForm.tsx     # Formulaire pour les variantes de puissance
│   ├── cards/          # Composants de cartes
│   │   └── ContributionCard.tsx     # Affichage d'une contribution
│   └── index.ts        # Barrel export
├── hooks/              # Hooks React personnalisés
│   ├── useContributions.ts          # Récupération des contributions
│   ├── useProviders.ts              # Récupération des fournisseurs
│   ├── useOffers.ts                 # Récupération des offres
│   ├── useContributionForm.ts       # Gestion du formulaire
│   └── index.ts        # Barrel export
├── types/              # Types TypeScript
│   ├── contribute.types.ts          # Définitions de types
│   └── index.ts        # Barrel export
├── utils/              # Fonctions utilitaires
│   ├── contribute.utils.ts          # Fonctions helpers
│   └── index.ts        # Barrel export
├── index.tsx           # Composant principal
└── README.md           # Documentation (ce fichier)
```

## Composants principaux

### NewContribution

Formulaire pour soumettre une nouvelle offre ou un nouveau fournisseur.

**Fonctionnalités** :

- Choix du type de contribution (nouvelle offre / nouveau fournisseur)
- Formulaire adaptatif selon le type d'offre (BASE, HC/HP, TEMPO, etc.)
- Support des variantes de puissance (3, 6, 9, 12 kVA, etc.)
- Import JSON pour batch d'offres
- Édition de contributions existantes

### MyContributions

Liste des contributions de l'utilisateur avec accordéons par statut.

**Fonctionnalités** :

- Groupement par statut (en attente / approuvées / rejetées)
- Chat WhatsApp-style pour communiquer avec les admins
- Édition des contributions en attente ou rejetées
- Rafraîchissement auto toutes les 10 secondes

### AllOffers

Interface d'édition inline des offres existantes pour soumettre des mises à jour de tarifs.

**Fonctionnalités** :

- Filtrage par fournisseur et type d'offre
- Édition inline des prix
- Récapitulatif des modifications avant envoi
- Soumission groupée de contributions

## Hooks personnalisés

### useContributions

Récupère les contributions de l'utilisateur depuis l'API.

```tsx
const { contributions, isLoading, error, invalidateContributions } = useContributions()
```

### useProviders

Récupère la liste des fournisseurs d'énergie.

```tsx
const { providers, isLoading, error } = useProviders()
```

### useOffers

Récupère toutes les offres d'énergie disponibles.

```tsx
const { offers, isLoading, error } = useOffers()
```

### useContributionForm

Gère l'état du formulaire de contribution.

```tsx
const { formState, setFormState, handleFormStateChange, resetForm } = useContributionForm()
```

## Types principaux

### PowerVariant

Représente une variante de puissance pour une offre.

```typescript
interface PowerVariant {
  power_kva: number
  subscription_price: number
  pricing_data?: {
    base_price?: number
    hc_price?: number
    hp_price?: number
    tempo_blue_hc?: number
    // ... autres prix selon le type d'offre
  }
}
```

### TabType

Type des onglets de la page.

```typescript
type TabType = 'new' | 'mine' | 'offers'
```

## Utilitaires

### formatPrice

Formate un prix en euros avec 4 décimales.

```typescript
formatPrice(0.1234) // "0.1234 €/kWh"
```

### getOfferTypeLabel

Retourne le label français d'un type d'offre.

```typescript
getOfferTypeLabel('HC_HP') // "Heures Creuses / Heures Pleines"
```

## Flux de données

```
index.tsx (état global)
    ↓
TabNavigation (navigation)
    ↓
NewContribution / MyContributions / AllOffers (onglets)
    ↓
Hooks (useContributions, useProviders, useOffers)
    ↓
API (@/api/energy)
```

## Conventions

1. **Imports relatifs** : Utiliser `../../` pour remonter vers la racine de `Contribute/`
2. **Barrel exports** : Importer depuis `./components` et `./hooks` plutôt que des chemins directs
3. **Props typées** : Toujours définir les interfaces pour les props
4. **Naming** : PascalCase pour les composants, camelCase pour les fonctions
