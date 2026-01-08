# ⚡ Quick Start - AI Trading Bot

## 🚀 Lancement Rapide du Projet

### 📋 Prérequis
- Docker & Docker Compose installés
- Python 3.13 installé
- Terminal ouvert

---

## 1️⃣ Premier Lancement (Setup Initial)

### Étape 1.1: Clone et Navigate
```bash
cd /Users/cube/Documents/00-code/0xBot
```

### Étape 1.2: Démarre les Services Docker
```bash
# Démarre PostgreSQL + Redis
cd docker
docker-compose up -d

# Vérifie que c'est OK
docker-compose ps
# Tu dois voir: postgres et redis en "Up"
```

### Étape 1.3: Configure l'Environnement
```bash
# Retourne à la racine
cd ..

# Copie le template .env
cp .env.example .env

# Édite .env avec tes clés API (IMPORTANT!)
nano .env  # ou vim, ou VSCode
```

**Dans `.env`, ajoute AU MOINS:**
```bash
# Pour Qwen Max (LE MEILLEUR +60%)
QWEN_API_KEY=sk-ta-vraie-clé-ici

# OU pour DeepSeek (EXCELLENT +40%)
DEEPSEEK_API_KEY=ta-vraie-clé-ici
```

### Étape 1.4: Setup Backend Python
```bash
cd backend

# Crée l'environnement virtuel (si pas déjà fait)
python3.13 -m venv venv

# Active l'environnement
source venv/bin/activate

# Installe les dépendances
pip install -r requirements.txt

# Lance les migrations
alembic upgrade head
```

---

## 2️⃣ Lancement Normal (Après le Setup)

### Méthode Simple (1 commande)
```bash
cd /Users/cube/Documents/00-code/0xBot/backend
source venv/bin/activate && python -m uvicorn src.main:app --host 0.0.0.0 --port 8020 --reload
```

### Ou Étape par Étape
```bash
# 1. Va dans backend
cd /Users/cube/Documents/00-code/0xBot/backend

# 2. Active l'environnement virtuel
source venv/bin/activate

# 3. Lance le serveur
python -m uvicorn src.main:app --host 0.0.0.0 --port 8020 --reload
```

### ✅ Tu Dois Voir:
```
🚀 Starting AI Trading Agent API...
✅ Redis connected
✅ Database connected
✅ Bot scheduler started
✅ Application ready
📊 Access API docs at http://localhost:8020/docs
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8020
```

---

## 3️⃣ Test de l'API

### Ouvre Swagger UI
```bash
# Dans ton navigateur
http://localhost:8020/docs
```

### OU Test en Ligne de Commande

#### A. Crée un Utilisateur
```bash
curl -X POST http://localhost:8020/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "trader@example.com",
    "password": "password123"
  }'
```

**Résultat**: Copie le `token` retourné!

#### B. Crée un Bot Qwen
```bash
# Remplace YOUR_TOKEN par ton vrai token
curl -X POST http://localhost:8020/api/bots \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Qwen Champion",
    "model_name": "qwen-max-3",
    "capital": 1000,
    "paper_trading": true
  }'
```

**Résultat**: Copie le `id` du bot!

#### C. Démarre le Bot
```bash
# Remplace YOUR_TOKEN et BOT_ID
curl -X POST http://localhost:8020/api/bots/BOT_ID/start \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### D. Vérifie l'État
```bash
# Voir l'état du bot
curl -X GET http://localhost:8020/api/bots/BOT_ID \
  -H "Authorization: Bearer YOUR_TOKEN"

# Voir les positions
curl -X GET http://localhost:8020/api/bots/BOT_ID/positions \
  -H "Authorization: Bearer YOUR_TOKEN"

# Voir les trades
curl -X GET http://localhost:8020/api/bots/BOT_ID/trades \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 4️⃣ Arrêt du Serveur

### Arrêt Simple
```bash
# Dans le terminal où tourne uvicorn
Ctrl + C
```

### Arrêt des Services Docker
```bash
cd /Users/cube/Documents/00-code/0xBot/docker
docker-compose down
```

### Arrêt Complet
```bash
# Arrête le serveur
Ctrl + C

# Arrête Docker
cd /Users/cube/Documents/00-code/0xBot/docker
docker-compose down

# Désactive venv
deactivate
```

---

## 5️⃣ Redémarrage Complet

```bash
# 1. Démarre Docker
cd /Users/cube/Documents/00-code/0xBot/docker
docker-compose up -d

# 2. Démarre le serveur
cd ../backend
source venv/bin/activate
python -m uvicorn src.main:app --host 0.0.0.0 --port 8020 --reload
```

---

## 6️⃣ Commandes Utiles

### Voir les Logs Docker
```bash
# Logs PostgreSQL
docker logs trading_agent_postgres -f

# Logs Redis
docker logs trading_agent_redis -f
```

### Migrations Database
```bash
cd /Users/cube/Documents/00-code/0xBot/backend
source venv/bin/activate

# Voir l'état des migrations
alembic current

# Créer une nouvelle migration
alembic revision --autogenerate -m "Description"

# Appliquer les migrations
alembic upgrade head

# Revenir en arrière
alembic downgrade -1
```

### Réinitialiser la Database
```bash
# ATTENTION: Efface TOUT!
cd /Users/cube/Documents/00-code/0xBot/docker
docker-compose down -v  # -v efface les volumes
docker-compose up -d

# Puis recrée les tables
cd ../backend
source venv/bin/activate
alembic upgrade head
```

### Vérifier les Bots Actifs
```bash
# Se connecter à PostgreSQL
docker exec -it trading_agent_postgres psql -U postgres -d trading_agent

# Voir tous les bots
SELECT id, name, model_name, status, capital FROM bots;

# Voir les positions ouvertes
SELECT * FROM positions WHERE status = 'open';

# Voir les derniers trades
SELECT * FROM trades ORDER BY executed_at DESC LIMIT 10;

# Quitter
\q
```

---

## 7️⃣ Scripts de Développement

### Lancer tous les Tests
```bash
cd /Users/cube/Documents/00-code/0xBot/backend
source venv/bin/activate
pytest tests/ -v
```

### Linter le Code
```bash
# Black (format)
black src/

# Vérifier sans modifier
black --check src/
```

### Voir les Dépendances
```bash
pip list
pip freeze > requirements-freeze.txt
```

---

## 8️⃣ Troubleshooting

### Le serveur ne démarre pas
```bash
# Vérifie que Docker tourne
docker ps

# Vérifie les logs
cd /Users/cube/Documents/00-code/0xBot/backend
source venv/bin/activate
python -m uvicorn src.main:app --host 0.0.0.0 --port 8020 --log-level debug
```

### Erreur "Module not found"
```bash
# Réinstalle les dépendances
cd /Users/cube/Documents/00-code/0xBot/backend
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

### Erreur Database
```bash
# Redémarre PostgreSQL
cd /Users/cube/Documents/00-code/0xBot/docker
docker-compose restart postgres

# Vérifie la connexion
docker exec -it trading_agent_postgres psql -U postgres -c "SELECT 1;"
```

### Port déjà utilisé
```bash
# Trouve qui utilise le port 8020
lsof -i :8020

# Tue le processus (remplace PID)
kill -9 PID

# Ou utilise un autre port
python -m uvicorn src.main:app --host 0.0.0.0 --port 8021 --reload
```

---

## 9️⃣ Variables d'Environnement Importantes

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/trading_agent

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET=change-this-in-production

# API Keys (choisis au moins UNE IA)
QWEN_API_KEY=sk-...          # ⭐ RECOMMANDÉ (+60%)
DEEPSEEK_API_KEY=sk-...      # ✅ BON AUSSI (+40%)
CLAUDE_API_KEY=sk-ant-...    # ⚠️ Décevant (-5%)
OPENAI_API_KEY=sk-...        # ⛔ À ÉVITER (-78%)

# Binance (pour trading réel)
BINANCE_API_KEY=...
BINANCE_SECRET_KEY=...
```

---

## 🔟 Monitoring en Temps Réel

### Logs du Serveur
```bash
# Les logs apparaissent automatiquement dans le terminal
# Tu verras:
{"message": "Bot monitor started"}
{"message": "Trading Cycle Started"}
{"message": "LLM Decision: ..."}
{"message": "Trade executed"}
```

### Tester Health Check
```bash
curl http://localhost:8020/health
# Résultat: {"status": "healthy"}
```

### Voir la Doc API
```bash
# OpenAPI/Swagger
http://localhost:8020/docs

# ReDoc (alternative)
http://localhost:8020/redoc
```

---

## 📊 Workflow Complet Recommandé

```bash
# 1. Démarre Docker
cd docker && docker-compose up -d

# 2. Active venv et lance serveur
cd ../backend
source venv/bin/activate
python -m uvicorn src.main:app --host 0.0.0.0 --port 8020 --reload

# 3. Dans un autre terminal: teste
curl http://localhost:8020/health

# 4. Ouvre Swagger
open http://localhost:8020/docs  # macOS
# ou xdg-open http://localhost:8020/docs  # Linux

# 5. Crée et teste tes bots via Swagger UI!
```

---

## 🎯 Commande Ultime (Tout en Un)

```bash
cd /Users/cube/Documents/00-code/0xBot && \
  cd docker && docker-compose up -d && \
  cd ../backend && \
  source venv/bin/activate && \
  python -m uvicorn src.main:app --host 0.0.0.0 --port 8020 --reload
```

**Ensuite**: Ouvre http://localhost:8020/docs et c'est parti! 🚀

---

**Tout est prêt! Bon trading avec Qwen Max! 🏆**