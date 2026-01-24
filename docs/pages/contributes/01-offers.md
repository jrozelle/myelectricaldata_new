---
name: offers
slug: /contribute/offers
description: Onglet offers des contribution
mode_client: false
mode_server: true
menu: Contribuer
tab: Toutes les offres
---

# Onglet "Toutes les offres" (AllOffers)

Fichier : `apps/web/src/pages/Contribute/components/tabs/AllOffers.tsx`

## Features

| Feature                          | Statut |
| -------------------------------- | ------ |
| Mode lecture/edition             | FAIT   |
| Filtre par fournisseur           | FAIT   |
| Filtre par type d'offre          | FAIT   |
| Edition inline des offres        | FAIT   |
| Suppression de puissance         | FAIT   |
| Ajout de puissance               | FAIT   |
| Recapitulatif avant soumission   | FAIT   |
| Soumission des modifications     | FAIT   |

## Details implementation

### Mode lecture/edition (FAIT)

- **Mode lecture** (par defaut) : Affichage simple des offres en lecture seule
- **Mode edition** : Permet de modifier les tarifs, supprimer et ajouter des puissances
- Bouton "Proposer des modifications" en haut a droite pour passer en mode edition
- Bouton "Mode lecture" pour revenir au mode lecture (reset toutes les modifications)
- Encadre d'information en mode edition rappelant :
  - Selectionner un fournisseur et un type d'offre
  - Chaque soumission concerne un seul fournisseur/type a la fois

**UI :**

- Bouton mode lecture : `bg-gray-100 dark:bg-gray-700`
- Bouton mode edition : `bg-primary-600 text-white`
- Encadre info : `bg-blue-50 dark:bg-blue-900/20 border-blue-200`

### Filtre par fournisseur (FAIT)

- Boutons pour selectionner un fournisseur
- EDF affiche en premier par defaut
- Compteur d'offres par fournisseur

### Filtre par type d'offre (FAIT)

- Boutons dynamiques selon le fournisseur selectionne
- Types supportes : BASE, HC_HP, TEMPO, EJP, ZEN_FLEX, ZEN_WEEK_END, SEASONAL
- Reset automatique quand on change de fournisseur

### Edition inline des offres (FAIT)

- Champs input type="number" avec step="0.0001"
- Highlight jaune/ambre quand une valeur est modifiee
- Badge "Modifie" sur l'offre
- Champs selon le type d'offre :
  - BASE : Abonnement, Prix Base
  - HC_HP : Abonnement, HC, HP
  - TEMPO : Abonnement, Bleu HC/HP, Blanc HC/HP, Rouge HC/HP
  - EJP : Abonnement, Normal, Pointe
  - ZEN_FLEX : Abonnement, Eco HC/HP, Sobriete HC/HP
  - ZEN_WEEK_END : Abonnement, HC, HP, Week-end HC/HP
  - SEASONAL : Abonnement, Hiver HC/HP, Ete HC/HP

### Suppression de puissance (FAIT)

Permet de proposer la suppression d'une puissance existante pour un fournisseur/type d'offre.

- Icone corbeille rouge sur chaque ligne d'offre
- Clic sur la corbeille marque la puissance pour suppression
- Ligne devient rouge avec opacite reduite et texte barre
- Badge "A supprimer" affiche sur la ligne
- Icone annulation (Undo) pour annuler la suppression
- Reset automatique quand on change de fournisseur ou type d'offre

**UI :**

- Bouton corbeille : `text-red-500 dark:text-red-400`
- Ligne marquee : `border-red-400 bg-red-50 opacity-60`
- Badge : `text-red-600 bg-red-100`

**Soumission :**

- Type de contribution : `UPDATE_OFFER`
- Nom de l'offre prefixe avec `[SUPPRESSION]`
- Description : "Demande de suppression de la puissance X kVA pour Fournisseur (Type)"

**Backend (approbation) :**

Quand l'admin approuve une contribution de suppression :

1. Le backend detecte le prefixe `[SUPPRESSION]` dans `offer_name`
2. Recherche l'offre par `provider_id`, `offer_type` et `power_kva`
3. Supprime l'offre de la base de donnees

### Ajout de puissance (FAIT)

Permet de proposer l'ajout de plusieurs nouvelles puissances pour un fournisseur/type d'offre existant.

**Fonctionnement :**

- Bouton "Ajouter une puissance" en bas de la liste des offres
- Chaque clic ajoute une nouvelle ligne verte au-dessus du bouton
- Possibilite d'ajouter plusieurs puissances en une seule soumission
- Chaque ligne contient :
  - Champ de saisie pour la puissance (kVA) - input number
  - Champs de tarification selon le type d'offre
  - Bouton X pour supprimer cette ligne
- Badge "Nouveau" sur chaque ligne ajoutee
- Reset automatique quand on change de fournisseur ou type d'offre

**Champs de tarification selon le type d'offre :**

- BASE : Abonnement (€/mois), Base (€/kWh)
- HC_HP : Abonnement (€/mois), HC (€/kWh), HP (€/kWh)
- TEMPO : Abonnement uniquement (tarifs specifiques apres validation)
- Autres types : Abonnement uniquement (tarifs specifiques apres validation)

**UI :**

- Conteneur : `bg-green-50 dark:bg-green-900/20`
- Bordure : `border-dashed border-green-300` (vide) ou `border-green-400` (avec donnees)
- Icone + : `text-green-600 dark:text-green-400`
- Champs : bordure verte `border-green-300 dark:border-green-600`

**Soumission :**

- Type de contribution : `NEW_OFFER`
- `existing_provider_id` : ID du fournisseur selectionne
- `power_kva` : puissance saisie
- `pricing_data` : tarifs saisis (subscription_price, base_price, hc_price, hp_price)
- Description : "Ajout de la puissance X kVA pour Fournisseur (Type)"

### Recapitulatif avant soumission (FAIT)

- Section recapitulative affichee quand des modifications existent
- Affiche les modifications de tarifs avec ancienne/nouvelle valeur
- Affiche les modifications de puissances dans une section dediee :
  - Suppressions en rouge avec icone corbeille
  - Ajouts en vert avec icone + et details des tarifs saisis (supporte plusieurs ajouts)
- Champ lien vers la fiche tarifaire officielle :
  - Obligatoire pour les utilisateurs standards
  - Optionnel pour les admins/moderateurs
- Boutons "Annuler les modifications" et "Envoyer les contributions"

**Recap ajout de puissance :**

Le recapitulatif affiche les informations completes :

- Puissance en kVA
- Abonnement en €/mois (si renseigne)
- Tarif Base en €/kWh (si renseigne)
- Tarif HC en €/kWh (si renseigne, couleur bleue)
- Tarif HP en €/kWh (si renseigne, couleur rouge)

### Soumission des modifications (FAIT)

- Types de contribution :
  - `UPDATE_OFFER` : modification de tarifs existants ou demande de suppression
  - `NEW_OFFER` : ajout d'une nouvelle puissance (une contribution par puissance ajoutee)
- Toast de succes/erreur apres soumission
- Invalidation du cache `my-contributions`
- Reset des modifications apres succes (editedOffers, priceSheetUrl, powersToRemove, newPowersData)

## State management

```typescript
// Mode lecture (false) ou edition (true)
const [isEditMode, setIsEditMode] = useState(false)

// Editions de tarifs existants
const [editedOffers, setEditedOffers] = useState<Record<string, Record<string, string>>>({})

// Puissances a supprimer
const [powersToRemove, setPowersToRemove] = useState<number[]>([])

// Nouvelles puissances a ajouter avec leurs tarifs (supporte plusieurs ajouts)
const [newPowersData, setNewPowersData] = useState<Array<{
  power: number
  fields: Record<string, string>
}>>([])

// URL de la fiche tarifaire (obligatoire sauf admin/moderateur)
const [priceSheetUrl, setPriceSheetUrl] = useState('')
```

## API utilisee

- `energyApi.getProviders()` : liste des fournisseurs
- `energyApi.getOffers()` : liste des offres
- `energyApi.submitContribution()` : soumission d'une contribution

## Flux utilisateur

1. Consulter les offres en mode lecture (par defaut)
2. Cliquer sur "Proposer des modifications" pour passer en mode edition
3. Selectionner un fournisseur (boutons)
4. Selectionner un type d'offre (boutons)
5. Effectuer les modifications souhaitees :
   - Modifier les tarifs existants (champs inline)
   - Marquer des puissances pour suppression (icone corbeille)
   - Ajouter une ou plusieurs puissances (bouton "Ajouter une puissance")
6. Renseigner le lien vers la fiche tarifaire officielle (optionnel pour admin/moderateur)
7. Cliquer sur "Envoyer les contributions"
8. Les contributions sont soumises et apparaissent dans "Mes contributions"
