# Installation Mode Client

## Prérequis

### Matériel

- **RAM** : 512 Mo minimum (1 Go recommandé)
- **Disque** : 500 Mo pour l'application + espace pour les données
- **CPU** : 1 core minimum

### Logiciels

- Docker 24+ et Docker Compose v2
- Accès réseau vers `www.v2.myelectricaldata.fr`

### Compte MyElectricalData

1. Créer un compte sur [www.v2.myelectricaldata.fr](https://www.v2.myelectricaldata.fr)
2. Autoriser vos PDL (Points de Livraison) via le consentement Enedis
3. Récupérer vos **Client ID** et **Client Secret** dans les paramètres

---

## Installation Docker

### Étape 1 : Cloner le dépôt

```bash
git clone https://github.com/MyElectricalData/myelectricaldata.git
cd myelectricaldata
```

### Étape 2 : Créer le fichier de configuration

```bash
# Copier le template
cp .env.client.example .env.client

# Éditer avec vos credentials
nano .env.client
```

**Contenu minimum de `.env.client`** :

```bash
# === OBLIGATOIRE ===
# Credentials API MyElectricalData (depuis votre compte)
MED_CLIENT_ID=cli_xxxxxxxxxxxxxxxxxxxxxxxxx
MED_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# === OPTIONNEL ===
# Timezone (défaut: Europe/Paris)
TZ=Europe/Paris

# Port frontend (défaut: 8100)
CLIENT_FRONTEND_PORT=8100

# Port backend (défaut: 8181)
CLIENT_BACKEND_PORT=8181
```

### Étape 3 : Démarrer les services

```bash
# Démarrer le mode client
docker compose -f docker-compose.client.yml up -d

# Vérifier les logs
docker compose -f docker-compose.client.yml logs -f
```

### Étape 4 : Accéder à l'interface

Ouvrir http://localhost:8100 dans un navigateur.

---

## Première synchronisation

Au premier démarrage, les données ne sont pas encore synchronisées. Deux options :

### Option A : Synchronisation automatique

Le scheduler lance une synchronisation automatique à 6h00 chaque jour. Attendez la prochaine exécution.

### Option B : Synchronisation manuelle

1. Accéder à l'interface : http://localhost:8100
2. Aller dans **Dashboard**
3. Cliquer sur le bouton **Synchroniser**

Ou via API :

```bash
curl -X POST http://localhost:8181/api/sync
```

---

## Coexistence avec le mode serveur

Les deux modes utilisent des ports et volumes différents :

### Ports par défaut

| Service | Mode Serveur | Mode Client |
|---------|--------------|-------------|
| Frontend | 8000 | 8100 |
| Backend | 8081 | 8181 |
| PostgreSQL | 5432 (interne) | 5433 (interne) |

### Démarrer les deux modes

```bash
# Terminal 1 : Mode serveur
docker compose -f docker-compose.yml up -d

# Terminal 2 : Mode client
docker compose -f docker-compose.client.yml up -d
```

### Vérifier les conteneurs

```bash
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"
```

Résultat attendu :

```
NAMES                          PORTS                     STATUS
myelectricaldata-frontend-1    0.0.0.0:8000->5173/tcp   Up
myelectricaldata-backend-1     0.0.0.0:8081->8000/tcp   Up
myelectricaldata-client-1      0.0.0.0:8100->5173/tcp   Up
myelectricaldata-client-api-1  0.0.0.0:8181->8000/tcp   Up
```

---

## Installation sur Raspberry Pi

Le mode client est optimisé pour fonctionner sur Raspberry Pi 3B+ ou supérieur.

### Configuration spécifique

Ajouter dans `.env.client` :

```bash
# Réduire l'utilisation mémoire
POSTGRES_SHARED_BUFFERS=64MB
POSTGRES_WORK_MEM=4MB

# Désactiver le hot-reload (économie CPU)
DISABLE_HOT_RELOAD=true
```

### Image Docker ARM

Les images Docker supportent automatiquement ARM64 (Pi 4) et ARMv7 (Pi 3).

```bash
# Vérifier l'architecture
uname -m
# aarch64 (Pi 4) ou armv7l (Pi 3)

# Pull des images optimisées
docker compose -f docker-compose.client.yml pull
```

---

## Mise à jour

### Mise à jour des images

```bash
cd myelectricaldata

# Arrêter les services
docker compose -f docker-compose.client.yml down

# Mettre à jour le code
git pull

# Reconstruire et redémarrer
docker compose -f docker-compose.client.yml up -d --build
```

### Migration de base de données

Les migrations Alembic s'appliquent automatiquement au démarrage. Pour une migration manuelle :

```bash
docker compose -f docker-compose.client.yml exec backend-client \
  alembic upgrade head
```

---

## Sauvegarde et restauration

### Sauvegarde PostgreSQL

```bash
# Créer une sauvegarde
docker compose -f docker-compose.client.yml exec postgres-client \
  pg_dump -U client client > backup_$(date +%Y%m%d).sql
```

### Restauration

```bash
# Restaurer depuis une sauvegarde
docker compose -f docker-compose.client.yml exec -T postgres-client \
  psql -U client client < backup_20240115.sql
```

### Sauvegarde complète (volumes Docker)

```bash
# Arrêter les services
docker compose -f docker-compose.client.yml down

# Sauvegarder les volumes
docker run --rm \
  -v myelectricaldata_client_postgres_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/postgres_data.tar.gz -C /data .

# Redémarrer
docker compose -f docker-compose.client.yml up -d
```

---

## Dépannage

### Le frontend ne démarre pas

```bash
# Vérifier les logs
docker compose -f docker-compose.client.yml logs frontend-client

# Erreur courante : port déjà utilisé
# Solution : modifier CLIENT_FRONTEND_PORT dans .env.client
```

### Erreur de connexion à l'API MyElectricalData

```bash
# Vérifier les credentials
docker compose -f docker-compose.client.yml exec backend-client \
  curl -X POST https://www.v2.myelectricaldata.fr/api/accounts/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=${MED_CLIENT_ID}&client_secret=${MED_CLIENT_SECRET}"
```

### Base de données corrompue

```bash
# Réinitialiser la base (ATTENTION : perte de données)
docker compose -f docker-compose.client.yml down -v
docker compose -f docker-compose.client.yml up -d
```

### Voir les logs en temps réel

```bash
# Tous les services
docker compose -f docker-compose.client.yml logs -f

# Backend uniquement
docker compose -f docker-compose.client.yml logs -f backend-client

# Avec timestamps
docker compose -f docker-compose.client.yml logs -f -t
```

---

## Structure des fichiers

Après installation, la structure est :

```
myelectricaldata/
├── docker-compose.yml           # Mode serveur
├── docker-compose.client.yml    # Mode client
├── .env.api                     # Config mode serveur
├── .env.client                  # Config mode client
└── apps/
    ├── api/
    │   └── data/
    │       └── client/          # Données mode client
    └── web/
```

---

## Désinstallation

```bash
# Arrêter et supprimer les conteneurs
docker compose -f docker-compose.client.yml down

# Supprimer aussi les volumes (données)
docker compose -f docker-compose.client.yml down -v

# Supprimer les images
docker rmi $(docker images 'myelectricaldata-client*' -q)
```
