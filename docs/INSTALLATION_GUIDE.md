# 🤖 Guide d'Installation 0xBot - De Zéro à Hero

Guide complet pour installer et lancer le bot de trading IA **0xBot** sur votre machine.

---

## 📋 Prérequis Système

### Système d'Exploitation
- ✅ macOS (Apple Silicon ou Intel)
- ✅ Linux (Ubuntu/Debian)
- ✅ Windows (avec WSL2)

### Logiciels Requis
- **Docker Desktop** : [Télécharger ici](https://www.docker.com/products/docker-desktop)
- **Git** : [Télécharger ici](https://git-scm.com/downloads)
- **Python 3.11+** : [Télécharger ici](https://www.python.org/downloads/)

### Pour macOS uniquement
```bash
# Installer Homebrew si pas déjà installé
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Installer TA-Lib (nécessaire pour l'analyse technique)
brew install ta-lib
```

### Pour Linux (Ubuntu/Debian)
```bash
# Installer TA-Lib
sudo apt-get update
sudo apt-get install -y build-essential wget
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
cd ..
rm -rf ta-lib ta-lib-0.4.0-src.tar.gz
```

---

## 🔑 Étape 1 : Obtenir les Clés API

### 1.1 Clé API Alibaba Cloud (Qwen-max LLM)

Le bot utilise **Qwen-max** comme modèle IA pour prendre les décisions de trading.

1. **Créer un compte** : [https://www.alibabacloud.com](https://www.alibabacloud.com)

2. **Obtenir votre clé API** :
   - Aller sur : [https://modelstudio.console.alibabacloud.com/?tab=globalset#/efm/api_key](https://modelstudio.console.alibabacloud.com/?tab=globalset#/efm/api_key)
   - Créer une nouvelle clé API
   - **Copier et sauvegarder** la clé (elle ne sera affichée qu'une fois !)

3. **Format de la clé** :
   ```
   sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

### 1.2 Clés API OKX (Exchange Crypto)

Le bot utilise **OKX** pour obtenir les données de marché en temps réel.

**Option A : Mode Paper Trading (Recommandé pour débuter)**
- ✅ **Pas besoin de clés API !**
- Le bot utilise les données publiques de marché
- Trades simulés (pas d'argent réel)

**Option B : Trading Réel (Avancé)**
1. Créer un compte sur [OKX.com](https://www.okx.com)
2. Aller dans **Account** → **API** → **Create API Key**
3. Activer les permissions : **Read** + **Trade**
4. Noter :
   - API Key
   - Secret Key
   - Passphrase

⚠️ **Important** : Commencez toujours en mode **Paper Trading** pour tester !

---

## 📦 Étape 2 : Cloner le Projet

```bash
# Cloner le repository
git clone <URL_DU_REPO>
cd 0xBot

# Vérifier que vous êtes dans le bon dossier
ls -la
# Vous devriez voir : backend/, frontend/, docker/, etc.
```

---

## 🐳 Étape 3 : Démarrer PostgreSQL et Redis

```bash
# Démarrer Docker Desktop (GUI)
# Puis dans le terminal :

cd docker
docker-compose up -d

# Vérifier que tout tourne bien
docker ps
# Vous devriez voir : trading_agent_postgres et trading_agent_redis
```

✅ PostgreSQL tourne sur le port **5432**  
✅ Redis tourne sur le port **6379**

---

## ⚙️ Étape 4 : Configuration du .env

### 4.1 Créer le fichier .env principal

```bash
# À la racine du projet (0xBot/)
nano .env
```

**Copier-coller cette configuration** (remplacer les `XXX` par vos vraies clés) :

```bash
# ============================================
# Configuration 0xBot - Trading Bot
# ============================================

# ─────────────────────────────────────────
# Base de données PostgreSQL
# ─────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/trading_agent

# ─────────────────────────────────────────
# Redis (Cache)
# ─────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ─────────────────────────────────────────
# Alibaba Cloud (Qwen-max LLM)
# ─────────────────────────────────────────
# Obtenir la clé ici : https://modelstudio.console.alibabacloud.com/?tab=globalset#/efm/api_key
DASHSCOPE_API_KEY=sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# ─────────────────────────────────────────
# OKX Exchange (Optionnel pour paper trading)
# ─────────────────────────────────────────
# Laisser vide pour le paper trading (recommandé pour débuter)
OKX_API_KEY=
OKX_SECRET_KEY=
OKX_PASSPHRASE=

# ─────────────────────────────────────────
# Sécurité API Backend
# ─────────────────────────────────────────
# Générer une clé aléatoire : openssl rand -hex 32
JWT_SECRET=votre_cle_secrete_aleatoire_ici
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440

# ─────────────────────────────────────────
# Configuration Serveur
# ─────────────────────────────────────────
API_HOST=0.0.0.0
API_PORT=8020
LOG_LEVEL=INFO
ENVIRONMENT=development
```

**Sauvegarder** : `Ctrl+X` puis `Y` puis `Entrée`

### 4.2 Créer le fichier .env.dev (Auto-start)

```bash
# À la racine du projet (0xBot/)
nano .env.dev
```

**Copier-coller** :

```bash
# Configuration pour l'auto-démarrage du bot

# Credentials d'authentification
DEV_EMAIL=demo@0xbot.com
DEV_PASSWORD=Demo1234!

# Bot ID (sera rempli automatiquement par le script)
AUTO_START_BOT_ID=
```

**Sauvegarder** : `Ctrl+X` puis `Y` puis `Entrée`

---

## 🔧 Étape 5 : Installation Backend

```bash
cd backend

# Créer le virtual environment
python3 -m venv venv

# Activer le venv
source venv/bin/activate  # Sur macOS/Linux
# OU
.\venv\Scripts\activate   # Sur Windows

# Installer les dépendances
pip install -r requirements.txt

# Lancer les migrations de base de données
alembic upgrade head
```

✅ Si tout s'est bien passé, vous devriez voir :
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

---

## 👤 Étape 6 : Créer un Utilisateur

```bash
# Toujours dans backend/ avec le venv activé
cd ..  # Retour à la racine
```

Créez un script temporaire pour créer votre utilisateur :

```bash
nano create_user.py
```

**Copier-coller** :

```python
#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from sqlalchemy import select
from backend.src.core.database import AsyncSessionLocal
from backend.src.models.user import User
from passlib.hash import bcrypt

async def create_user():
    async with AsyncSessionLocal() as db:
        # Vérifier si l'utilisateur existe
        query = select(User).where(User.email == "demo@0xbot.com")
        result = await db.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            print("✅ Utilisateur existe déjà!")
            return
        
        # Créer l'utilisateur
        user = User(
            email="demo@0xbot.com",
            hashed_password=bcrypt.hash("Demo1234!")
        )
        db.add(user)
        await db.commit()
        print("✅ Utilisateur créé : demo@0xbot.com / Demo1234!")

if __name__ == "__main__":
    asyncio.run(create_user())
```

**Sauvegarder** et **exécuter** :

```bash
python3 create_user.py
# Puis supprimer le script
rm create_user.py
```

---

## 🤖 Étape 7 : Créer le Bot de Trading

```bash
cd backend
source venv/bin/activate  # Réactiver si nécessaire

# Créer le bot (capital $10,000)
python scripts/create_test_bot.py
```

Le script va :
1. ✅ Créer le bot **0xBot**
2. ✅ Configurer le capital initial : **$10,000**
3. ✅ Configurer les cryptos : **BTC, ETH, SOL, BNB, XRP**
4. ✅ **Sauvegarder automatiquement le bot ID** dans `.env.dev` ✨

**Sortie attendue** :
```
✅ Bot créé avec succès!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   Nom: 0xBot
   Capital: $10,000.00
   ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Bot ID sauvegardé dans .env.dev
```

---

## 🚀 Étape 8 : Lancer le Bot !

```bash
cd ..  # Retour à la racine (0xBot/)

# Lancer le bot en mode développement
./dev.sh
```

Le script va :
1. Démarrer le serveur backend
2. Charger automatiquement le bot ID depuis `.env.dev`
3. Démarrer le bot de trading
4. Afficher les logs en temps réel

**Vous devriez voir** :
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 Mode Développement - Auto-Start Bot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 Bot ID depuis .env.dev: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

1️⃣  Démarrage du serveur en arrière-plan...
✓ Serveur lancé
2️⃣  Auto-démarrage du bot...
✅ Serveur prêt !
✅ Authentifié
✅ Bot démarré avec succès !

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Logs en temps réel:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

13:35:22 | ✅ 0xBot | qwen-max | $10,000.00 | 3min cycles
13:35:22 | Trading symbols: BTC/USDT, ETH/USDT, SOL/USDT, BNB/USDT, XRP/USDT
...
```

🎉 **Félicitations ! Votre bot trade maintenant !**

---

## 📊 Étape 9 : Surveiller le Bot

### Voir les logs
Les logs s'affichent automatiquement dans le terminal.

### API Backend
- **URL** : http://localhost:8020
- **Documentation API** : http://localhost:8020/docs
- **Health Check** : http://localhost:8020/health

### Arrêter le bot
```bash
Ctrl+C  # Dans le terminal où tourne dev.sh
```

---

## 🔧 Gestion du Bot

### Reset rapide (pour tests quotidiens)
```bash
cd backend/scripts
./reset.sh <bot-id> [capital]

# Exemples :
./reset.sh xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx          # Reset à $10,000
./reset.sh xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx 5000    # Reset à $5,000
```

### Créer un nouveau bot propre
```bash
cd backend
source venv/bin/activate
python scripts/create_test_bot.py
# Le bot ID sera automatiquement sauvegardé dans .env.dev
```

### Relancer le bot
```bash
cd ..  # À la racine
./dev.sh
```

---

## ⚙️ Configuration Avancée

### Changer les cryptos tradées

**Option 1 : Via SQL**
```bash
docker exec -i trading_agent_postgres psql -U postgres -d trading_agent -c \
"UPDATE bots SET trading_symbols = '[\"BTC/USDT\", \"ETH/USDT\", \"SOL/USDT\", \"BNB/USDT\", \"XRP/USDT\", \"DOGE/USDT\"]'::jsonb WHERE status = 'active';"
```

**Option 2 : Via script SQL**
```bash
# Éditer et exécuter
nano backend/scripts/sql/update_trading_symbols.sql
docker exec -i trading_agent_postgres psql -U postgres -d trading_agent < backend/scripts/sql/update_trading_symbols.sql
```

### Modifier les paramètres de risque

Les paramètres sont configurés dans `create_test_bot.py` :
- `max_position_pct: 0.15` → Max 15% du capital par position
- `max_exposure_pct: 0.85` → Max 85% du capital utilisé
- `stop_loss_pct: 0.035` → Stop Loss à 3.5%
- `take_profit_pct: 0.07` → Take Profit à 7%

---

## 🐛 Dépannage

### Problème : PostgreSQL ne démarre pas
```bash
# Vérifier Docker
docker ps

# Relancer les conteneurs
cd docker
docker-compose down
docker-compose up -d
```

### Problème : "Module not found"
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Problème : "Not authorized" (403)
Le bot n'appartient pas au bon utilisateur. Transférer le bot :
```bash
docker exec -i trading_agent_postgres psql -U postgres -d trading_agent -c \
"UPDATE bots SET user_id = (SELECT id FROM users WHERE email = 'demo@0xbot.com' LIMIT 1) WHERE status = 'active';"
```

### Problème : Clé API Qwen invalide
1. Vérifier que la clé commence bien par `sk-`
2. Vérifier qu'elle est bien copiée dans `.env` → `DASHSCOPE_API_KEY=`
3. Relancer le serveur

### Voir tous les logs
```bash
tail -f backend.log
```

---

## 📚 Ressources

### Documentation
- **API Backend** : http://localhost:8020/docs
- **Guide complet** : `docs/QUICK_START.md`
- **Scripts utiles** : `backend/scripts/README.md`

### Liens Utiles
- **Alibaba Cloud API Keys** : [https://modelstudio.console.alibabacloud.com/?tab=globalset#/efm/api_key](https://modelstudio.console.alibabacloud.com/?tab=globalset#/efm/api_key)
- **OKX API** : [https://www.okx.com/account/my-api](https://www.okx.com/account/my-api)
- **Docker Desktop** : [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)

### Cryptos Supportées
Le bot peut trader sur n'importe quelle crypto disponible sur OKX au format `/USDT` :
- BTC, ETH, SOL, BNB, XRP (par défaut)
- ADA, AVAX, MATIC, DOT, LINK, UNI, ATOM, etc.

---

## ✅ Checklist Finale

Avant de lancer le bot, vérifiez que :

- [ ] Docker Desktop est lancé
- [ ] PostgreSQL et Redis tournent (`docker ps`)
- [ ] `.env` est configuré avec la clé Alibaba Cloud
- [ ] `.env.dev` est créé
- [ ] Virtual env est activé (`source venv/bin/activate`)
- [ ] Dépendances installées (`pip install -r requirements.txt`)
- [ ] Migrations effectuées (`alembic upgrade head`)
- [ ] Utilisateur créé (demo@0xbot.com)
- [ ] Bot créé (`python scripts/create_test_bot.py`)
- [ ] Bot ID sauvegardé dans `.env.dev` automatiquement

**Si tout est ✅, lancez : `./dev.sh`** 🚀

---

## 🎯 Mode Paper Trading vs Trading Réel

### Paper Trading (Par défaut)
- ✅ **Pas besoin de clés OKX**
- ✅ Trades simulés
- ✅ Données de marché réelles
- ✅ Parfait pour tester et apprendre
- ✅ **Zéro risque**

### Trading Réel (Avancé)
- ⚠️ Nécessite des clés API OKX
- ⚠️ Argent réel en jeu
- ⚠️ Testez d'abord en paper trading !
- ⚠️ Commencez avec un petit capital

Pour passer en mode réel :
1. Obtenir les clés API OKX
2. Les ajouter dans `.env`
3. Dans la DB : `UPDATE bots SET paper_trading = false WHERE id = '<bot-id>';`
4. Relancer le bot

---

## 🎉 Prêt à Trader !

Votre bot **0xBot** est maintenant opérationnel ! Il va :
- 📊 Analyser les marchés toutes les 3 minutes
- 🧠 Utiliser l'IA Qwen-max pour prendre des décisions
- 💰 Gérer automatiquement vos positions
- 📈 Suivre les tendances et opportunités

**Bon trading ! 🚀**

---

*Version : 1.0 | Dernière mise à jour : 2025-10-26*

