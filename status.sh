#!/bin/bash
# Script de vérification du statut des services NOF1

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 Statut du NOF1 Trading Bot"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. Docker Desktop
echo "1️⃣  Docker Desktop"
if docker ps &> /dev/null; then
    echo -e "   ${GREEN}✓${NC} Actif"
else
    echo -e "   ${RED}✗${NC} Non actif"
    exit 1
fi
echo ""

# 2. Conteneurs
echo "2️⃣  Conteneurs Docker"

# PostgreSQL
POSTGRES_STATUS=$(docker inspect --format='{{.State.Status}}' trading_agent_postgres 2>/dev/null || echo "stopped")
POSTGRES_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' trading_agent_postgres 2>/dev/null || echo "none")

if [ "$POSTGRES_STATUS" = "running" ]; then
    if [ "$POSTGRES_HEALTH" = "healthy" ]; then
        echo -e "   ${GREEN}✓${NC} PostgreSQL : running (healthy)"
    else
        echo -e "   ${YELLOW}⚠${NC} PostgreSQL : running ($POSTGRES_HEALTH)"
    fi
else
    echo -e "   ${RED}✗${NC} PostgreSQL : $POSTGRES_STATUS"
fi

# Redis
REDIS_STATUS=$(docker inspect --format='{{.State.Status}}' trading_agent_redis 2>/dev/null || echo "stopped")
REDIS_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' trading_agent_redis 2>/dev/null || echo "none")

if [ "$REDIS_STATUS" = "running" ]; then
    if [ "$REDIS_HEALTH" = "healthy" ]; then
        echo -e "   ${GREEN}✓${NC} Redis      : running (healthy)"
    else
        echo -e "   ${YELLOW}⚠${NC} Redis      : running ($REDIS_HEALTH)"
    fi
else
    echo -e "   ${RED}✗${NC} Redis      : $REDIS_STATUS"
fi
echo ""

# 3. Ports
echo "3️⃣  Ports"
if lsof -Pi :5432 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "   ${GREEN}✓${NC} Port 5432 (PostgreSQL) : Ouvert"
else
    echo -e "   ${RED}✗${NC} Port 5432 (PostgreSQL) : Fermé"
fi

if lsof -Pi :6379 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "   ${GREEN}✓${NC} Port 6379 (Redis)      : Ouvert"
else
    echo -e "   ${RED}✗${NC} Port 6379 (Redis)      : Fermé"
fi

if lsof -Pi :8020 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "   ${GREEN}✓${NC} Port 8020 (Backend)    : Ouvert"
else
    echo -e "   ${YELLOW}⚠${NC} Port 8020 (Backend)    : Fermé (pas démarré)"
fi
echo ""

# 4. Connectivité
echo "4️⃣  Connectivité"

# PostgreSQL
if docker exec trading_agent_postgres pg_isready -U postgres >/dev/null 2>&1; then
    echo -e "   ${GREEN}✓${NC} PostgreSQL accepte les connexions"
else
    echo -e "   ${RED}✗${NC} PostgreSQL ne répond pas"
fi

# Redis
if docker exec trading_agent_redis redis-cli ping >/dev/null 2>&1; then
    echo -e "   ${GREEN}✓${NC} Redis répond (PONG)"
else
    echo -e "   ${RED}✗${NC} Redis ne répond pas"
fi

# Backend API
if curl -s http://localhost:8020/health >/dev/null 2>&1; then
    echo -e "   ${GREEN}✓${NC} Backend API répond"
else
    echo -e "   ${YELLOW}⚠${NC} Backend API ne répond pas (normal si pas démarré)"
fi
echo ""

# 5. Base de données
echo "5️⃣  Base de données"
BOT_COUNT=$(docker exec trading_agent_postgres psql -U postgres -d trading_agent -t -c "SELECT COUNT(*) FROM bots;" 2>/dev/null | tr -d ' ')
if [ -n "$BOT_COUNT" ]; then
    echo -e "   ${GREEN}✓${NC} Nombre de bots : $BOT_COUNT"
else
    echo -e "   ${YELLOW}⚠${NC} Impossible de compter les bots"
fi
echo ""

# Résumé
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$POSTGRES_HEALTH" = "healthy" ] && [ "$REDIS_HEALTH" = "healthy" ]; then
    echo -e "${GREEN}✅ Tous les services sont opérationnels${NC}"
    echo ""
    echo "Pour démarrer le backend :"
    echo "  ./start.sh"
else
    echo -e "${YELLOW}⚠️  Certains services ont besoin d'attention${NC}"
    echo ""
    echo "Pour démarrer les services :"
    echo "  docker-compose up -d"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
