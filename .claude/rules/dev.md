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

## Auto-reload actif

**Les services sont en auto-reload. NE PAS redemarrer apres modification de code.**

- **Backend** : Uvicorn `--reload` detecte les changements Python
- **Frontend** : Vite HMR recharge instantanement les composants React

**Redemarrage necessaire uniquement si** :

- Modification `.env.api` ou `.env`
- Ajout dependances (`pyproject.toml`, `package.json`)
- Modification `docker-compose.yml` ou `Dockerfile`

## Commandes principales

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

## Validation

**En fin de traitement, toujours verifier les logs Docker pour valider que tout est OK :**

```bash
make backend-logs     # Verifier pas d'erreurs backend
make logs             # Ou tous les logs
```

## Documentation

**En cas de changement de fonctionnement, mettre a jour la documentation dans `docs/` :**

- `docs/features-spec/` : Specifications fonctionnelles
- `docs/pages/` : Documentation des pages frontend
- `docs/setup/` : Installation et configuration
- `docs/architecture/` : Architecture systeme
- `docs/enedis-api/` : API Enedis
- `docs/troubleshooting/` : Resolution de problemes

## Acces

| Service     | URL                          |
| ----------- | ---------------------------- |
| Frontend    | <http://localhost:8000>      |
| Backend API | <http://localhost:8081>      |
| API Docs    | <http://localhost:8081/docs> |
| pgAdmin     | <http://localhost:5050>      |
