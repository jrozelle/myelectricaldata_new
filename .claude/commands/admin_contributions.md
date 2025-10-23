# Page Administration - Gestion des contributions

Tu travailles sur la page `/admin/contributions` de l'application MyElectricalData.

## Description de la page

Cette page permet aux **administrateurs de modérer les contributions d'offres d'énergie** soumises par les utilisateurs.

## Fonctionnalités principales

1. **Liste des contributions**
   - Tableau avec toutes les contributions
   - Colonnes affichées :
     - Date de soumission
     - Utilisateur contributeur
     - Fournisseur
     - Nom de l'offre
     - Type (BASE, HP/HC, TEMPO)
     - Statut (En attente, Validée, Rejetée)
     - Actions

2. **Filtrage et tri**
   - Filtre par statut (en attente, validées, rejetées)
   - Filtre par fournisseur
   - Filtre par type d'offre
   - Tri par date de soumission
   - Recherche par nom d'offre ou utilisateur

3. **Détails d'une contribution**
   - Vue complète de l'offre proposée
   - Informations du contributeur
   - Tarifs détaillés selon le type
   - Puissances compatibles
   - Commentaires de l'utilisateur (si fournis)

4. **Validation d'une contribution**
   - Vérification des tarifs
   - Comparaison avec les offres existantes
   - Détection des doublons
   - Bouton "Valider et publier"
   - Possibilité de modifier avant validation
   - Notification envoyée au contributeur

5. **Rejet d'une contribution**
   - Raisons de rejet prédéfinies :
     - Tarifs incorrects
     - Offre déjà existante
     - Informations incomplètes
     - Source non vérifiable
     - Autre (avec commentaire libre)
   - Message personnalisé au contributeur
   - Notification envoyée au contributeur

6. **Modification avant validation**
   - Correction des erreurs mineures
   - Ajustement des tarifs
   - Ajout d'informations manquantes
   - Conservation du crédit pour le contributeur

7. **Statistiques**
   - Nombre de contributions en attente
   - Nombre de contributions validées ce mois
   - Nombre de contributions rejetées
   - Top contributeurs
   - Temps moyen de traitement

8. **Actions en masse**
   - Sélection multiple de contributions
   - Validation/rejet en masse
   - Export des contributions

## Workflow de modération

1. Utilisateur soumet une contribution via `/contribute`
2. Contribution apparaît avec statut "En attente"
3. Administrateur examine la contribution
4. Administrateur valide, modifie ou rejette
5. Utilisateur reçoit une notification du résultat
6. Si validée, l'offre est ajoutée à la base de données

## Permissions requises

- **Rôle** : Administrateur
- **Permission** : `contributions:manage`

## Technologies utilisées

- React avec TypeScript
- React Query pour les mutations et le cache
- Tailwind CSS pour le style
- Support du mode sombre

## Fichiers liés

- **Frontend** : `apps/web/src/pages/AdminContributions.tsx`
- **API** : `apps/web/src/api/contributions.ts`, `apps/web/src/api/admin.ts`
- **Types** : `apps/web/src/types/api.ts`
- **Backend** : `apps/api/src/routers/contributions.py`

## Navigation

Cette page est accessible via le **menu de navigation supérieur** : **Admin → Contributions**

Le menu Admin regroupe toutes les pages d'administration :
- Tableau de bord, Utilisateurs, Offres, TEMPO, EcoWatt, Contributions, Rôles, Logs, Ajouter PDL

## Notes importantes

- Les contributions permettent d'enrichir la base de données collaborativement
- Les tarifs doivent être vérifiés avant validation (site du fournisseur)
- Les contributeurs réguliers peuvent obtenir des badges
- Un historique des modifications est conservé
- Les rejets doivent être justifiés pour aider le contributeur
