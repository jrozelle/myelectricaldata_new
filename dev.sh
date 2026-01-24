#!/bin/bash

# Script pour démarrer l'environnement de développement avec couleurs préservées

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Dossiers et fichiers
LOG_DIR="./tmp"
LOG_FILE="$LOG_DIR/watch-backend.log"
WATCH_PID_FILE="$LOG_DIR/watch-backend.pid"
WATCH_SCRIPT="./watch-backend.sh"

echo -e "${GREEN}🚀 Starting development environment...${NC}"

# Créer le dossier de logs
mkdir -p "$LOG_DIR"

# Arrêter un watcher existant
if [ -f "$WATCH_PID_FILE" ]; then
    echo -e "${YELLOW}⚠️  Stopping existing watcher...${NC}"
    kill $(cat "$WATCH_PID_FILE") 2>/dev/null || true
    rm -f "$WATCH_PID_FILE"
fi

# Démarrer le watcher si le script existe
if [ -f "$WATCH_SCRIPT" ]; then
    echo -e "${GREEN}🔄 Starting backend file watcher...${NC}"
    nohup "$WATCH_SCRIPT" > "$LOG_FILE" 2>&1 & echo $! > "$WATCH_PID_FILE"
    echo -e "${GREEN}✅ Watcher PID: $(cat $WATCH_PID_FILE)${NC}"
    echo -e "${GREEN}📝 Logs: $LOG_FILE${NC}"
else
    echo -e "${YELLOW}⚠️  Warning: $WATCH_SCRIPT not found, skipping hot reload${NC}"
fi

# Démarrer le serveur de documentation
DOCS_PID_FILE="$LOG_DIR/docs.pid"
DOCS_LOG_FILE="$LOG_DIR/docs.log"

if [ -f "$DOCS_PID_FILE" ]; then
    echo -e "${YELLOW}⚠️  Stopping existing docs server...${NC}"
    kill $(cat "$DOCS_PID_FILE") 2>/dev/null || true
    rm -f "$DOCS_PID_FILE"
fi

if [ -d "apps/docs" ] && [ -f "apps/docs/package.json" ]; then
    echo -e "${GREEN}📚 Starting documentation server...${NC}"
    cd apps/docs
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}📦 Installing docs dependencies...${NC}"
        npm install > /dev/null 2>&1
    fi
    nohup npm start -- --port 8002 --no-open > "../../$DOCS_LOG_FILE" 2>&1 & echo $! > "../../$DOCS_PID_FILE"
    cd ../..
    echo -e "${GREEN}✅ Docs server PID: $(cat $DOCS_PID_FILE)${NC}"
    echo -e "${GREEN}📖 Documentation: http://localhost:8002${NC}"
else
    echo -e "${YELLOW}⚠️  Warning: apps/docs not found, skipping documentation${NC}"
fi

echo -e "${GREEN}🐳 Starting Docker services with colors...${NC}"

# Forcer TTY et les couleurs
export COMPOSE_DOCKER_CLI_BUILD=1
export DOCKER_BUILDKIT=1
export FORCE_COLOR=1
export DOCKER_CLI_HINTS=false
export COMPOSE_ANSI=always

# Démarrer les services client si .env.local-client existe
if [ -f ".env.local-client" ]; then
    echo -e "${GREEN}🏠 Starting Client Mode services (background)...${NC}"
    docker compose -f docker-compose.client.yml up -d
    echo -e "${GREEN}✅ Client Mode started${NC}"
else
    echo -e "${YELLOW}⚠️  Client Mode not started (.env.local-client not found)${NC}"
fi

echo -e "${GREEN}🌐 Starting Server Mode services (foreground)...${NC}"
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                    📍 ACCESS POINTS                        ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Server Mode:${NC}"
echo -e "    Frontend:        http://localhost:8000"
echo -e "    Backend API:     http://localhost:8081"
echo -e "    API Docs:        http://localhost:8081/docs"
echo -e "    pgAdmin:         http://localhost:5050"
if [ -f ".env.local-client" ]; then
echo -e ""
echo -e "${GREEN}  Client Mode:${NC}"
echo -e "    Frontend:        http://localhost:8100"
echo -e "    Backend API:     http://localhost:8181"
echo -e "    API Docs:        http://localhost:8181/docs"
echo -e "    VictoriaMetrics: http://localhost:8428"
echo -e "    pgAdmin Client:  http://localhost:5051"
fi
if [ -d "apps/docs" ]; then
echo -e ""
echo -e "${GREEN}  Documentation:${NC}"
echo -e "    Docusaurus:      http://localhost:8002"
fi
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Lancer les deux modes avec logs combinés
if [ -f ".env.local-client" ]; then
    # Les deux modes sont actifs : combiner les logs
    # Utiliser docker compose logs -f pour les deux en parallèle
    docker compose up -d
    echo -e "${GREEN}🔄 Showing combined logs (Server + Client)...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop viewing logs (services will keep running)${NC}"
    echo ""

    # Trap pour cleanup propre
    trap 'echo -e "\n${YELLOW}Stopping all services...${NC}"; docker compose down; docker compose -f docker-compose.client.yml down; exit 0' INT

    # Afficher les logs des deux modes en parallèle
    docker compose logs -f --tail=100 &
    SERVER_LOGS_PID=$!
    docker compose -f docker-compose.client.yml logs -f --tail=100 &
    CLIENT_LOGS_PID=$!

    # Attendre les deux processus
    wait $SERVER_LOGS_PID $CLIENT_LOGS_PID
else
    # Mode serveur uniquement
    exec docker compose up
fi
