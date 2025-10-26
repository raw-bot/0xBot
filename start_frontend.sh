#!/bin/bash

echo "🚀 Démarrage du Frontend"
echo "========================"
echo ""

# Aller dans le bon répertoire
PROJECT_DIR="/Users/cube/Documents/00-code/nof1"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# Vérifier que le répertoire existe
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "❌ Erreur: Le répertoire frontend n'existe pas à: $FRONTEND_DIR"
    exit 1
fi

echo "📂 Répertoire: $FRONTEND_DIR"
cd "$FRONTEND_DIR" || exit 1

# Vérifier que node_modules existe
if [ ! -d "node_modules" ]; then
    echo "📦 Installation des dépendances..."
    npm install
fi

echo ""
echo "✅ Lancement du serveur de développement..."
echo "🌐 URL: http://localhost:5173"
echo ""
echo "💡 Pour arrêter: Ctrl+C"
echo ""

npm run dev