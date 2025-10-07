#!/bin/bash

# Script pour démarrer le mode développement avec hot-reload

echo "🔧 Démarrage du mode développement..."
echo "📝 Les changements dans apps/web/src seront automatiquement rechargés"
echo ""

# Arrêter le frontend de production s'il tourne
echo "Arrêt du frontend de production..."
docker compose stop frontend 2>/dev/null || true

# Démarrer tous les services nécessaires (backend, redis, postgres, etc.)
echo "Démarrage des services (backend, redis, postgres)..."
docker compose up -d backend redis postgres pgadmin

# Attendre que le backend soit prêt
echo "Attente du backend..."
sleep 3

# Démarrer le frontend en mode dev
echo "Démarrage du frontend en mode développement..."
docker compose -f docker-compose.dev.yml up -d frontend-dev

echo ""
echo "✅ Mode développement actif !"
echo "🌐 Frontend dev: http://localhost:5173"
echo "🔌 Backend API: http://localhost:8000"
echo "🗄️  PgAdmin: http://localhost:5050"
echo "🔄 Hot-reload activé - vos changements seront automatiquement appliqués"
echo ""
echo "📋 Logs frontend: docker compose -f docker-compose.dev.yml logs -f frontend-dev"
echo "📋 Logs backend: docker compose logs -f backend"
echo "🛑 Pour arrêter: docker compose -f docker-compose.dev.yml stop && docker compose stop"
