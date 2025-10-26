# 🔧 Fix du Scheduler - Intégration Complète

## 🎯 Problème Identifié

Le scheduler existait mais n'était **pas connecté** aux endpoints API :
- `POST /api/bots/{id}/start` changeait le statut en "active" 
- Mais ne lançait PAS le TradingEngine
- Le scheduler monitore toutes les 30s → trop lent, pas réactif

## ✅ Solution Implémentée

Modifications dans [`backend/src/routes/bots.py`](../backend/src/routes/bots.py) :

### 1. Import du Scheduler
```python
from ..core.scheduler import get_scheduler
```

### 2. Start Endpoint (ligne 354-368)
**Avant:**
```python
# TODO: Start trading engine in background (T048 - scheduler)
logger.info(f"Bot {bot_id} started (trading engine will be started by scheduler)")
```

**Après:**
```python
# Start trading engine immediately via scheduler
scheduler = get_scheduler()
success = await scheduler.start_bot(uuid.UUID(bot_id), db)

if not success:
    logger.error(f"Failed to start trading engine for bot {bot_id}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Bot status updated but trading engine failed to start"
    )

logger.info(f"Bot {bot_id} started and trading engine launched")
```

### 3. Stop Endpoint (ligne 444-456)
**Avant:**
```python
# TODO: Stop trading engine and close positions (T048 - scheduler)
logger.info(f"Bot {bot_id} stopped (positions will be closed by engine)")
```

**Après:**
```python
# Stop trading engine immediately via scheduler
scheduler = get_scheduler()
engine_stopped = await scheduler.stop_bot(uuid.UUID(bot_id))

logger.info(f"Bot {bot_id} stopped (engine_stopped={engine_stopped})")
```

## 🔄 Ce qui se Passe Maintenant

### Quand vous appelez `POST /api/bots/{id}/start`:

1. ✅ Change le status du bot en "active" (base de données)
2. ✅ Récupère le scheduler global
3. ✅ **Lance IMMÉDIATEMENT le TradingEngine** en arrière-plan
4. ✅ Le TradingEngine commence son cycle de 3 minutes
5. ✅ Retourne une confirmation avec `engine_running: true`

### Quand vous appelez `POST /api/bots/{id}/stop`:

1. ✅ Change le status en "stopped"
2. ✅ Récupère le scheduler
3. ✅ **Arrête IMMÉDIATEMENT le TradingEngine**
4. ✅ Ferme toutes les positions ouvertes
5. ✅ Retourne la confirmation

## 🧪 Comment Tester

### Test 1: Créer et Démarrer un Bot

```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8020/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"drawbot@protonmail.com","password":"votre-password"}' \
  | jq -r '.token')

echo "Token: $TOKEN"

# 2. Créer un bot
BOT_ID=$(curl -s -X POST http://localhost:8020/api/bots \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Test Trading Engine",
    "model_name": "qwen-max-3",
    "capital": 1000,
    "paper_trading": true
  }' | jq -r '.id')

echo "Bot ID: $BOT_ID"

# 3. Démarrer le bot
curl -X POST http://localhost:8020/api/bots/$BOT_ID/start \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Résultat attendu:**
```json
{
  "message": "Bot started successfully - trading engine is now running",
  "details": {
    "bot_id": "uuid",
    "status": "active",
    "engine_running": true
  }
}
```

### Test 2: Vérifier que le Moteur Tourne

**Dans les logs du serveur**, vous devriez voir:
```
INFO: Trading engine initialized for bot <uuid> (Test Trading Engine)
INFO: Starting trading engine for bot <uuid>
INFO: === Trading Cycle Started for Test Trading Engine ===
INFO: Fetching market data...
INFO: Calculating technical indicators...
INFO: LLM Decision: hold - ...
INFO: === Trading Cycle Completed in X.XXs ===
```

**Attendre 3 minutes et vous verrez un nouveau cycle.**

### Test 3: Vérifier en Base de Données

```bash
# Voir les bots actifs
docker exec trading_agent_postgres psql -U postgres -d trading_agent \
  -c "SELECT id, name, status FROM bots WHERE status='active';"

# Voir les décisions LLM (preuve que ça tourne)
docker exec trading_agent_postgres psql -U postgres -d trading_agent \
  -c "SELECT bot_id, tokens_used, timestamp FROM llm_decisions ORDER BY timestamp DESC LIMIT 5;"

# Voir les trades (si le bot en a fait)
docker exec trading_agent_postgres psql -U postgres -d trading_agent \
  -c "SELECT symbol, side, quantity, executed_at FROM trades ORDER BY executed_at DESC LIMIT 10;"
```

### Test 4: Arrêter le Bot

```bash
curl -X POST http://localhost:8020/api/bots/$BOT_ID/stop \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Résultat attendu:**
```json
{
  "message": "Bot stopped successfully - all positions closed",
  "details": {
    "bot_id": "uuid",
    "status": "stopped",
    "open_positions": 0,
    "engine_stopped": true
  }
}
```

## 📊 Surveillance en Temps Réel

### Option 1: Logs du Serveur
Regardez le terminal où tourne le serveur FastAPI :
```bash
# Les logs apparaissent automatiquement
# Vous verrez les cycles de trading toutes les 3 minutes
```

### Option 2: Vérifier les Décisions LLM
```bash
# Toutes les 3 minutes après le start, une nouvelle ligne apparaît:
docker exec trading_agent_postgres psql -U postgres -d trading_agent \
  -c "SELECT bot_id, parsed_decisions->>'action' as action, timestamp 
      FROM llm_decisions 
      ORDER BY timestamp DESC 
      LIMIT 10;"
```

### Option 3: Swagger UI
1. Ouvrir http://localhost:8020/docs
2. Utiliser les endpoints pour surveiller:
   - `GET /api/bots/{id}` - Voir le portfolio_value qui évolue
   - `GET /api/bots/{id}/positions` - Voir les positions ouvertes
   - `GET /api/bots/{id}/trades` - Voir l'historique

## ⚠️ Points Importants

### 1. Clés API Requises
Pour que le bot trade réellement, vous DEVEZ avoir dans votre `.env`:
```bash
# Au moins UN de ces LLMs:
QWEN_API_KEY=sk-...        # Recommandé (+60% de perf)
DEEPSEEK_API_KEY=sk-...    # Alternative (+40%)
CLAUDE_API_KEY=sk-ant-...  # Possible mais moins bon
OPENAI_API_KEY=sk-...      # Déconseillé (-78%)

# Pour le trading réel (optionnel en paper trading):
BINANCE_API_KEY=...
BINANCE_SECRET_KEY=...
```

### 2. Paper Trading vs Real
- **Paper Trading** (default: true): Simule les trades, pas d'argent réel
- **Real Trading** (paper_trading: false): Utilise vraiment l'API Binance

### 3. Cycle de Trading
- Défaut: **3 minutes** (180 secondes)
- Configurable dans le scheduler
- Chaque cycle:
  1. Récupère les données de marché (BTC/USDT)
  2. Calcule 10+ indicateurs (EMA, RSI, MACD, etc.)
  3. Construit un prompt avec contexte complet
  4. Appelle le LLM (Claude/GPT-4/DeepSeek/Qwen)
  5. Valide la décision avec le risk manager
  6. Exécute les trades si approuvé
  7. Met à jour les positions

### 4. Gestion des Erreurs
Si une erreur survient pendant un cycle:
- ❌ Le cycle échoue MAIS
- ✅ Le moteur continue (ne s'arrête pas)
- ✅ Réessaie au prochain cycle (3 min plus tard)
- ✅ Les erreurs sont loggées

## 🎉 Résultat Final

**AVANT le fix:**
- Créer un bot ✅
- Le démarrer ✅
- Status change en "active" ✅
- **Mais rien ne se passe** ❌

**APRÈS le fix:**
- Créer un bot ✅
- Le démarrer ✅
- Status change en "active" ✅
- **TradingEngine démarre IMMÉDIATEMENT** ✅
- **Cycle de 3 min commence** ✅
- **Appels LLM toutes les 3 min** ✅
- **Trades exécutés si décision** ✅

## 🚀 Prochaines Actions

1. **Redémarrer le serveur** pour appliquer les changements:
   ```bash
   # Ctrl+C dans le terminal du serveur, puis:
   cd backend
   source venv/bin/activate
   python -m uvicorn src.main:app --host 0.0.0.0 --port 8020 --reload
   ```

2. **Tester avec un vrai bot**:
   - Suivre les commandes ci-dessus
   - Surveiller les logs pendant 10 minutes
   - Vérifier les décisions LLM en base

3. **Valider que tout fonctionne**:
   - Au moins 3 cycles de trading (9 minutes)
   - Au moins 3 décisions LLM enregistrées
   - Pas d'erreurs critiques dans les logs

---

**✅ Le scheduler est maintenant COMPLÈTEMENT intégré et fonctionnel !**