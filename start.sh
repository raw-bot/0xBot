#!/bin/bash
# Script de démarrage intelligent pour 0xBot Trading Bot
# Attend que PostgreSQL soit prêt avant de lancer le backend

set -e  # Arrêter si erreur (désactivé pour auto-start)

echo "🚀 Démarrage du 0xBot Trading Bot..."
echo ""

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
info() {
    echo -e "${GREEN}✓${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

# Aller à la racine du projet
cd "$(dirname "$0")"

# 1. Vérifier que Docker Desktop tourne
echo "1️⃣  Vérification de Docker Desktop..."
if ! docker ps &> /dev/null; then
    error "Docker Desktop n'est pas démarré !"
    echo "   👉 Ouvre Docker Desktop et attends qu'il soit prêt"
    exit 1
fi
info "Docker Desktop est actif"
echo ""

# 2. Vérifier que les conteneurs sont lancés
echo "2️⃣  Vérification des conteneurs..."

POSTGRES_RUNNING=$(docker ps --filter "name=trading_agent_postgres" --format "{{.Names}}" 2>/dev/null)
REDIS_RUNNING=$(docker ps --filter "name=trading_agent_redis" --format "{{.Names}}" 2>/dev/null)

if [ -z "$POSTGRES_RUNNING" ] || [ -z "$REDIS_RUNNING" ]; then
    warn "Les conteneurs ne sont pas tous lancés"
    echo "   Lancement via docker-compose..."
    
    # Trouver où est docker-compose.yml
    if [ -f "docker-compose.yml" ]; then
        docker-compose up -d
    elif [ -f "docker/docker-compose.yml" ]; then
        cd docker && docker-compose up -d && cd ..
    else
        error "Fichier docker-compose.yml introuvable"
        exit 1
    fi
    
    echo ""
fi

# 3. Attendre que PostgreSQL soit VRAIMENT prêt
echo "3️⃣  Attente de PostgreSQL (healthcheck)..."
MAX_RETRIES=30
RETRY=0

while [ $RETRY -lt $MAX_RETRIES ]; do
    # Vérifier le healthcheck
    HEALTH=$(docker inspect --format='{{.State.Health.Status}}' trading_agent_postgres 2>/dev/null || echo "none")
    
    if [ "$HEALTH" = "healthy" ]; then
        info "PostgreSQL est prêt !"
        break
    fi
    
    # Afficher un point pour montrer la progression
    echo -n "."
    sleep 1
    RETRY=$((RETRY + 1))
done

echo ""

if [ $RETRY -eq $MAX_RETRIES ]; then
    error "PostgreSQL n'est pas devenu healthy après ${MAX_RETRIES}s"
    echo "   Vérifiez les logs : docker logs trading_agent_postgres"
    exit 1
fi

# 4. Vérifier Redis
echo "4️⃣  Vérification de Redis..."
if docker exec trading_agent_redis redis-cli ping &> /dev/null; then
    info "Redis répond (PONG)"
else
    warn "Redis ne répond pas encore, on continue quand même..."
fi
echo ""

# 5. Activer le virtualenv et lancer le backend
echo "5️⃣  Démarrage du backend Python..."
cd backend

if [ ! -d "venv" ]; then
    error "Le virtualenv n'existe pas !"
    echo "   Exécute d'abord : ./setup.sh"
    exit 1
fi

source venv/bin/activate

info "Backend prêt à démarrer"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 Services opérationnels :"
echo "   • PostgreSQL : localhost:5432"
echo "   • Redis      : localhost:6379"
echo "   • Backend    : http://localhost:8020"
echo "   • Docs API   : http://localhost:8020/docs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 Lancement du serveur FastAPI..."
echo ""

# Désactiver set -e AVANT les commandes qui peuvent échouer
set +e

# Vérifier si le port 8020 est déjà utilisé
PORT_IN_USE=$(lsof -ti:8020 2>/dev/null)
if [ ! -z "$PORT_IN_USE" ]; then
    warn "Le port 8020 est déjà utilisé par le processus $PORT_IN_USE"
    echo "   Arrêt du processus existant..."
    kill -9 $PORT_IN_USE 2>/dev/null || true
    sleep 1
    info "Processus arrêté"
fi

# Lancer le serveur en arrière-plan si auto-start est configuré
if [ -f "../.env.dev" ]; then
    info "Configuration auto-start détectée"
    echo ""
    
    # Démarrer le serveur en arrière-plan (conserver les logs)
    ./venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8020 --reload > ../backend.log 2>&1 &
    SERVER_PID=$!
    echo "   Serveur lancé (PID: $SERVER_PID)"
    
    # Attendre que le serveur soit vraiment prêt (max 30 secondes)
    echo -n "   Attente du serveur"
    MAX_WAIT=30
    WAIT_COUNT=0
    while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
        if curl -s http://localhost:8020/docs > /dev/null 2>&1; then
            echo ""
            info "Serveur prêt !"
            break
        fi
        echo -n "."
        sleep 1
        WAIT_COUNT=$((WAIT_COUNT + 1))
    done
    echo ""
    
    if [ $WAIT_COUNT -eq $MAX_WAIT ]; then
        error "Le serveur n'a pas démarré dans les ${MAX_WAIT}s"
        kill $SERVER_PID 2>/dev/null || true
        exit 1
    fi
    
    # Lancer l'auto-start du bot depuis la racine
    cd ..
    echo ""
    echo "6️⃣  Auto-démarrage du bot..."
    python3 auto_start_bot.py
    AUTO_START_EXIT=$?
    
    if [ $AUTO_START_EXIT -ne 0 ]; then
        warn "L'auto-start a échoué (code: $AUTO_START_EXIT), mais le serveur reste actif"
    fi
    
    echo ""
    info "Serveur actif sur http://localhost:8020"
    info "Docs API: http://localhost:8020/docs"
    info "Appuyez sur Ctrl+C pour arrêter"
    echo ""
    
    # Attendre le serveur (foreground)
    wait $SERVER_PID
else
    # Pas de config auto-start, juste lancer le serveur normalement
    ./venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8020 --reload
fi
