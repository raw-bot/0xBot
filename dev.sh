#!/bin/bash
# Script de développement : Lance le serveur ET démarre automatiquement un bot
# Usage: ./dev.sh [bot_id]

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🚀 Mode Développement - Auto-Start Bot${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Vérifier que les fichiers nécessaires existent
if [ ! -f "auto_start_bot.py" ]; then
    echo -e "${RED}❌ Fichier auto_start_bot.py introuvable${NC}"
    echo -e "${YELLOW}Téléchargez-le et placez-le à la racine du projet${NC}"
    exit 1
fi

if [ ! -f ".env.dev" ]; then
    echo -e "${RED}❌ Fichier .env.dev introuvable${NC}"
    echo -e "${YELLOW}Créez-le avec vos credentials:${NC}"
    echo "  cp .env.dev.example .env.dev"
    echo "  nano .env.dev"
    exit 1
fi

# Récupérer le bot_id (argument ou .env.dev)
BOT_ID="$1"

if [ -n "$BOT_ID" ]; then
    echo -e "${GREEN}📌 Bot ID spécifié: $BOT_ID${NC}"
else
    # Essayer de lire depuis .env.dev
    if grep -q "AUTO_START_BOT_ID" .env.dev; then
        BOT_ID=$(grep "AUTO_START_BOT_ID" .env.dev | cut -d'=' -f2 | tr -d ' ')
        if [ -n "$BOT_ID" ]; then
            echo -e "${GREEN}📌 Bot ID depuis .env.dev: $BOT_ID${NC}"
        fi
    fi
fi

if [ -z "$BOT_ID" ]; then
    echo -e "${YELLOW}⚠️  Aucun bot_id spécifié${NC}"
    echo -e "${BLUE}Le dernier bot créé sera démarré automatiquement${NC}"
fi

echo ""
echo -e "${BLUE}1️⃣  Démarrage du serveur en arrière-plan...${NC}"

# Démarrer le serveur en arrière-plan
./start.sh > /tmp/nof1_server.log 2>&1 &
SERVER_PID=$!

echo -e "${GREEN}✓${NC} Serveur lancé (PID: $SERVER_PID)"
echo -e "${BLUE}   Logs: backend.log${NC}"
echo ""

# Attendre un peu pour que le serveur démarre
sleep 3

# Fonction de nettoyage
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Arrêt du serveur...${NC}"
    kill $SERVER_PID 2>/dev/null || true
    exit
}

# Intercepter Ctrl+C
trap cleanup INT TERM

echo -e "${BLUE}2️⃣  Auto-démarrage du bot...${NC}"
echo ""

# Démarrer le bot avec Python (depuis le venv backend)
if [ -n "$BOT_ID" ]; then
    backend/venv/bin/python3 auto_start_bot.py "$BOT_ID"
else
    backend/venv/bin/python3 auto_start_bot.py
fi

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ Serveur ET bot démarrés avec succès !${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}📊 Services:${NC}"
    echo -e "   • API:     http://localhost:8020/docs"
    echo -e "   • Health:  http://localhost:8020/health"
    echo ""
    echo -e "${BLUE}🛑 Pour arrêter: ${YELLOW}Ctrl+C${NC}"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}📊 Logs en temps réel:${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # Afficher les logs en temps réel dans le terminal
    tail -f backend.log
else
    echo ""
    echo -e "${RED}❌ Échec du démarrage du bot${NC}"
    echo -e "${YELLOW}Le serveur continue de tourner (PID: $SERVER_PID)${NC}"
    echo -e "${YELLOW}Pour l'arrêter: kill $SERVER_PID${NC}"
    exit 1
fi
