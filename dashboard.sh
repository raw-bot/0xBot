#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🚀 0xBot - Script de lancement unifié (Bot + Dashboard)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Ce script:
# - Kill automatiquement les ports utilisés
# - Lance le backend API (port 8020)
# - Lance le frontend dashboard (port 5173)
# - Sauvegarde la config et les PIDs pour arrêt propre
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration des ports (mémorisés)
BACKEND_PORT=8020
FRONTEND_PORT=3030

# Aller à la racine du projet
cd "$(dirname "$0")"
PROJECT_ROOT=$(pwd)

# Fichier de configuration persistant
CONFIG_FILE="$PROJECT_ROOT/.dashboard_config"
PID_FILE="$PROJECT_ROOT/.dashboard_pids"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Fonctions utilitaires
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

info() { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; }
header() { echo -e "${CYAN}$1${NC}"; }

# Fonction pour tuer un port
kill_port() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        warn "Port $port occupé - arrêt des processus: $pids"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 1
        info "Port $port libéré"
    fi
}

# Fonction de nettoyage (appelée sur Ctrl+C ou sortie)
cleanup() {
    echo ""
    header "🛑 Arrêt du dashboard..."

    if [ -f "$PID_FILE" ]; then
        while read -r pid; do
            if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null || true
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi

    # Force kill des ports pour s'assurer qu'ils sont libres
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT

    # Double vérification avec pkill
    pkill -9 -f "serve -l $FRONTEND_PORT" 2>/dev/null || true
    pkill -9 -f "uvicorn.*$BACKEND_PORT" 2>/dev/null || true

    info "Dashboard arrêté - ports $BACKEND_PORT et $FRONTEND_PORT libérés"
    exit 0
}

# Intercepter les signaux d'arrêt
trap cleanup INT TERM

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Affichage du header
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

clear
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}       🤖 0xBot Dashboard Launcher     ${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Sauvegarder la config
echo "BACKEND_PORT=$BACKEND_PORT" > "$CONFIG_FILE"
echo "FRONTEND_PORT=$FRONTEND_PORT" >> "$CONFIG_FILE"
echo "LAST_START=$(date +%Y-%m-%d_%H:%M:%S)" >> "$CONFIG_FILE"
info "Configuration sauvegardée dans $CONFIG_FILE"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. NETTOYAGE DES PORTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo ""
header "1️⃣  Nettoyage des ports..."
kill_port $BACKEND_PORT
kill_port $FRONTEND_PORT
info "Ports libérés"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. VÉRIFICATION DOCKER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo ""
header "2️⃣  Vérification de Docker..."
if ! docker ps &> /dev/null; then
    error "Docker Desktop n'est pas démarré !"
    echo "   👉 Ouvre Docker Desktop et relance ce script"
    exit 1
fi
info "Docker Desktop actif"

# Vérifier les conteneurs
POSTGRES_RUNNING=$(docker ps --filter "name=trading_agent_postgres" --format "{{.Names}}" 2>/dev/null)
REDIS_RUNNING=$(docker ps --filter "name=trading_agent_redis" --format "{{.Names}}" 2>/dev/null)

if [ -z "$POSTGRES_RUNNING" ] || [ -z "$REDIS_RUNNING" ]; then
    warn "Conteneurs non démarrés - lancement..."
    if [ -f "docker/docker-compose.yml" ]; then
        cd docker && docker-compose up -d && cd ..
    elif [ -f "docker-compose.yml" ]; then
        docker-compose up -d
    fi

    # Attendre que PostgreSQL soit prêt
    echo -n "   Attente de PostgreSQL"
    for i in {1..30}; do
        HEALTH=$(docker inspect --format='{{.State.Health.Status}}' trading_agent_postgres 2>/dev/null || echo "none")
        if [ "$HEALTH" = "healthy" ]; then
            echo ""
            info "PostgreSQL prêt"
            break
        fi
        echo -n "."
        sleep 1
    done
else
    info "PostgreSQL et Redis déjà actifs"
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. DÉMARRAGE DU BACKEND
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo ""
header "3️⃣  Démarrage du Backend API..."

cd "$PROJECT_ROOT/backend"

if [ ! -d "venv" ]; then
    error "Le virtualenv n'existe pas ! Exécute d'abord: ./setup.sh"
    exit 1
fi

source venv/bin/activate

# Lancer le backend en arrière-plan
./venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload > "$PROJECT_ROOT/backend.log" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$PID_FILE"

# Attendre que le backend soit prêt
echo -n "   Attente du serveur API"
for i in {1..30}; do
    if curl -s "http://localhost:$BACKEND_PORT/docs" > /dev/null 2>&1; then
        echo ""
        info "Backend API prêt (PID: $BACKEND_PID)"
        break
    fi
    echo -n "."
    sleep 1
done

cd "$PROJECT_ROOT"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. DÉMARRAGE DU FRONTEND (React/Vite Application)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo ""
header "4️⃣  Démarrage du Dashboard Frontend (React)..."

cd "$PROJECT_ROOT/frontend"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    warn "Installation des dépendances npm..."
    npm install > /dev/null 2>&1
fi

# Start Vite dev server on port 3030 (with API proxy configured in vite.config.ts)
npm run dev -- --port $FRONTEND_PORT > "$PROJECT_ROOT/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "$FRONTEND_PID" >> "$PID_FILE"

# Wait for frontend to be ready
echo -n "   Attente du dashboard React"
for i in {1..30}; do
    if curl -s "http://localhost:$FRONTEND_PORT" > /dev/null 2>&1; then
        echo ""
        info "Dashboard React prêt sur port $FRONTEND_PORT (PID: $FRONTEND_PID)"
        break
    fi
    echo -n "."
    sleep 1
done

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. AUTO-START DU BOT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo ""
header "5️⃣  Auto-démarrage du bot..."

if [ -f "$PROJECT_ROOT/auto_start_bot.py" ] && [ -f "$PROJECT_ROOT/.env.dev" ]; then
    cd "$PROJECT_ROOT"
    backend/venv/bin/python3 auto_start_bot.py
    if [ $? -eq 0 ]; then
        info "Bot démarré avec succès"
    else
        warn "Échec du démarrage du bot (le dashboard reste actif)"
    fi
else
    warn "Auto-start non configuré (.env.dev ou auto_start_bot.py manquant)"
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RÉSUMÉ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅ 0xBot Dashboard OPÉRATIONNEL     ${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${CYAN}📊 Dashboard:${NC}  http://localhost:$FRONTEND_PORT/dashboard.html"
echo -e "  ${CYAN}🔧 API Docs:${NC}   http://localhost:$BACKEND_PORT/docs"
echo -e "  ${CYAN}💾 Config:${NC}     $CONFIG_FILE"
echo ""
echo -e "  ${YELLOW}📝 Logs:${NC}"
echo -e "     • Backend:  tail -f backend.log"
echo -e "     • Frontend: tail -f frontend.log"
echo ""
echo -e "  ${RED}🛑 Pour arrêter: Ctrl+C${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Attendre en affichant les logs combinés
tail -f "$PROJECT_ROOT/backend.log"
