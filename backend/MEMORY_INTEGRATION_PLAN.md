# DeepMem Integration Plan - LLM + Filter Strategy

## Architecture: Hybrid Memory System

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator (Main Loop)                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    ┌──────────────────────┐
                    │   Memory Manager     │
                    │  (Central Hub)       │
                    └──────────────────────┘
                     ↙                     ↘
        ┌─────────────────────┐   ┌─────────────────────┐
        │  LLM Decision Block  │   │  Trade Filter Service│
        │                     │   │                     │
        │ • Learn from LLM    │   │ • Adapt thresholds  │
        │   decisions         │   │   based on history  │
        │ • Store good/bad    │   │ • Dynamic win prob  │
        │   patterns          │   │   calculation       │
        │ • Adjust confidence │   │ • Smart profit min  │
        └─────────────────────┘   └─────────────────────┘
                ↓                          ↓
        ┌─────────────────────┐   ┌─────────────────────┐
        │ IndicatorDecision   │   │  Trade Execution    │
        │ Block               │   │  & Recording        │
        └─────────────────────┘   └─────────────────────┘
                                           ↓
                                    ┌─────────────┐
                                    │  Database   │
                                    │  (Trades)   │
                                    └─────────────┘
```

## Integration Points

### 1. LLM Decision Block with Memory
**File**: `src/blocks/block_llm_decision.py`

**What it learns:**
- Profitable LLM patterns by symbol
- Poor LLM decisions to avoid
- Confidence levels that work

**How it works:**
```python
class LLMDecisionBlock:
    def __init__(self, llm_client):
        self.memory = TradingMemoryService(bot_id)
        self.llm_client = llm_client

    async def get_decisions(self, market_data, portfolio_context):
        # Get LLM decisions as usual
        decisions = await self.llm_client.analyze_market(...)

        # Adjust confidence based on memory
        for symbol, decision in decisions.items():
            if MemoryManager.is_enabled():
                adjustment = await self.memory.suggest_confidence_adjustment(symbol)
                decision.confidence *= adjustment

        return decisions

    async def record_decision_outcome(self, symbol, decision, actual_pnl):
        # After trade closes, learn from it
        if actual_pnl > 0:
            await self.memory.remember_profitable_setup(
                symbol=symbol,
                entry_pattern={"llm_reasoning": decision.reasoning},
                pnl=actual_pnl,
                confidence=decision.confidence
            )
        else:
            await self.memory.remember_losing_setup(
                symbol=symbol,
                entry_pattern={"llm_reasoning": decision.reasoning},
                pnl=actual_pnl
            )
```

### 2. Trade Filter Service with Memory
**File**: `src/services/trade_filter_service.py`

**What it learns:**
- Symbol-specific profitability curves
- Dynamic minimum profit thresholds
- Win probability per symbol

**How it works:**
```python
class TradeFilterService:
    def __init__(self):
        self.memory = TradingMemoryService(bot_id)

    async def validate_trade_setup(self, symbol, entry, sl, tp, size, win_prob, conf):
        # Get historical stats from memory
        symbol_stats = await self.memory.recall_symbol_stats(symbol)

        if symbol_stats:
            # Use real data instead of defaults
            historical_win_prob = symbol_stats["win_rate"]
            # Weight new trade with history
            weighted_win_prob = (win_prob + historical_win_prob) / 2
        else:
            weighted_win_prob = win_prob

        # Apply dynamic minimum profit based on symbol history
        min_profit_usd = self._get_dynamic_min_profit(symbol, symbol_stats)

        # Validate with actual stats
        expected_profit = (weighted_win_prob * reward_usd) - ...

        if expected_profit >= min_profit_usd:
            return True, "Valid"
        else:
            return False, f"Profit below dynamic threshold: ${expected_profit}"

    def _get_dynamic_min_profit(self, symbol, stats):
        # Adjust minimum profit based on history
        if not stats:
            return 10  # Default

        win_rate = stats["win_rate"]
        avg_profit = stats["avg_profit"]

        # Higher win rate = lower min profit needed
        if win_rate > 0.65:
            return 5   # Relax minimum for proven symbols
        elif win_rate < 0.50:
            return 20  # Stricter for struggling symbols
        else:
            return 10  # Default

        return 10
```

### 3. Execution Block Integration
**File**: `src/blocks/block_execution.py`

**What it does:**
- Records trade outcome
- Tells memory if trade was profitable
- Closes feedback loop

**How it works:**
```python
class ExecutionBlock:
    async def close_position(self, position, exit_price, reason):
        # Close position as usual
        result = await self._execute_close_order(...)

        # Calculate PnL
        pnl = await self._calculate_realized_pnl(position, exit_price)

        # Record in memory for learning
        if MemoryManager.is_enabled():
            memory = TradingMemoryService(self.bot_id)

            # Get symbol stats
            trades_for_symbol = await self._get_closed_trades(position.symbol)
            win_count = len([t for t in trades_for_symbol if t.realized_pnl > 0])

            stats = {
                "win_rate": win_count / len(trades_for_symbol),
                "avg_profit": sum(t.realized_pnl for t in trades_for_symbol) / len(trades_for_symbol),
                "total_trades": len(trades_for_symbol),
            }

            await memory.remember_symbol_stats(position.symbol, stats)

        return result
```

## Data Flow

### Example: BTC Trade Cycle

```
1. MARKET DATA
   ├─ BTC price: $45,000
   ├─ RSI: 32
   └─ Trend: Bullish

2. LLM DECISION
   ├─ Signal: BUY (from LLM prompt)
   ├─ Confidence: 0.70
   └─ Memory Check:
      └─ BTC has 58% win rate historically
      └─ Adjust confidence: 0.70 * 1.08 = 0.756 ✓

3. FILTER VALIDATION
   ├─ Expected profit: $75
   ├─ Memory check:
   │  └─ Dynamic min profit for BTC (58% WR): $5
   │  └─ $75 > $5 ✓
   ├─ Win probability: 58%
   ├─ R/R ratio: 2.1x ✓
   └─ Result: APPROVED ✓

4. EXECUTION
   └─ Open position: BTC 1.0 @ $45,000

5. RESULT (hours later)
   ├─ Close: BTC @ $46,500
   ├─ PnL: +$1,500
   └─ Memory Update:
      ├─ Remember profitable setup: BTC LLM pattern
      ├─ Update BTC stats: 59% win rate (1 more win)
      └─ Next adjustment: 0.70 * 1.09 = 0.763

6. NEXT TRADE
   └─ Same symbol uses updated confidence!
```

## Implementation Checklist

- [ ] Add memory calls to `block_llm_decision.py`
- [ ] Add memory calls to `trade_filter_service.py`
- [ ] Add memory calls to `block_execution.py` (record outcomes)
- [ ] Create integration tests
- [ ] Test with both memory ON and OFF
- [ ] Monitor memory overhead (should be <5ms)
- [ ] Document memory keys and formats
- [ ] Create admin API to view/clear memory

## Enable/Disable via Config

```python
# In main bot startup
from src.core.memory.memory_manager import MemoryManager, MemoryConfig

# Easy toggle
config = MemoryConfig(
    enabled=True,  # Set to False to completely disable
    provider="deepmem",
    debug=False,   # Set to True to see memory operations
)
MemoryManager.initialize(config)

# Or at runtime
MemoryManager.switch_off()  # Disable memory
MemoryManager.switch_on()   # Re-enable memory
```

## Expected Benefits

| Aspect | Before | After |
|--------|--------|-------|
| **LLM decisions** | Fixed confidence | Adjusted by history |
| **Trade filtering** | Static thresholds | Dynamic by symbol |
| **Win rate** | 50-55% | 55-65%+ (estimated) |
| **Profit/trade** | $2-5 | $10-50 (target) |
| **False signals** | High | Reduced (learns patterns) |

## Risk Mitigation

- ✅ **No crashes** - Memory failures are graceful
- ✅ **Easy rollback** - Switch off anytime
- ✅ **Debuggable** - Full logging of memory ops
- ✅ **Monitorable** - Health checks available
- ✅ **Testable** - Works with or without DeepMem

## Next Steps

1. **Integrate memory into LLMDecisionBlock**
2. **Integrate memory into TradeFilterService**
3. **Add outcome recording in ExecutionBlock**
4. **Test with memory enabled**
5. **Monitor impact on win rate and profit**
6. **Toggle on/off based on results**

---

*Status: Ready for Implementation*
