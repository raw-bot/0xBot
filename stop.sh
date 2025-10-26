#!/bin/bash
# Script d'arrêt propre du NOF1 Trading Bot

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🛑 Arrêt du NOF1 Trading Bot..."
echo ""

# 1. Arrêter le backend (si en cours)
echo "1️⃣  Arrêt du backend..."
BACKEND_PID=$(lsof -ti:8020 2>/dev/null || echo "")
if [ -n "$BACKEND_PID" ]; then
    echo -e "   ${YELLOW}⚠${NC} Arrêt du processus backend (PID: $BACKEND_PID)"
    kill $BACKEND_PID 2>/dev/null || true
    sleep 2
    echo -e "   ${GREEN}✓${NC} Backend arrêté"
else
    echo -e "   ${GREEN}✓${NC} Backend n'était pas en cours"
fi
echo ""

# 2. Arrêter les conteneurs Docker
echo "2️⃣  Arrêt des conteneurs Docker..."
cd "$(dirname "$0")"

if docker ps --filter "name=trading_agent" --format "{{.Names}}" | grep -q trading_agent; then
    # Trouver où est docker-compose.yml
    if [ -f "docker-compose.yml" ]; then
        docker-compose down
    elif [ -f "docker/docker-compose.yml" ]; then
        cd docker && docker-compose down && cd ..
    else
        warn "docker-compose.yml introuvable, arrêt manuel des conteneurs"
        docker stop trading_agent_postgres trading_agent_redis 2>/dev/null || true
    fi
    echo -e "   ${GREEN}✓${NC} Conteneurs arrêtés"
else
    echo -e "   ${GREEN}✓${NC} Conteneurs n'étaient pas en cours"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Arrêt complet terminé${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Pour redémarrer :"
echo "  ./start.sh"
echo ""
echo "Pour arrêter ET supprimer les données :"
echo "  docker-compose down -v"
