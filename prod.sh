#!/bin/bash

# Script pour revenir en mode production

echo "🔧 Passage en mode production..."
echo ""

# Arrêter le frontend de dev
echo "Arrêt du frontend de développement..."
docker compose -f docker-compose.dev.yml stop frontend-dev 2>/dev/null || true

# Rebuild et redémarrer le frontend de production
echo "Rebuild du frontend de production..."
docker compose build frontend --no-cache
docker compose up -d frontend

echo ""
echo "✅ Mode production actif !"
echo "🌐 Application: http://localhost"
echo ""
