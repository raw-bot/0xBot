# 🤖 0xBot - AI-Powered Crypto Trading Bot

Bot de trading automatisé utilisant l'intelligence artificielle **DeepSeek** pour trader les cryptomonnaies sur **OKX**.

---

## ✨ Caractéristiques

- 🧠 **IA DeepSeek** - Décisions de trading intelligentes basées sur l'analyse technique
- 📊 **5 Cryptos** - BTC, ETH, SOL, BNB, XRP (configurable)
- 💰 **Paper Trading** - Testez sans risque avec de l'argent virtuel
- 🔄 **Auto-Trading** - Cycles automatiques toutes les 3 minutes
- 📈 **Analyse Multi-Timeframe** - 5min + 1H pour des décisions précises
- ⚡ **Gestion du Risque** - Stop-loss, take-profit, exposition maximale
- 🎯 **100% Automatisé** - Configuration et lancement en quelques minutes

---

## 🚀 Quick Start

### 1. Prérequis

- **Docker Desktop** installé et lancé
- **Python 3.11+** installé
- **Clé API DeepSeek** : [Obtenir ici](https://platform.deepseek.com/)

### 2. Installation Rapide

```bash
# Cloner le projet
git clone <URL_DU_REPO>
cd 0xBot

# Démarrer PostgreSQL & Redis
cd docker && docker-compose up -d && cd ..

# Configurer les variables d'environnement
cp .env.example .env
nano .env  # Ajouter votre DEEPSEEK_API_KEY

# Installer les dépendances
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Lancer les migrations
alembic upgrade head

# Créer le bot
python scripts/create_test_bot.py
# ✨ Le bot ID est automatiquement sauvegardé dans .env.dev

# Lancer le bot
cd ..
./dev.sh
```

🎉 **C'est tout !** Votre bot trade maintenant.

---

## 📚 Documentation Complète

Pour une **installation pas à pas détaillée** avec explications :

👉 **[Guide d'Installation Complet](docs/INSTALLATION_GUIDE.md)**

Autres guides :

- 📖 [Quick Start](docs/QUICK_START.md)
- 🔧 [Gestion du Bot](corrections/guide-gestion-bot.md)
- 📊 [Scripts Utiles](backend/scripts/README.md)

---

## 🎯 Configuration par Défaut

| Paramètre           | Valeur                  | Description                  |
| ------------------- | ----------------------- | ---------------------------- |
| **Capital Initial** | $10,000                 | Montant de départ (virtuel)  |
| **Cryptos**         | BTC, ETH, SOL, BNB, XRP | Top 5 cryptomonnaies         |
| **Modèle IA**       | deepseek-chat           | LLM DeepSeek                 |
| **Mode**            | Paper Trading           | Trades simulés (sans risque) |
| **Cycles**          | 3 minutes               | Fréquence d'analyse          |
| **Max Position**    | 15%                     | Maximum par crypto           |
| **Max Exposure**    | 85%                     | Capital total utilisé        |
| **Stop Loss**       | 3.5%                    | Protection contre les pertes |
| **Take Profit**     | 7%                      | Objectif de gains            |

---

## 🔧 Gestion Quotidienne

### Lancer le bot

```bash
./dev.sh
```

### Arrêter le bot

```bash
Ctrl+C
```

### Reset rapide (tests)

```bash
cd backend/scripts
./reset.sh <bot-id>
```

### Créer un nouveau bot

```bash
cd backend
source venv/bin/activate
python scripts/create_test_bot.py
# Le bot ID est auto-configuré ✨
```

### Voir les logs

```bash
tail -f backend.log
```

---

## 📊 API et Interfaces

### Backend API

- **URL** : http://localhost:8020
- **Documentation** : http://localhost:8020/docs
- **Health Check** : http://localhost:8020/health

### Base de Données

- **PostgreSQL** : `localhost:5432`
- **Redis** : `localhost:6379`

---

## 🔑 Clés API Requises

### Obligatoire

**DeepSeek LLM**

- 🔗 [Obtenir la clé API](https://platform.deepseek.com/)
- Variable : `DEEPSEEK_API_KEY=sk-...`
- Utilisation : Prise de décisions IA

### Optionnel (pour trading réel)

**OKX Exchange**

- 🔗 [Obtenir les clés](https://www.okx.com/account/my-api)
- Variables : `OKX_API_KEY`, `OKX_SECRET_KEY`, `OKX_PASSPHRASE`
- Utilisation : Trading réel (laisser vide pour paper trading)

---

## 💡 Modes de Trading

### Paper Trading (Par défaut) ✅

- ✅ **Pas besoin de clés OKX**
- ✅ Trades simulés
- ✅ Données réelles de marché
- ✅ **Zéro risque**
- ✅ Parfait pour tester

### Trading Réel ⚠️

- ⚠️ Nécessite clés API OKX
- ⚠️ Argent réel en jeu
- ⚠️ **Testez d'abord en paper trading !**
- ⚠️ Commencez avec un petit capital

---

## 🛠️ Technologies

### Backend

- **Python 3.11+** - Langage principal
- **FastAPI** - API REST async
- **SQLAlchemy** - ORM async
- **PostgreSQL** - Base de données
- **Redis** - Cache
- **Alembic** - Migrations
- **CCXT** - Connexion exchanges crypto

### IA & Analyse

- **DeepSeek Chat** - Décisions de trading
- **TA-Lib** - Indicateurs techniques (RSI, MACD, EMA, etc.)
- **Pandas/NumPy** - Analyse de données

### Infrastructure

- **Docker** - PostgreSQL & Redis
- **Uvicorn** - Serveur ASGI

---

## 📈 Performance

Le bot analyse en temps réel :

- 📊 Prix et volumes
- 📉 Indicateurs techniques (RSI, MACD, Bollinger, EMA, etc.)
- 🔄 Corrélations entre cryptos
- 📈 Tendances multi-timeframe (5min + 1H)
- 🧠 Sentiment de marché (risk-on/risk-off)

L'IA Qwen-max prend ensuite des décisions de :

- 📍 **ENTRY** - Ouvrir une position (LONG/SHORT)
- 🚪 **EXIT** - Fermer une position
- ⏸️ **HOLD** - Maintenir les positions actuelles

---

## 🔐 Sécurité

- ✅ Authentification JWT pour l'API
- ✅ Variables d'environnement pour les clés
- ✅ `.env` exclu du versioning (`.gitignore`)
- ✅ Mode paper trading par défaut
- ✅ Stop-loss automatique
- ✅ Limites d'exposition

⚠️ **Important** : Ne commitez JAMAIS vos fichiers `.env` !

---

## 📝 Logs et Monitoring

Le bot log toutes ses actions :

- 📊 Analyses de marché
- 🧠 Décisions de l'IA
- 💰 Entrées/sorties de positions
- 📈 PnL en temps réel
- ⚠️ Erreurs et warnings

Format optimisé pour la lisibilité :

```
13:35:22 | ✅ 0xBot | qwen-max | $10,000.00 | 3min cycles
13:35:22 | 📊 Analyzing BTC/USDT
13:35:24 | 💰 Equity: $9,994.95 | Return: -0.05%
13:35:24 | 📍 Total Positions: 2
```

---

## 🐛 Dépannage

### PostgreSQL ne démarre pas

```bash
cd docker
docker-compose down
docker-compose up -d
```

### Module manquant

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Erreur "Not authorized"

```bash
# Transférer le bot au bon utilisateur
docker exec -i trading_agent_postgres psql -U postgres -d trading_agent -c \
"UPDATE bots SET user_id = (SELECT id FROM users WHERE email = 'demo@0xbot.com' LIMIT 1) WHERE status = 'active';"
```

### Plus de détails

👉 Voir le [Guide d'Installation Complet](docs/INSTALLATION_GUIDE.md) section Dépannage

---

## 🎯 Exemples d'Utilisation

### Ajouter des cryptos

```bash
# Via SQL
docker exec -i trading_agent_postgres psql -U postgres -d trading_agent -c \
"UPDATE bots SET trading_symbols = '[\"BTC/USDT\", \"ETH/USDT\", \"SOL/USDT\", \"BNB/USDT\", \"XRP/USDT\", \"DOGE/USDT\"]'::jsonb WHERE status = 'active';"

# Relancer le bot
./dev.sh
```

### Changer le capital

```bash
cd backend/scripts
./reset.sh <bot-id> 5000  # Reset à $5,000
```

### Modifier les paramètres de risque

Éditer `backend/scripts/create_test_bot.py` avant de créer le bot.

---

## 📦 Structure du Projet

```
0xBot/
├── backend/           # API FastAPI + Services de trading
│   ├── alembic/       # Migrations de base de données
│   ├── scripts/       # Scripts utilitaires (reset, create bot)
│   ├── src/           # Code source
│   │   ├── core/      # Database, Redis, Exchange, LLM
│   │   ├── models/    # Modèles SQLAlchemy
│   │   ├── routes/    # Endpoints API
│   │   └── services/  # Logique métier (trading, analyse)
│   └── requirements.txt
├── docker/            # PostgreSQL + Redis
├── docs/              # Documentation
│   └── INSTALLATION_GUIDE.md  # Guide complet
├── corrections/       # Guides de gestion
├── .env               # Config principale (à créer)
├── .env.dev           # Config auto-start (créé automatiquement)
└── dev.sh             # Script de lancement
```

---

## 🤝 Contribution

Améliorations bienvenues ! Le bot est en développement actif.

---

## 📄 Licence

Privé - Usage personnel uniquement.

---

## 🆘 Support

- 📖 [Guide d'Installation](docs/INSTALLATION_GUIDE.md)
- 🔧 [Guide de Gestion](corrections/guide-gestion-bot.md)
- 📊 [Documentation Scripts](backend/scripts/README.md)

---

## 🎉 Démarrage Rapide Ultime

**Pour les pressés** :

```bash
# 1. Démarrer Docker Desktop
# 2. Obtenir clé API : https://modelstudio.console.alibabacloud.com/?tab=globalset#/efm/api_key
# 3. Tout installer et lancer :

cd docker && docker-compose up -d && cd ..
cp .env.example .env  # Puis ajouter DASHSCOPE_API_KEY
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && alembic upgrade head
python scripts/create_test_bot.py && cd .. && ./dev.sh
```

**C'est tout ! Votre bot trade ! 🚀**

---

_Bot de trading alimenté par IA - Utilisez-le de manière responsable_
