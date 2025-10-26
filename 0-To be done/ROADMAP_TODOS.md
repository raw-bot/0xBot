# 🔧 ROADMAP - AJOUT STATS TRADES COMPLÈTES

**Objectif** : Ajouter win rate, best/worst trade, et Sharpe ratio réels  
**Durée** : 15 minutes  
**Fichiers** : 3  

---

## FICHIER 1 : `trading_memory_service.py`

### Modification 1.1 : `get_trades_today_context()` (ligne ~100-110)

**REMPLACER** :
```python
def get_trades_today_context(self, bot: Bot, open_positions: List[Position]) -> Dict:
    return {
        "trades_today": 0,
        "max_trades_per_day": bot.risk_params.get("max_trades_per_day", 10),
        "win_rate": 0.0,
        "total_closed_trades": 0,
        "winning_trades": 0,
        "best_trade": None,
        "worst_trade": None
    }
```

**PAR** :
```python
def get_trades_today_context(self, bot: Bot, open_positions: List[Position], all_trades: List) -> Dict:
    """Context des trades du jour avec stats complètes"""
    from datetime import datetime
    
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Filtrer trades d'aujourd'hui (buy = entrées)
    today_trades = [t for t in all_trades if t.timestamp and t.timestamp >= today_start and t.side == "buy"]
    trades_today_count = len(today_trades)
    
    # Filtrer trades fermés récents pour stats
    closed_trades = [t for t in all_trades if t.exit_timestamp is not None]
    recent_closed = sorted(closed_trades, key=lambda x: x.exit_timestamp, reverse=True)[:20]
    
    if not recent_closed:
        return {
            "trades_today": trades_today_count,
            "max_trades_per_day": bot.risk_params.get("max_trades_per_day", 10),
            "win_rate": 0.0,
            "total_closed_trades": 0,
            "winning_trades": 0,
            "best_trade": None,
            "worst_trade": None
        }
    
    # Stats
    winning_trades = sum(1 for t in recent_closed if t.pnl and t.pnl > 0)
    win_rate = (winning_trades / len(recent_closed)) * 100 if recent_closed else 0
    
    # Best/Worst
    trades_with_pnl = [t for t in recent_closed if t.pnl is not None and t.entry_value and t.entry_value > 0]
    
    best_trade = None
    worst_trade = None
    
    if trades_with_pnl:
        best = max(trades_with_pnl, key=lambda x: x.pnl)
        worst = min(trades_with_pnl, key=lambda x: x.pnl)
        
        best_trade = {
            "pnl": best.pnl,
            "symbol": best.symbol,
            "pnl_pct": (best.pnl / best.entry_value) * 100
        }
        
        worst_trade = {
            "pnl": worst.pnl,
            "symbol": worst.symbol,
            "pnl_pct": (worst.pnl / worst.entry_value) * 100
        }
    
    return {
        "trades_today": trades_today_count,
        "max_trades_per_day": bot.risk_params.get("max_trades_per_day", 10),
        "win_rate": win_rate,
        "total_closed_trades": len(recent_closed),
        "winning_trades": winning_trades,
        "best_trade": best_trade,
        "worst_trade": worst_trade
    }
```

### Modification 1.2 : `get_sharpe_ratio()` (ligne ~120-130)

**REMPLACER** :
```python
def get_sharpe_ratio(self, bot: Bot, period_days: int = 7) -> float:
    return 0.0
```

**PAR** :
```python
def get_sharpe_ratio(self, all_trades: List, period_days: int = 7) -> float:
    """Calculer Sharpe depuis trades passés en paramètre"""
    try:
        from datetime import datetime, timedelta
        
        since = datetime.now() - timedelta(days=period_days)
        
        # Filtrer trades de la période
        period_trades = [
            t for t in all_trades 
            if t.exit_timestamp and t.exit_timestamp >= since 
            and t.pnl is not None and t.entry_value and t.entry_value > 0
        ]
        
        if len(period_trades) < 2:
            return 0.0
        
        # Returns
        returns = [t.pnl / t.entry_value for t in period_trades]
        
        import numpy as np
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # Annualiser
        sharpe = (mean_return / std_return) * np.sqrt(252)
        return round(sharpe, 3)
    except:
        return 0.0
```

### Modification 1.3 : `get_full_context()` (ligne ~140)

**REMPLACER** :
```python
def get_full_context(self, bot: Bot, open_positions: List[Position]) -> Dict:
    self.increment_invocation()
    return {
        "session": self.get_session_context(bot),
        "portfolio": self.get_portfolio_context(bot, open_positions),
        "positions": self.get_positions_context(open_positions),
        "trades_today": self.get_trades_today_context(bot, open_positions),
        "sharpe_ratio": self.get_sharpe_ratio(bot)
    }
```

**PAR** :
```python
def get_full_context(self, bot: Bot, open_positions: List[Position], all_trades: List) -> Dict:
    self.increment_invocation()
    return {
        "session": self.get_session_context(bot),
        "portfolio": self.get_portfolio_context(bot, open_positions),
        "positions": self.get_positions_context(open_positions),
        "trades_today": self.get_trades_today_context(bot, open_positions, all_trades),
        "sharpe_ratio": self.get_sharpe_ratio(all_trades)
    }
```

**✅ Checkpoint 1** : Fichier compilé sans erreur

---

## FICHIER 2 : `enriched_llm_prompt_service.py`

### Modification 2.1 : `build_enriched_prompt()` signature (ligne ~20)

**CHERCHER** :
```python
def build_enriched_prompt(
    self, 
    bot, 
    symbol: str, 
    market_snapshot: Dict, 
    market_regime: Dict, 
    all_coins_data: Dict,
    bot_positions: List
) -> str:
```

**REMPLACER PAR** :
```python
def build_enriched_prompt(
    self, 
    bot, 
    symbol: str, 
    market_snapshot: Dict, 
    market_regime: Dict, 
    all_coins_data: Dict,
    bot_positions: List,
    bot_trades: List
) -> str:
```

### Modification 2.2 : Appel `get_full_context()` (ligne ~35)

**CHERCHER** :
```python
memory = get_trading_memory(self.db, bot.id)
ctx = memory.get_full_context(bot, bot_positions)
```

**REMPLACER PAR** :
```python
memory = get_trading_memory(self.db, bot.id)
ctx = memory.get_full_context(bot, bot_positions, bot_trades)
```

### Modification 2.3 : `get_simple_decision()` signature (ligne ~250)

**CHERCHER** :
```python
def get_simple_decision(
    self, 
    bot, 
    symbol: str, 
    market_snapshot: Dict, 
    market_regime: Dict, 
    all_coins_data: Dict,
    bot_positions: List
) -> Dict:
```

**REMPLACER PAR** :
```python
def get_simple_decision(
    self, 
    bot, 
    symbol: str, 
    market_snapshot: Dict, 
    market_regime: Dict, 
    all_coins_data: Dict,
    bot_positions: List,
    bot_trades: List
) -> Dict:
```

### Modification 2.4 : Appel `build_enriched_prompt()` (ligne ~260)

**CHERCHER** :
```python
prompt = self.build_enriched_prompt(
    bot, symbol, market_snapshot, market_regime, all_coins_data, bot_positions
)
```

**REMPLACER PAR** :
```python
prompt = self.build_enriched_prompt(
    bot, symbol, market_snapshot, market_regime, all_coins_data, bot_positions, bot_trades
)
```

**✅ Checkpoint 2** : Fichier compilé sans erreur

---

## FICHIER 3 : `trading_engine_service.py`

### Modification 3.1 : Charger les trades (ligne ~250, AVANT l'appel prompt_data)

**CHERCHER** :
```python
# Build enriched prompt
prompt_data = self.enriched_prompt_service.get_simple_decision(
```

**AJOUTER JUSTE AVANT** :
```python
# Load bot trades for stats
from sqlalchemy import select
from backend.models import Trade

trades_query = select(Trade).where(Trade.bot_id == bot.id).order_by(Trade.timestamp.desc()).limit(50)
trades_result = await self.db.execute(trades_query)
all_trades = list(trades_result.scalars().all())
```

### Modification 3.2 : Passer les trades (ligne ~260)

**CHERCHER** :
```python
prompt_data = self.enriched_prompt_service.get_simple_decision(
    bot=bot,
    symbol=symbol,
    market_snapshot=market_snapshot,
    market_regime=market_regime_analysis,
    all_coins_data=self._get_all_coins_quick_snapshot(),
    bot_positions=all_positions
)
```

**REMPLACER PAR** :
```python
prompt_data = self.enriched_prompt_service.get_simple_decision(
    bot=bot,
    symbol=symbol,
    market_snapshot=market_snapshot,
    market_regime=market_regime_analysis,
    all_coins_data=self._get_all_coins_quick_snapshot(),
    bot_positions=all_positions,
    bot_trades=all_trades
)
```

**✅ Checkpoint 3** : Fichier compilé sans erreur

---

## TESTS DE VALIDATION

```bash
cd /Users/cube/Documents/00-code/0xBot

# Test 1: Compilation
python3 -m py_compile backend/src/services/trading_memory_service.py
python3 -m py_compile backend/src/services/enriched_llm_prompt_service.py
python3 -m py_compile backend/src/services/trading_engine_service.py

# Test 2: Import
python3 -c "from backend.src.services.trading_memory_service import TradingMemoryService; print('✅ Memory OK')"
python3 -c "from backend.src.services.enriched_llm_prompt_service import EnrichedLLMPromptService; print('✅ Prompt OK')"

# Test 3: Démarrage
./stop.sh && ./start.sh

# Test 4: Observer les logs (après 2-3 minutes)
tail -f backend.log | grep -E "(Win Rate|Sharpe|Best:|Worst:)"
```

**Attendu dans les logs** :
```
TRADES TODAY: 3/10 | Win Rate: 66.7% | Best: BTC/USDT $+45.23 | Worst: ETH/USDT $-12.50
Sharpe Ratio: 1.234
```

---

## RÉSUMÉ DES MODIFICATIONS

| Fichier | Modifications | Lignes |
|---------|---------------|--------|
| `trading_memory_service.py` | 3 méthodes | ~80 lignes |
| `enriched_llm_prompt_service.py` | 4 signatures | ~8 lignes |
| `trading_engine_service.py` | 1 query + 1 param | ~10 lignes |

**Total** : ~100 lignes ajoutées/modifiées

---

## ROLLBACK (si problème)

```bash
cd /Users/cube/Documents/00-code/0xBot/backend/src/services
cp trading_engine_service.py.backup trading_engine_service.py
git checkout trading_memory_service.py enriched_llm_prompt_service.py
./start.sh
```

---

## RÉSULTAT FINAL

✅ Win rate réel (20 derniers trades)  
✅ Best/Worst trade avec $ et %  
✅ Sharpe ratio 7 jours  
✅ Trades today comptés précisément  
✅ Contexte LLM enrichi au maximum  

**Le bot devient un vrai portfolio manager avec métriques complètes.**

---

*Roadmap TODOs v1.0 - 15 minutes*
