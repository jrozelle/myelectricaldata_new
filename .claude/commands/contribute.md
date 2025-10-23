# Page Contribuer

Tu travailles sur la page `/contribute` de l'application MyElectricalData.

## Description de la page

Cette page permet aux **utilisateurs de contribuer en ajoutant des offres d'énergie** qui ne sont pas encore dans la base de données.

## Fonctionnalités principales

1. **Formulaire de contribution**
   - Sélection du fournisseur d'énergie
   - Nom de l'offre
   - Type d'offre (BASE, HP/HC, TEMPO)
   - Puissance(s) souscrite(s) compatible(s)
   - Prix de l'abonnement annuel
   - Prix du/des kWh selon le type :
     - **BASE** : 1 tarif unique
     - **HP/HC** : 2 tarifs (Heures Pleines / Heures Creuses)
     - **TEMPO** : 6 tarifs (Bleu HP/HC, Blanc HP/HC, Rouge HP/HC)

2. **Validation des données**
   - Vérification que tous les champs requis sont remplis
   - Validation du format des prix (nombre positif)
   - Vérification de la cohérence des données

3. **Soumission**
   - Envoi de la contribution aux administrateurs
   - Statut de la contribution (en attente, validée, rejetée)
   - Message de confirmation après soumission

4. **Mes contributions**
   - Liste des contributions soumises par l'utilisateur
   - Statut de chaque contribution
   - Commentaires des administrateurs si rejet

5. **Aide et exemples**
   - Explications sur comment remplir le formulaire
   - Exemples de tarifs pour chaque type d'offre
   - Lien vers les sites des fournisseurs

## Modération

- Les contributions sont vérifiées par les administrateurs avant publication
- Les utilisateurs sont notifiés du statut de leurs contributions
- Les contributions validées sont automatiquement ajoutées à la base de données

## Technologies utilisées

- React avec TypeScript
- React Query pour les mutations et le cache
- Tailwind CSS pour le style
- Support du mode sombre

## Fichiers liés

- **Frontend** : `apps/web/src/pages/Contribute.tsx`
- **API** : `apps/web/src/api/contributions.ts`
- **Types** : `apps/web/src/types/api.ts`
- **Backend** : `apps/api/src/routers/contributions.py`

## Notes importantes

- Les contributions aident à enrichir la base de données pour tous les utilisateurs
- Les tarifs doivent être récents et vérifiables
- Les administrateurs peuvent demander des justificatifs (capture d'écran, lien)
- Les contributeurs réguliers peuvent obtenir un badge spécial
