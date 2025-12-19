# Scripts de Gestion du Bot

Ce dossier contient les scripts utilitaires pour gérer le bot de trading **0xBot**.

---

## 📋 Vue d'ensemble

Deux solutions complémentaires pour gérer le bot :

| Script | Usage | Avantages |
|--------|-------|-----------|
| `reset.sh` | Reset rapide | ⚡ Rapide, garde l'historique |
| `create_test_bot.py` | Nouveau bot propre | 🆕 Fresh start, nettoie le cache |

---

## ⚡ reset.sh - Reset Rapide

**Quand l'utiliser :**
- ✅ Tests quotidiens
- ✅ Développement itératif
- ✅ Garder l'historique

**Ce qu'il fait :**
1. Supprime toutes les positions du bot
2. Supprime tous les trades du bot
3. Réinitialise le capital à une valeur donnée
4. Reset le total_pnl à $0.00

### Prérequis

- PostgreSQL installé et accessible
- Variables d'environnement (optionnel) :
  - `POSTGRES_HOST` (défaut: localhost)
  - `POSTGRES_PORT` (défaut: 5432)
  - `POSTGRES_DB` (défaut: trading_agent)
  - `POSTGRES_USER` (défaut: postgres)
  - `POSTGRES_PASSWORD` (défaut: postgres)

### Usage

**Reset avec capital par défaut ($10,000)** :
```bash
cd backend/scripts
./reset.sh <bot-id>
```

**Reset avec capital personnalisé** :
```bash
cd backend/scripts
./reset.sh <bot-id> 5000
```

### Exemple

```bash
# Reset du bot avec $10,000
./reset.sh d8f9e1a2-3b4c-5d6e-7f8g-9h0i1j2k3l4m

# Reset du bot avec $5,000
./reset.sh d8f9e1a2-3b4c-5d6e-7f8g-9h0i1j2k3l4m 5000
```

---

## 🆕 create_test_bot.py - Nouveau Bot Propre

**Quand l'utiliser :**
- ✅ DB vide (0 bytes)
- ✅ Cache mémoire persistant
- ✅ Après corrections majeures
- ✅ Changer de capital

**Ce qu'il fait :**
1. Détecte si un bot actif existe déjà
2. Propose de le réinitialiser ou d'en créer un nouveau
3. Configure automatiquement les paramètres optimisés
4. Active le mode paper trading par défaut
5. **🆕 Sauvegarde automatiquement le bot ID dans `.env.dev`** (plus besoin de copier-coller !)

### Prérequis

- Python 3.11+
- Virtual environment activé
- Base de données PostgreSQL configurée

### Usage

```bash
cd backend
source venv/bin/activate
python scripts/create_test_bot.py
```

### Configuration du bot créé

- 💰 Capital Initial : $10,000.00
- 💰 Capital Actuel : $10,000.00
- 🤖 Nom : **0xBot**
- 📊 Paper Trading : Activé
- 🎯 Modèle LLM : qwen-max
- 📈 Symboles : BTC/USDT, ETH/USDT, SOL/USDT
- ⚙️  Paramètres de risque optimisés :
  - Max position : 15%
  - Max exposure : 85%
  - Stop Loss : 3.5%
  - Take Profit : 7%

---

## 📊 Quand Utiliser Quoi ?

| Situation | Solution |
|-----------|----------|
| Test rapide du jour | `reset.sh` |
| DB vide (0 bytes) | `create_test_bot.py` |
| Cache mémoire qui persiste | `create_test_bot.py` |
| Après gros bugs corrigés | `create_test_bot.py` |
| Garder l'historique des trades | `reset.sh` |
| Changer le capital initial | `reset.sh` (simple) ou `create_test_bot.py` (nouveau bot) |

---

## 🚀 Workflow Typique

### Développement quotidien

```bash
# 1. Modifier le code
vim backend/src/services/trading_engine_service.py

# 2. Reset rapide du bot
cd backend/scripts
./reset.sh <bot-id>

# 3. Relancer le bot
cd ../..
./start.sh
```

### Après corrections majeures

```bash
# 1. Créer un nouveau bot propre
cd backend
source venv/bin/activate
python scripts/create_test_bot.py

# 2. Le bot ID est automatiquement sauvegardé dans .env.dev

# 3. Lancer le bot
cd ..
./dev.sh  # ou ./start.sh
```

---

## ⚠️ Important

### Avant d'exécuter ces scripts

1. **Arrêtez le bot** :
   ```bash
   ./stop.sh
   ```

2. Les deux scripts sont **complémentaires**, pas concurrents :
   - `reset.sh` → rapide, garde l'historique
   - `create_test_bot.py` → fresh start, nettoie le cache, **configure automatiquement le bot ID**

### Sécurité

- Les deux scripts demandent confirmation avant modification
- `reset.sh` utilise une transaction PostgreSQL
- Aucune perte de données historiques (sauf ce qui est spécifiquement supprimé)

---

## 🔍 Autres Scripts Utiles

### Dossier `sql/`

Scripts SQL pour opérations avancées (voir `sql/README.md`) :
- `activate_bot.sql` - Activer un bot
- `check_bot_health.sql` - Vérifier l'état du bot
- `update_bot_capital.sql` - Modifier le capital manuellement
- `update_bot_quota.sql` - Gérer les quotas de trading
- `force_reset_trades.sql` - Reset forcé des trades

### Dossier `tests/`

Scripts de test et diagnostic (voir `tests/README.md`) :
- `test_api.py` - Tester les endpoints API
- `test_okx_connection.py` - Tester la connexion OKX
- `diagnose_okx_keys.py` - Diagnostiquer les clés API

---

## 📚 Documentation Complète

Pour plus de détails, consultez :
- 📖 `corrections/guide-gestion-bot.md` - Guide complet de gestion
- 📖 `docs/QUICK_START.md` - Guide de démarrage rapide
- 📖 `README.md` - Documentation principale du projet

---

**💡 L'Essentiel**

- `reset.sh` → rapide, garde l'historique
- `create_test_bot.py` → fresh start, nettoie le cache, **configure automatiquement le bot ID**
- Les deux sont **complémentaires**, pas concurrents
- ✨ **Workflow 100% automatisé** : créer → lancer, c'est tout !

C'est tout ! 🎯
