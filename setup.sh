#!/bin/bash
# Script d'installation complète du 0xBot Trading Bot
# À exécuter une seule fois lors du premier setup

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() {
    echo -e "${GREEN}✓${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Installation du 0xBot Trading Bot"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Aller à la racine du projet
cd "$(dirname "$0")"

# 1. Vérifier les prérequis
echo "1️⃣  Vérification des prérequis..."

# Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    info "Python $PYTHON_VERSION installé"
else
    error "Python 3 n'est pas installé"
    echo "   Installez Python 3.11+ depuis https://www.python.org"
    exit 1
fi

# Docker
if command -v docker &> /dev/null; then
    info "Docker installé"
else
    error "Docker n'est pas installé"
    echo "   Installez Docker Desktop depuis https://www.docker.com"
    exit 1
fi

# Docker Compose
if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    info "Docker Compose installé"
else
    error "Docker Compose n'est pas installé"
    exit 1
fi

echo ""

# 2. Créer le fichier .env
echo "2️⃣  Configuration de l'environnement..."

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        info "Fichier .env créé depuis .env.example"
        warn "N'oubliez pas de configurer vos clés API dans .env !"
    else
        warn ".env.example n'existe pas, création d'un .env minimal"
        cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/trading_agent

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET=change-this-in-production-$(openssl rand -hex 32)

# LLM API Keys (configurez AU MOINS UNE clé)
# QWEN_API_KEY=sk-...
# DEEPSEEK_API_KEY=sk-...
# CLAUDE_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...

# Exchange API (optionnel pour paper trading)
# OKX_API_KEY=
# OKX_SECRET_KEY=
# OKX_PASSPHRASE=
EOF
        info "Fichier .env créé avec configuration minimale"
        warn "IMPORTANT: Configurez vos clés API dans .env avant de continuer"
    fi
else
    info "Fichier .env existe déjà"
fi

echo ""

# 3. Démarrer Docker Compose
echo "3️⃣  Démarrage des services Docker..."

if ! docker ps &> /dev/null; then
    error "Docker Desktop n'est pas actif"
    echo "   Démarrez Docker Desktop et réessayez"
    exit 1
fi

# Trouver où est docker-compose.yml
if [ -f "docker-compose.yml" ]; then
    DOCKER_COMPOSE_DIR="."
    info "Fichier docker-compose.yml trouvé à la racine"
elif [ -f "docker/docker-compose.yml" ]; then
    DOCKER_COMPOSE_DIR="docker"
    info "Fichier docker-compose.yml trouvé dans docker/"
else
    error "Fichier docker-compose.yml introuvable"
    echo "   Vérifiez que le fichier existe dans le projet"
    exit 1
fi

# Démarrer les services
cd "$DOCKER_COMPOSE_DIR"
docker-compose up -d
cd - > /dev/null
info "PostgreSQL et Redis démarrés"

echo ""

# 4. Attendre que PostgreSQL soit prêt
echo "4️⃣  Attente de PostgreSQL..."
MAX_RETRIES=30
RETRY=0

while [ $RETRY -lt $MAX_RETRIES ]; do
    HEALTH=$(docker inspect --format='{{.State.Health.Status}}' trading_agent_postgres 2>/dev/null || echo "none")
    
    if [ "$HEALTH" = "healthy" ]; then
        info "PostgreSQL est prêt"
        break
    fi
    
    echo -n "."
    sleep 1
    RETRY=$((RETRY + 1))
done

echo ""

if [ $RETRY -eq $MAX_RETRIES ]; then
    error "PostgreSQL n'est pas devenu healthy après ${MAX_RETRIES}s"
    exit 1
fi

echo ""

# 5. Setup du backend Python
echo "5️⃣  Configuration du backend Python..."
cd backend

# Créer le virtualenv
if [ ! -d "venv" ]; then
    echo "   Création du virtualenv..."
    python3 -m venv venv
    info "Virtualenv créé"
else
    info "Virtualenv existe déjà"
fi

# Activer et installer les dépendances
source venv/bin/activate

echo "   Installation des dépendances..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
info "Dépendances installées"

echo ""

# 6. Migrations de base de données
echo "6️⃣  Création des tables de base de données..."

if command -v alembic &> /dev/null; then
    alembic upgrade head
    info "Tables créées avec succès"
else
    warn "Alembic n'est pas disponible, migrations ignorées"
fi

echo ""

# 7. Résumé
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Installation terminée avec succès !${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Prochaines étapes :"
echo ""
echo "1. Configurez vos clés API dans le fichier .env :"
echo "   ${BLUE}nano .env${NC}  # ou utilisez votre éditeur préféré"
echo ""
echo "2. Démarrez le serveur :"
echo "   ${BLUE}./start.sh${NC}"
echo ""
echo "3. Accédez à l'API :"
echo "   • API Docs    : http://localhost:8020/docs"
echo "   • Health Check: http://localhost:8020/health"
echo ""
echo "📚 Documentation disponible dans le dossier docs/"
echo ""

# Vérifier si les clés API sont configurées
if ! grep -q "^QWEN_API_KEY=sk-" .env && \
   ! grep -q "^DEEPSEEK_API_KEY=sk-" .env && \
   ! grep -q "^CLAUDE_API_KEY=sk-ant-" .env && \
   ! grep -q "^OPENAI_API_KEY=sk-" .env; then
    echo -e "${YELLOW}⚠️  ATTENTION: Aucune clé API LLM configurée !${NC}"
    echo "   Le bot ne pourra pas fonctionner sans clé API."
    echo "   Configurez AU MOINS UNE clé dans .env"
    echo ""
fi
