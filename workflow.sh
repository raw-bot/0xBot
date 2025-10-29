#!/bin/bash
# Script de workflow amélioré pour NOF1 Trading Bot
# Utilisation: ./workflow.sh [command]
# Commands disponibles: dev, test, debug, lint, clean, setup, status, logs

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
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

header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}🚀 $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Aller à la racine du projet
cd "$(dirname "$0")"

# Fonction pour vérifier les prérequis
check_prerequisites() {
    header "Vérification des prérequis"

    # Vérifier Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        info "Python $PYTHON_VERSION installé"
    else
        error "Python 3 n'est pas installé"
        exit 1
    fi

    # Vérifier Node.js
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        info "Node.js $NODE_VERSION installé"
    else
        warn "Node.js n'est pas installé (pour le frontend)"
    fi

    # Vérifier Docker
    if command -v docker &> /dev/null; then
        info "Docker installé"
    else
        error "Docker n'est pas installé"
        exit 1
    fi

    # Vérifier Git
    if command -v git &> /dev/null; then
        info "Git installé"
    else
        warn "Git n'est pas installé"
    fi
}

# Fonction setup
setup_environment() {
    header "Configuration de l'environnement"

    # Lancer le setup principal
    if [ -f "setup.sh" ]; then
        ./setup.sh
        info "Setup principal terminé"
    else
        warn "setup.sh introuvable"
    fi

    # Installer les dépendances frontend
    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
        echo "📦 Installation des dépendances frontend..."
        cd frontend
        npm install
        cd ..
        info "Dépendances frontend installées"
    fi

    # Configurer VS Code
    if [ -d ".vscode" ]; then
        info "Configuration VS Code disponible"
        echo "   Extensions recommandées: $(find .vscode -name 'extensions.json' | wc -l)"
    fi
}

# Fonction pour lancer en mode développement
dev_mode() {
    header "Mode Développement"

    # Vérifier si Docker tourne
    if ! docker ps &> /dev/null; then
        error "Docker Desktop n'est pas démarré"
        exit 1
    fi

    # Démarrer les services
    if [ -f "dev.sh" ]; then
        ./dev.sh
    else
        warn "dev.sh introuvable, utilisation de start.sh"
        ./start.sh
    fi
}

# Fonction pour les tests
run_tests() {
    header "Exécution des tests"

    # Tests backend
    if [ -d "backend" ] && [ -d "backend/tests" ]; then
        echo "🧪 Tests backend..."
        cd backend
        if [ -d "venv" ]; then
            source venv/bin/activate
            python -m pytest tests/ -v --tb=short
            info "Tests backend terminés"
        else
            warn "Virtualenv backend introuvable"
        fi
        cd ..
    fi

    # Tests audit
    if [ -d "backend/scripts/tests" ]; then
        echo "🔍 Tests d'audit..."
        cd backend/scripts/tests
        if [ -d "../../venv" ]; then
            source ../../venv/bin/activate
            python audit_critical_paths.py
            info "Tests d'audit terminés"
        fi
        cd ../..
    fi
}

# Fonction pour le linting et formatage
lint_and_format() {
    header "Formatage et vérification du code"

    # Backend formatting
    if [ -d "backend" ]; then
        echo "🎨 Formatage backend..."
        cd backend
        if [ -d "venv" ]; then
            source venv/bin/activate

            # Black formatting
            echo "   Black formatting..."
            ./venv/bin/black . --line-length 100

            # Import sorting
            echo "   Import sorting..."
            ./venv/bin/isort . --profile black

            # Type checking
            echo "   Type checking..."
            ./venv/bin/mypy src --config-file=pyproject.toml

            info "Backend formaté"
        fi
        cd ..
    fi

    # Frontend linting
    if [ -d "frontend" ]; then
        echo "🎨 Linting frontend..."
        cd frontend
        if [ -f "package.json" ]; then
            npm run lint --if-present || warn "Lint frontend échoué"
            npm run build --if-present || warn "Build frontend échoué"
        fi
        cd ..
    fi
}

# Fonction pour le debug
debug_mode() {
    header "Mode Debug"

    echo "🔧 Options de debug disponibles:"
    echo "   • Backend: FastAPI avec hot reload"
    echo "   • Frontend: Vite avec hot reload"
    echo "   • Database: PostgreSQL avec health checks"
    echo ""

    # Lancer avec debug
    docker-compose up -d 2>/dev/null || (cd docker && docker-compose up -d && cd ..)

    sleep 3

    if [ -d "backend" ]; then
        cd backend
        if [ -d "venv" ]; then
            source venv/bin/activate
            echo "🐍 Lancement backend en mode debug..."
            ./venv/bin/python -m uvicorn src.main:app --reload --log-level debug
        fi
        cd ..
    fi
}

# Fonction pour nettoyer
clean_environment() {
    header "Nettoyage de l'environnement"

    echo "🧹 Nettoyage en cours..."

    # Nettoyer les logs
    if [ -f "backend.log" ]; then
        rm -f backend.log
        info "Logs backend supprimés"
    fi

    # Nettoyer les caches Python
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name ".mypy_cache" -type d -exec rm -rf {} + 2>/dev/null || true
    info "Caches Python nettoyés"

    # Nettoyer node_modules
    if [ -d "frontend/node_modules" ]; then
        rm -rf frontend/node_modules
        info "node_modules nettoyé"
    fi

    # Nettoyer les builds
    if [ -d "frontend/dist" ]; then
        rm -rf frontend/dist
        info "Build frontend nettoyé"
    fi
}

# Fonction pour afficher le statut
show_status() {
    header "Statut du projet"

    echo "📊 Services Docker:"
    docker ps --filter "name=trading_agent" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || warn "Docker non disponible"

    echo ""
    echo "🔧 Statut des services:"

    # API
    if curl -s http://localhost:8020/health > /dev/null 2>&1; then
        info "API Backend: ✅ Fonctionnel"
    else
        warn "API Backend: ❌ Non accessible"
    fi

    # Frontend
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        info "Frontend: ✅ Fonctionnel"
    else
        warn "Frontend: ❌ Non accessible"
    fi

    # Database
    if docker exec trading_agent_postgres pg_isready -U postgres > /dev/null 2>&1; then
        info "PostgreSQL: ✅ Fonctionnel"
    else
        warn "PostgreSQL: ❌ Non accessible"
    fi

    # Redis
    if docker exec trading_agent_redis redis-cli ping > /dev/null 2>&1; then
        info "Redis: ✅ Fonctionnel"
    else
        warn "Redis: ❌ Non accessible"
    fi

    echo ""
    echo "📈 URLs disponibles:"
    echo "   • API Docs:    http://localhost:8020/docs"
    echo "   • Frontend:    http://localhost:5173"
    echo "   • Health:      http://localhost:8020/health"
}

# Fonction pour afficher les logs
show_logs() {
    header "Logs en temps réel"

    echo "📋 Options de logs:"
    echo "   1. Logs backend (tail -f backend.log)"
    echo "   2. Logs Docker (docker logs -f <container>)"
    echo "   3. Tous les logs backend"
    echo ""

    if [ -f "backend.log" ]; then
        echo "📄 Affichage des derniers logs backend:"
        tail -n 50 backend.log
    else
        warn "Fichier backend.log introuvable"
    fi
}

# Fonction d'aide
show_help() {
    header "Commandes disponibles"

    echo "Usage: ./workflow.sh <command>"
    echo ""
    echo "Commands:"
    echo "  setup          Configuration complète de l'environnement"
    echo "  dev            Lance le serveur en mode développement"
    echo "  test           Exécute les tests backend et audit"
    echo "  lint           Formatage et vérification du code"
    echo "  debug          Lance avec logs détaillés"
    echo "  clean          Nettoie les caches et logs"
    echo "  status         Affiche le statut des services"
    echo "  logs           Affiche les logs"
    echo "  help           Affiche cette aide"
    echo ""
    echo "Examples:"
    echo "  ./workflow.sh setup    # Premier setup"
    echo "  ./workflow.sh dev      # Développement"
    echo "  ./workflow.sh test     # Tests"
}

# Main
case "${1:-help}" in
    "setup")
        check_prerequisites
        setup_environment
        ;;
    "dev")
        dev_mode
        ;;
    "test")
        run_tests
        ;;
    "lint")
        lint_and_format
        ;;
    "debug")
        debug_mode
        ;;
    "clean")
        clean_environment
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs
        ;;
    "help"|*)
        show_help
        ;;
esac
