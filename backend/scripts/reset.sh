#!/bin/bash
# Script de réinitialisation rapide d'un bot de trading
# Usage: ./reset.sh <bot_id> [capital]
# Exemple: ./reset.sh bot-abc123 10000

set -e

# Couleurs pour output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BOT_ID=$1
CAPITAL=${2:-10000}

# Validation des paramètres
if [ -z "$BOT_ID" ]; then
    echo -e "${RED}❌ Erreur: Bot ID requis${NC}"
    echo -e "Usage: ./reset.sh <bot_id> [capital]"
    echo -e "Exemple: ./reset.sh bot-abc123 10000"
    exit 1
fi

# Variables d'environnement PostgreSQL (avec valeurs par défaut)
DB_HOST=${POSTGRES_HOST:-localhost}
DB_PORT=${POSTGRES_PORT:-5432}
DB_NAME=${POSTGRES_DB:-trading_agent}
DB_USER=${POSTGRES_USER:-postgres}
DB_PASSWORD=${POSTGRES_PASSWORD:-postgres}

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🔄 RESET BOT DE TRADING${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "   Bot ID: ${BOT_ID}"
echo -e "   Capital: \$${CAPITAL}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Confirmation
read -p "Confirmer la réinitialisation? (o/N): " -r
echo
if [[ ! $REPLY =~ ^[Oo]$ ]]; then
    echo -e "${RED}❌ Opération annulée${NC}"
    exit 0
fi

# Export du mot de passe pour psql
export PGPASSWORD=$DB_PASSWORD

# Exécution des commandes SQL
echo -e "${YELLOW}🗑️  Suppression des positions...${NC}"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c \
    "DELETE FROM positions WHERE bot_id = '$BOT_ID';" > /dev/null

echo -e "${YELLOW}🗑️  Suppression des trades...${NC}"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c \
    "DELETE FROM trades WHERE bot_id = '$BOT_ID';" > /dev/null

echo -e "${YELLOW}💰 Réinitialisation du capital...${NC}"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c \
    "UPDATE bots
     SET capital = $CAPITAL,
         initial_capital = $CAPITAL,
         updated_at = NOW()
     WHERE id = '$BOT_ID';" > /dev/null

# Vérification
RESULT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c \
    "SELECT capital FROM bots WHERE id = '$BOT_ID';")

if [ -n "$RESULT" ]; then
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ Bot réinitialisé avec succès!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "   Capital: \$${CAPITAL}"
    echo -e "   Positions: 0"
    echo -e "   Trades: 0"
    echo -e "   PnL: \$0.00"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "🚀 Vous pouvez relancer le bot avec: ${GREEN}./start.sh${NC}"
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}⚠️  Bot non trouvé: ${BOT_ID}${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 1
fi

# Nettoyer la variable d'environnement
unset PGPASSWORD

