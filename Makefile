# Makefile pour NOF1 Trading Bot
# Utilisation: make <target>

.PHONY: help setup dev test lint clean status logs install stop

# Variables
PYTHON = backend/venv/bin/python
PIP = backend/venv/bin/pip
NPM = npm

help: ## Affiche cette aide
	@echo "🚀 NOF1 Trading Bot - Commandes disponibles:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

setup: ## Configuration complète de l'environnement
	@echo "🚀 Configuration de l'environnement..."
	./setup.sh
	@make install
	@echo "✅ Setup terminé!"

install: ## Installe les dépendances
	@echo "📦 Installation des dépendances..."
	@if [ -f "frontend/package.json" ]; then \
		cd frontend && $(NPM) install; \
	fi
	@echo "✅ Dépendances installées"

dev: ## Lance le serveur en mode développement
	@echo "🚀 Mode développement..."
	./dev.sh

start: ## Démarre le serveur backend
	@echo "🚀 Démarrage du serveur..."
	./start.sh

stop: ## Arrête tous les services
	@echo "🛑 Arrêt des services..."
	@docker-compose down || (cd docker && docker-compose down && cd ..)
	@echo "✅ Services arrêtés"

test: ## Exécute les tests
	@echo "🧪 Exécution des tests..."
	@if [ -d "backend/tests" ]; then \
		cd backend && $(PYTHON) -m pytest tests/ -v; \
	fi
	@echo "✅ Tests terminés"

test-audit: ## Exécute les tests d'audit
	@echo "🔍 Tests d'audit..."
	@cd backend/scripts/tests && $(PYTHON) audit_critical_paths.py

lint: ## Formatage et linting du code
	@echo "🎨 Formatage du code..."
	@cd backend && $(PIP) install black isort mypy > /dev/null 2>&1 || true
	@cd backend && $(PYTHON) -m black . --line-length 100
	@cd backend && $(PYTHON) -m isort . --profile black
	@echo "✅ Code formaté"

type-check: ## Vérification des types
	@echo "🔍 Vérification des types..."
	@cd backend && $(PYTHON) -m mypy src --config-file=pyproject.toml

clean: ## Nettoie les caches et logs
	@echo "🧹 Nettoyage..."
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@rm -f backend.log
	@rm -rf frontend/node_modules 2>/dev/null || true
	@rm -rf frontend/dist 2>/dev/null || true
	@echo "✅ Nettoyage terminé"

status: ## Affiche le statut des services
	@echo "📊 Statut des services:"
	@echo ""
	@echo "🐳 Docker containers:"
	@docker ps --filter "name=trading_agent" || echo "Docker non disponible"
	@echo ""
	@echo "🌐 Services web:"
	@curl -s http://localhost:8020/health > /dev/null && echo "✅ API Backend: Fonctionnel" || echo "❌ API Backend: Non accessible"
	@curl -s http://localhost:5173 > /dev/null && echo "✅ Frontend: Fonctionnel" || echo "❌ Frontend: Non accessible"

logs: ## Affiche les logs
	@echo "📋 Logs:"
	@if [ -f "backend.log" ]; then \
		tail -f backend.log; \
	else \
		echo "Logs backend non trouvés"; \
	fi

build: ## Build le frontend
	@echo "🏗️ Build du frontend..."
	@cd frontend && $(NPM) run build
	@echo "✅ Build terminé"

reset: ## Reset complet (danger!)
	@echo "⚠️ Reset complet - Supprime toutes les données!"
	@make stop
	@docker-compose down -v || (cd docker && docker-compose down -v && cd ..)
	@make clean
	@echo "✅ Reset terminé"

# Commandes docker directes
db-shell: ## Shell dans PostgreSQL
	@docker exec -it trading_agent_postgres psql -U postgres -d trading_agent

db-backup: ## Backup de la base de données
	@docker exec trading_agent_postgres pg_dump -U postgres trading_agent > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup créé"

redis-cli: ## Client Redis
	@docker exec -it trading_agent_redis redis-cli

# Debug
debug-backend: ## Debug du backend avec pdb
	@cd backend && $(PYTHON) -m pdb src/main.py

debug-logs: ## Logs détaillés
	@docker-compose logs -f --tail=100 || (cd docker && docker-compose logs -f --tail=100 && cd ..)

# Utilitaires
health-check: ## Vérifie la santé de tous les services
	@echo "🔍 Health check..."
	@curl -f http://localhost:8020/health || echo "❌ API Backend DOWN"
	@curl -f http://localhost:5173 || echo "❌ Frontend DOWN"
	@docker exec trading_agent_postgres pg_isready -U postgres || echo "❌ PostgreSQL DOWN"
	@docker exec trading_agent_redis redis-cli ping || echo "❌ Redis DOWN"
	@echo "✅ Health check terminé"

# Aliases
up: dev
down: stop
restart: stop dev
check: type-check test

# Installation initiale
init: setup
	@echo ""
	@echo "🎉 Initialisation terminée!"
	@echo "Prochaines étapes:"
	@echo "  1. Configurez vos clés API dans .env"
	@echo "  2. Lancez: make dev"
	@echo "  3. Ouvrez: http://localhost:5173"
