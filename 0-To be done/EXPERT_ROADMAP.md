# 🚀 FEUILLE DE ROUTE EXPERT - INTÉGRATION LLM ENRICHI

**Objectif** : Transformer le bot pour utiliser Qwen3 Max à 100% de son potentiel  
**Durée** : 45 minutes  
**Difficulté** : Expert  

---

## ÉTAPE 1 : CRÉER `trading_memory_service.py`

**Chemin** : `/backend/services/trading_memory_service.py`

```python
"""Service de mémoire de trading pour enrichir le contexte LLM"""
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

from backend.models import Bot, Trade, Position, LLMDecision

logger = logging.getLogger(__name__)


class TradingMemoryService:
    def __init__(self, db: Session):
        self.db = db
        self._session_start = datetime.now()
        self._invocation_count = 0
        
    def increment_invocation(self):
        self._invocation_count += 1
        
    def get_session_context(self, bot: Bot) -> Dict:
        session_minutes = int((datetime.now() - self._session_start).total_seconds() / 60)
        return {
            "session_minutes": session_minutes,
            "total_invocations": self._invocation_count,
            "current_time": datetime.now().isoformat()
        }
    
    def get_portfolio_context(self, bot: Bot) -> Dict:
        return_pct = ((bot.equity - bot.initial_capital) / bot.initial_capital) * 100
        cash_pct = (bot.available_capital / bot.equity) * 100 if bot.equity > 0 else 0
        invested = bot.equity - bot.available_capital
        invested_pct = (invested / bot.equity) * 100 if bot.equity > 0 else 0
        
        return {
            "initial_capital": bot.initial_capital,
            "current_equity": bot.equity,
            "available_cash": bot.available_capital,
            "cash_pct": cash_pct,
            "invested": invested,
            "invested_pct": invested_pct,
            "return_pct": return_pct,
            "pnl": bot.equity - bot.initial_capital
        }
    
    def get_positions_context(self, bot: Bot) -> List[Dict]:
        positions_data = []
        for position in bot.positions:
            if position.status != "open":
                continue
            pnl = (position.current_price - position.entry_price) * position.size if position.side == "long" else (position.entry_price - position.current_price) * position.size
            pnl_pct = (pnl / (position.entry_price * position.size)) * 100 if position.size > 0 else 0
            
            positions_data.append({
                "symbol": position.symbol,
                "side": position.side.upper(),
                "size": position.size,
                "entry_price": position.entry_price,
                "current_price": position.current_price,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "stop_loss": position.stop_loss,
                "take_profit": position.take_profit,
                "notional_usd": position.entry_price * position.size
            })
        return positions_data
    
    def get_trades_today_context(self, bot: Bot) -> Dict:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        trades_today = self.db.query(Trade).filter(
            and_(Trade.bot_id == bot.id, Trade.timestamp >= today_start, Trade.side == "buy")
        ).count()
        
        recent_trades = self.db.query(Trade).filter(
            and_(Trade.bot_id == bot.id, Trade.exit_timestamp.isnot(None))
        ).order_by(Trade.exit_timestamp.desc()).limit(10).all()
        
        winning_trades = 0
        total_pnl = 0
        best_trade = {"pnl": 0, "symbol": None}
        worst_trade = {"pnl": 0, "symbol": None}
        
        for trade in recent_trades:
            if trade.pnl:
                total_pnl += trade.pnl
                if trade.pnl > 0:
                    winning_trades += 1
                if trade.pnl > best_trade["pnl"]:
                    best_trade = {"pnl": trade.pnl, "symbol": trade.symbol, "pnl_pct": (trade.pnl / trade.entry_value) * 100}
                if trade.pnl < worst_trade["pnl"]:
                    worst_trade = {"pnl": trade.pnl, "symbol": trade.symbol, "pnl_pct": (trade.pnl / trade.entry_value) * 100}
        
        win_rate = (winning_trades / len(recent_trades)) * 100 if recent_trades else 0
        
        return {
            "trades_today": trades_today,
            "max_trades_per_day": bot.risk_params.get("max_trades_per_day", 10),
            "win_rate": win_rate,
            "total_closed_trades": len(recent_trades),
            "winning_trades": winning_trades,
            "best_trade": best_trade if best_trade["symbol"] else None,
            "worst_trade": worst_trade if worst_trade["symbol"] else None
        }
    
    def get_sharpe_ratio(self, bot: Bot, period_days: int = 7) -> float:
        try:
            since = datetime.now() - timedelta(days=period_days)
            trades = self.db.query(Trade).filter(
                and_(Trade.bot_id == bot.id, Trade.exit_timestamp.isnot(None), Trade.exit_timestamp >= since)
            ).all()
            
            if len(trades) < 2:
                return 0.0
            
            returns = [trade.pnl / trade.entry_value for trade in trades if trade.entry_value > 0]
            if not returns:
                return 0.0
            
            import numpy as np
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            
            if std_return == 0:
                return 0.0
            
            sharpe = (mean_return / std_return) * np.sqrt(252)
            return round(sharpe, 3)
        except:
            return 0.0
    
    def get_full_context(self, bot: Bot) -> Dict:
        self.increment_invocation()
        return {
            "session": self.get_session_context(bot),
            "portfolio": self.get_portfolio_context(bot),
            "positions": self.get_positions_context(bot),
            "trades_today": self.get_trades_today_context(bot),
            "sharpe_ratio": self.get_sharpe_ratio(bot)
        }


_memory_instances: Dict[str, TradingMemoryService] = {}

def get_trading_memory(db: Session, bot_id: str) -> TradingMemoryService:
    if bot_id not in _memory_instances:
        _memory_instances[bot_id] = TradingMemoryService(db)
    return _memory_instances[bot_id]
```

**✅ Checkpoint** : Fichier créé dans `/backend/services/`

---

## ÉTAPE 2 : CRÉER `enriched_llm_prompt_service.py`

**Chemin** : `/backend/services/enriched_llm_prompt_service.py`

```python
"""Service de génération de prompts LLM enrichis"""
import json
import logging
from typing import Dict, Optional
from datetime import datetime

from backend.services.trading_memory_service import get_trading_memory
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class EnrichedLLMPromptService:
    def __init__(self, db: Session):
        self.db = db
    
    def build_enriched_prompt(self, bot, symbol: str, market_snapshot: Dict, market_regime: Dict, all_coins_data: Dict) -> str:
        memory = get_trading_memory(self.db, bot.id)
        ctx = memory.get_full_context(bot)
        
        # Session
        session = ctx["session"]
        session_text = f"""TRADING SESSION CONTEXT
Session Duration: {session['session_minutes']} minutes | Total Invocations: {session['total_invocations']}
Current Time: {session['current_time']}"""
        
        # Portfolio
        pf = ctx["portfolio"]
        portfolio_text = f"""
PORTFOLIO PERFORMANCE
Initial: ${pf['initial_capital']:,.2f} | Current: ${pf['current_equity']:,.2f} | Return: {pf['return_pct']:+.2f}%
Cash: ${pf['available_cash']:,.2f} ({pf['cash_pct']:.1f}%) | Invested: ${pf['invested']:,.2f} ({pf['invested_pct']:.1f}%)
Sharpe Ratio: {ctx['sharpe_ratio']:.3f}"""
        
        # Positions
        positions = ctx["positions"]
        if positions:
            pos_text = f"\nCURRENT POSITIONS ({len(positions)}):\n"
            for p in positions:
                pos_text += f"• {p['symbol']} {p['side']} {p['size']:.4f} @ ${p['entry_price']:,.2f} | PnL: ${p['pnl']:+,.2f} ({p['pnl_pct']:+.2f}%) | SL: ${p['stop_loss']:,.2f} TP: ${p['take_profit']:,.2f}\n"
        else:
            pos_text = "\nCURRENT POSITIONS: None"
        
        # Trades
        tr = ctx["trades_today"]
        trades_text = f"""
TRADES TODAY: {tr['trades_today']}/{tr['max_trades_per_day']} | Win Rate: {tr['win_rate']:.1f}%"""
        if tr['best_trade']:
            trades_text += f" | Best: {tr['best_trade']['symbol']} ${tr['best_trade']['pnl']:+.2f}"
        if tr['worst_trade']:
            trades_text += f" | Worst: {tr['worst_trade']['symbol']} ${tr['worst_trade']['pnl']:+.2f}"
        
        # Market state
        regime = market_regime.get("regime", "NEUTRAL")
        confidence = market_regime.get("confidence", 0.5)
        breadth = market_regime.get("breadth", {})
        market_text = f"""
MARKET STATE
Regime: {regime} ({confidence:.0%} confidence) | Breadth: {breadth.get('up', 0)} up / {breadth.get('down', 0)} down

ALL COINS SNAPSHOT:"""
        for sym, data in all_coins_data.items():
            market_text += f"\n{sym}: ${data.get('price', 0):,.2f} | RSI: {data.get('rsi', 50):.1f} | {data.get('trend', 'NEUTRAL')}"
        
        # Market data for symbol
        tech = market_snapshot.get("technical_indicators", {})
        tf_5m = tech.get("5m", {})
        tf_1h = tech.get("1h", {})
        
        symbol_text = f"""
DETAILED ANALYSIS - {symbol}
Price: ${market_snapshot.get('price', 0):,.2f} | EMA20: ${tf_5m.get('ema20', 0):,.2f} | MACD: {tf_5m.get('macd', 0):.3f}
RSI7: {tf_5m.get('rsi7', 50):.1f} | RSI14: {tf_5m.get('rsi14', 50):.1f}

1H Context: EMA20 ${tf_1h.get('ema20', 0):,.2f} vs EMA50 ${tf_1h.get('ema50', 0):,.2f} | RSI14: {tf_1h.get('rsi14', 50):.1f}
Trend 5m: {"BULL" if tf_5m.get('ema20', 0) > tf_5m.get('ema50', 0) else "BEAR"} | 1h: {"BULL" if tf_1h.get('ema20', 0) > tf_1h.get('ema50', 0) else "BEAR"}"""
        
        # Series data
        if "price_series" in market_snapshot:
            prices = market_snapshot["price_series"][-10:]
            symbol_text += f"\nPrice Series (last 10): [{', '.join([f'{p:,.2f}' for p in prices])}]"
        
        # Prompt
        prompt = f"""You are managing a ${pf['initial_capital']:,.0f} crypto portfolio with Qwen3 Max.

{session_text}
{portfolio_text}
{pos_text}
{trades_text}
{market_text}
{symbol_text}

YOUR MISSION
You are PERSONALLY RESPONSIBLE for this portfolio's performance.

Current Status: Return {pf['return_pct']:+.2f}% | Cash ${pf['available_cash']:,.0f} | Trades {tr['trades_today']}/{tr['max_trades_per_day']} | Positions {len(positions)}

DECISION RULES
ENTRY (75%+ confidence): ONLY if setup is EXCEPTIONAL + clear R/R + available cash
HOLD (50-75%): Default for performing positions, or when setup is good but not exceptional
EXIT (50%+): Stop loss approaching, profit target hit, or setup invalidated

THINK STRATEGICALLY
- "Do I REALLY need this trade NOW?"
- "Am I overtrading or adding value?"
- "What's my exit plan?"
- "How does this fit my portfolio?"

CRITICAL: Be HIGHLY SELECTIVE. Better to miss a trade than force a bad one.

RESPONSE FORMAT (JSON)
{{
  "{symbol}": {{
    "signal": "entry|hold|exit",
    "confidence": 0.75,
    "justification": "Detailed reasoning: (1) Market context, (2) Why this decision, (3) Risk plan, (4) Portfolio fit",
    "stop_loss": 112000.0,
    "profit_target": 115000.0,
    "leverage": 1,
    "risk_usd": 500.0
  }}
}}

Analyze {symbol} and decide:"""
        
        return prompt
    
    def parse_llm_response(self, response_text: str, symbol: str) -> Optional[Dict]:
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx == -1 or end_idx == 0:
                return None
            
            json_str = response_text[start_idx:end_idx]
            data = json.loads(json_str)
            
            if symbol in data:
                decision = data[symbol]
                required = ["signal", "confidence", "justification"]
                if not all(field in decision for field in required):
                    return None
                
                signal = decision["signal"].lower()
                if signal not in ["entry", "hold", "exit"]:
                    return None
                
                return decision
            return None
        except:
            return None
    
    def get_simple_decision(self, bot, symbol: str, market_snapshot: Dict, market_regime: Dict, all_coins_data: Dict) -> Dict:
        prompt = self.build_enriched_prompt(bot, symbol, market_snapshot, market_regime, all_coins_data)
        return {"prompt": prompt, "symbol": symbol, "timestamp": datetime.now().isoformat()}
```

**✅ Checkpoint** : Fichier créé dans `/backend/services/`

---

## ÉTAPE 3 : MODIFIER `trading_engine_service.py`

**Chemin** : `/backend/services/trading_engine_service.py`

### 3.1 AJOUTER LES IMPORTS (ligne ~15)

```python
from backend.services.enriched_llm_prompt_service import EnrichedLLMPromptService
from backend.services.trading_memory_service import get_trading_memory
```

### 3.2 INITIALISER LES SERVICES (dans `__init__`, après `self.llm_service = ...`)

```python
self.enriched_prompt_service = EnrichedLLMPromptService(db)
self.trading_memory = get_trading_memory(db, bot.id)
```

### 3.3 AJOUTER LES MÉTHODES HELPER (à la fin de la classe)

```python
def _get_all_coins_quick_snapshot(self) -> Dict[str, Dict]:
    all_coins = {}
    for symbol in ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]:
        try:
            ticker = self.market_service.get_ticker(symbol)
            if ticker:
                candles_5m = self.market_service.get_candles(symbol, "5m", limit=50)
                if len(candles_5m) >= 20:
                    closes = [c["close"] for c in candles_5m]
                    rsi = self._calculate_rsi(closes, 14)
                    ema20 = self._calculate_ema(closes, 20)
                    trend = "BULLISH" if closes[-1] > ema20 else "BEARISH"
                    all_coins[symbol] = {"price": ticker["last"], "rsi": rsi, "trend": trend}
        except:
            pass
    return all_coins

def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def _calculate_ema(self, prices: List[float], period: int) -> float:
    if len(prices) < period:
        return sum(prices) / len(prices)
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema
```

### 3.4 REMPLACER L'APPEL LLM (chercher `llm_decision = await self.llm_service.get_decision`)

**LOCALISER CE BLOC** :
```python
# Get LLM decision
llm_decision = await self.llm_service.get_decision(
    symbol=symbol,
    market_data=market_snapshot,
    position=current_position
)
```

**REMPLACER PAR** :
```python
# Build enriched prompt
prompt_data = self.enriched_prompt_service.get_simple_decision(
    bot=bot,
    symbol=symbol,
    market_snapshot=market_snapshot,
    market_regime=market_regime_analysis,
    all_coins_data=self._get_all_coins_quick_snapshot()
)

# Get LLM decision with enriched context
llm_response = await self.llm_client.generate(
    prompt=prompt_data["prompt"],
    model=bot.llm_model
)

# Parse structured response
parsed_decision = self.enriched_prompt_service.parse_llm_response(
    llm_response.get("text", ""),
    symbol
)

if not parsed_decision:
    logger.warning(f"Failed to parse LLM decision for {symbol}, using fallback")
    llm_decision = {"action": "hold", "confidence": 0.5, "reasoning": "Parse error"}
else:
    llm_decision = {
        "action": parsed_decision["signal"],
        "confidence": parsed_decision["confidence"],
        "reasoning": parsed_decision["justification"],
        "stop_loss": parsed_decision.get("stop_loss"),
        "take_profit": parsed_decision.get("profit_target")
    }
```

### 3.5 ENRICHIR MARKET SNAPSHOT (où `market_snapshot` est créé)

**AJOUTER** :
```python
# Enrichir avec séries temporelles
candles_5m = self.market_service.get_candles(symbol, "5m", limit=100)
if len(candles_5m) >= 20:
    market_snapshot["price_series"] = [c["close"] for c in candles_5m[-10:]]
    closes = [c["close"] for c in candles_5m]
    ema_series = []
    for i in range(len(closes) - 10, len(closes)):
        ema = self._calculate_ema(closes[:i+1], 20)
        ema_series.append(ema)
    market_snapshot["ema_series"] = ema_series
    rsi_series = []
    for i in range(len(closes) - 10, len(closes)):
        rsi = self._calculate_rsi(closes[:i+1], 7)
        rsi_series.append(rsi)
    market_snapshot["rsi_series"] = rsi_series
```

**✅ Checkpoint** : Trading engine modifié

---

## ÉTAPE 4 : TESTER

### 4.1 TEST IMPORTS
```bash
cd /Users/cube/Documents/00-code/nof1
python3 -c "from backend.services.trading_memory_service import TradingMemoryService; print('✅ Memory OK')"
python3 -c "from backend.services.enriched_llm_prompt_service import EnrichedLLMPromptService; print('✅ Prompt OK')"
python3 -m py_compile backend/services/trading_engine_service.py && echo "✅ Engine OK"
```

### 4.2 RESET ET LANCER
```bash
./scripts/reset.sh
./start.sh
```

### 4.3 OBSERVER LES LOGS
```bash
tail -f backend.log | grep -E "(Session Duration|Decision|Confidence)"
```

**Validation** :
- ✅ "Session Duration: X minutes"
- ✅ Confidences 75%+
- ✅ Raisonnements 200+ caractères
- ✅ Moins de trades (1-3/heure)

---

## ÉTAPE 5 : VALIDATION FINALE

**Checklist 30 min** :
- [ ] Bot démarre sans erreur
- [ ] Logs montrent contexte enrichi
- [ ] Décisions LLM sont HOLD majoritairement
- [ ] Confidences 75-85%
- [ ] Max 2-3 trades en 30 min
- [ ] Raisonnements mentionnent portfolio

**Si ✅** : C'est bon, laisse tourner 24h  
**Si ❌** : Check logs d'erreur, rollback si nécessaire

---

## ROLLBACK (si problème)

```bash
cd /Users/cube/Documents/00-code/nof1/backend/services
cp trading_engine_service.py.backup trading_engine_service.py
rm trading_memory_service.py enriched_llm_prompt_service.py
./start.sh
```

---

## MÉTRIQUES CIBLES

| Avant | Après |
|-------|-------|
| 10 trades/10min | 1-3 trades/h |
| Conf 65% | Conf 75-85% |
| Reasoning 50 chars | Reasoning 200+ chars |
| HOLD 20% | HOLD 70%+ |

**Résultat** : Bot pense comme portfolio manager, pas comme signal follower.

---

*Feuille de route expert v1.0 - Code production-ready*
