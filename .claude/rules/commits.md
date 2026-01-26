# Commits et Semantic Release

**IMPORTANT : Ce projet utilise semantic-release. Les messages de commit doivent respecter la convention Conventional Commits.**

## Format obligatoire

```text
<type>(<scope>): <description>

[body optionnel]

[footer optionnel]
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

## Types et impact sur la version

| Type       | Description                                      | Version bump |
| ---------- | ------------------------------------------------ | ------------ |
| `feat`     | Nouvelle fonctionnalite                          | **MINOR**    |
| `fix`      | Correction de bug                                | **PATCH**    |
| `perf`     | Amelioration des performances                    | **PATCH**    |
| `docs`     | Documentation uniquement                         | Aucun        |
| `style`    | Formatage (pas de changement de code)            | Aucun        |
| `refactor` | Refactorisation sans changement fonctionnel      | Aucun        |
| `test`     | Ajout ou modification de tests                   | Aucun        |
| `chore`    | Maintenance, dependencies, config                | Aucun        |
| `ci`       | Configuration CI/CD                              | Aucun        |
| `build`    | Systeme de build, dependencies externes          | Aucun        |

## Breaking Changes (MAJOR)

Pour une version MAJOR, ajouter `!` apres le type ou `BREAKING CHANGE:` dans le footer :

```text
feat!: nouvelle API incompatible avec l'ancienne

BREAKING CHANGE: L'endpoint /api/v1/data est remplace par /api/v2/data
```

## Scopes recommandes

| Scope        | Usage                                |
| ------------ | ------------------------------------ |
| `api`        | Backend FastAPI                      |
| `web`        | Frontend React                       |
| `contribute` | Page Contribuer                      |
| `dashboard`  | Page Dashboard                       |
| `tempo`      | Fonctionnalites Tempo                |
| `ecowatt`    | Fonctionnalites EcoWatt              |
| `admin`      | Pages administration                 |
| `auth`       | Authentification                     |
| `db`         | Base de donnees, migrations          |
| `docker`     | Docker, docker-compose               |
| `deps`       | Dependencies                         |

## Exemples

```bash
# Nouvelle fonctionnalite (MINOR: 1.0.0 → 1.1.0)
feat(contribute): ajouter filtrage par fournisseur

# Correction de bug (PATCH: 1.1.0 → 1.1.1)
fix(api): corriger validation des dates Enedis

# Breaking change (MAJOR: 1.1.1 → 2.0.0)
feat(api)!: migrer vers API v2

# Documentation (pas de version bump)
docs(contribute): mettre a jour le guide utilisateur

# Refactorisation (pas de version bump)
refactor(web): extraire composant ContributionCard
```

## Verification

Avant de commiter, verifier que le message :

- [ ] Commence par un type valide
- [ ] A un scope entre parentheses (recommande)
- [ ] A une description en minuscules
- [ ] N'a pas de point a la fin de la description
- [ ] Inclut `Co-Authored-By` si genere par Claude
