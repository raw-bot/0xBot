#!/bin/bash
# Script d'installation automatique du système de logging LLM

echo "🚀 Installation du Système de Logging LLM Détaillé"
echo "=================================================="
echo ""

# Vérifier qu'on est à la racine du projet
if [ ! -f "dev.sh" ]; then
    echo "❌ Erreur : Ce script doit être exécuté depuis la racine du projet 0xBot"
    echo "   cd /Users/cube/Documents/00-code/0xBot"
    exit 1
fi

echo "✅ Racine du projet détectée"
echo ""

# Étape 1 : Copier le logger
echo "📦 Étape 1/4 : Copie du service de logging..."
cp llm_decision_logger.py backend/src/services/
if [ $? -eq 0 ]; then
    echo "   ✅ llm_decision_logger.py copié"
else
    echo "   ❌ Erreur lors de la copie"
    exit 1
fi
echo ""

# Étape 2 : Copier le script d'analyse
echo "📊 Étape 2/4 : Copie du script d'analyse..."
cp analyze_llm_logs.py .
chmod +x analyze_llm_logs.py
if [ $? -eq 0 ]; then
    echo "   ✅ analyze_llm_logs.py copié et rendu exécutable"
else
    echo "   ❌ Erreur lors de la copie"
    exit 1
fi
echo ""

# Étape 3 : Créer les dossiers
echo "📁 Étape 3/4 : Création des dossiers de logs..."
mkdir -p logs/llm_decisions/prompts
mkdir -p logs/llm_decisions/responses
if [ $? -eq 0 ]; then
    echo "   ✅ Dossiers créés : logs/llm_decisions/{prompts,responses}"
else
    echo "   ❌ Erreur lors de la création des dossiers"
    exit 1
fi
echo ""

# Étape 4 : Rappel des modifications manuelles
echo "⚠️  Étape 4/4 : Modifications manuelles requises"
echo "=================================================="
echo ""
echo "Il reste à modifier 2 fichiers :"
echo ""
echo "1. backend/src/services/enriched_llm_prompt_service.py"
echo "   → Ouvrir MODIFICATIONS.patch pour voir les changements exacts"
echo "   → 5 modifications à faire"
echo ""
echo "2. backend/src/services/trading_engine_service.py"
echo "   → 1 modification à faire"
echo ""
echo "📄 Toutes les instructions sont dans MODIFICATIONS.patch"
echo ""
echo "Une fois les modifications faites :"
echo "   ./dev.sh"
echo ""
echo "Pour vérifier l'installation :"
echo "   # Attendre 1-2 cycles (6-10 min)"
echo "   ls logs/llm_decisions/prompts/ | wc -l"
echo "   python3 analyze_llm_logs.py"
echo ""
echo "=================================================="
echo "✅ Installation automatique terminée !"
echo "   Passez aux modifications manuelles (voir MODIFICATIONS.patch)"
echo "=================================================="
