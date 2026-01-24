---
globs:
  - apps/**/*
  - docker-compose*.yml
  - Makefile
---

# Developpement

## Agents specialises

**Utiliser les agents selon le contexte :**

- **Frontend** (`apps/web/`) : Utiliser l'agent `frontend-specialist`
- **Backend** (`apps/api/`) : Utiliser l'agent `backend-specialist`

## Modes d'execution

**Ce projet supporte deux modes qui peuvent tourner en parallele.**

| Mode       | Docker Compose               | Ports           | Description                       |
| ---------- | ---------------------------- | --------------- | --------------------------------- |
| **Serveur** | `docker-compose.yml`         | 8000 / 8081     | Gateway multi-users, Enedis direct |
| **Client** | `docker-compose.client.yml`  | 8100 / 8181     | Installation locale mono-user     |

### Demarrage par mode

```bash
# Mode Serveur (defaut)
make up                    # ou docker compose up -d

# Mode Client
docker compose -f docker-compose.client.yml up -d
```

### Logs par mode

**En developpement local, les logs Docker sont facilement accessibles :**

```bash
# Mode Serveur
make logs                  # Tous les services
make backend-logs          # Backend uniquement
docker compose logs -f     # Equivalent

# Mode Client
docker compose -f docker-compose.client.yml logs -f
docker compose -f docker-compose.client.yml logs -f backend
docker compose -f docker-compose.client.yml logs -f frontend
```

**Astuce** : Les logs sont en temps reel grace au flag `-f` (follow). Tres utile pour debugger car les erreurs Python/TypeScript apparaissent instantanement.

## Acces par mode

### Mode Serveur

| Service     | URL                          |
| ----------- | ---------------------------- |
| Frontend    | <http://localhost:8000>      |
| Backend API | <http://localhost:8081>      |
| API Docs    | <http://localhost:8081/docs> |
| pgAdmin     | <http://localhost:5050>      |

### Mode Client

| Service     | URL                          |
| ----------- | ---------------------------- |
| Frontend    | <http://localhost:8100>      |
| Backend API | <http://localhost:8181>      |
| API Docs    | <http://localhost:8181/docs> |

## Auto-reload actif

**Les services sont en auto-reload. NE PAS redemarrer apres modification de code.**

- **Backend** : Uvicorn `--reload` detecte les changements Python
- **Frontend** : Vite HMR recharge instantanement les composants React

**Redemarrage necessaire uniquement si** :

- Modification `.env.api`, `.env.client` ou `.env`
- Ajout dependances (`pyproject.toml`, `package.json`)
- Modification `docker-compose*.yml` ou `Dockerfile`

## Commandes principales

### Mode Serveur (Makefile)

```bash
# Demarrage
make dev              # Start dev avec hot-reload
make up               # Start tous les services
make down             # Stop tous les services

# Logs
make logs             # Tous les logs
make backend-logs     # Logs backend uniquement

# Database
make migrate          # Appliquer migrations
make migrate-revision # Generer nouvelle migration
make db-shell         # Shell PostgreSQL

# Backend (apps/api/)
make lint             # ruff + mypy
make test             # pytest avec coverage

# Frontend (apps/web/)
npm run lint          # ESLint
npm run build         # Build production
```

### Mode Client (commandes directes)

```bash
# Demarrage
docker compose -f docker-compose.client.yml up -d

# Arret
docker compose -f docker-compose.client.yml down

# Logs
docker compose -f docker-compose.client.yml logs -f

# Rebuild apres modification Dockerfile
docker compose -f docker-compose.client.yml up -d --build
```

## Validation

**En fin de traitement, toujours verifier les logs Docker pour valider que tout est OK :**

```bash
# Mode Serveur
make backend-logs     # Verifier pas d'erreurs backend

# Mode Client
docker compose -f docker-compose.client.yml logs -f backend

# Verifier les conteneurs actifs
docker ps             # Liste tous les conteneurs
```

**Indicateurs d'erreur a surveiller :**

- `ERROR` ou `CRITICAL` dans les logs Python
- Erreurs TypeScript/ESLint dans les logs frontend
- Codes HTTP 500 dans les requetes API

## Documentation

**En cas de changement de fonctionnement, mettre a jour la documentation :**

| Scope        | Emplacement                  |
| ------------ | ---------------------------- |
| Mode Serveur | `docs/`                      |
| Mode Client  | `docs/local-client/`         |
| Pages UI     | `docs/pages/`                |
| Design       | `docs/design/`               |
| API Enedis   | `docs/enedis-api/`           |
