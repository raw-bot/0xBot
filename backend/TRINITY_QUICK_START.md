# Trinity Framework - Quick Start Guide

**Framework**: Trinity Indicator Confluence Scoring
**Status**: ✅ Ready for Live Trading
**Last Updated**: 2026-01-16

---

## 🚀 Start Bot with Trinity Mode

### Method 1: Default (Trinity Mode)
```bash
python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8000

# Bot starts with Trinity mode enabled automatically
# Look for this in logs:
# 📈 Using Trinity indicator framework (confluence scoring)
```

### Method 2: Explicit Trinity Mode
```python
from src.blocks.orchestrator import TradingOrchestrator

orchestrator = TradingOrchestrator(
    bot_id=bot_uuid,
    decision_mode="trinity"  # ← Trinity mode
)
```

### Method 3: Switch at Runtime
```python
# Switch from any mode to Trinity
orchestrator.switch_decision_mode("trinity")

# Verify current mode
print(orchestrator.get_decision_mode())  # Output: "trinity"
```

---

## 📊 What Trinity Does

### Entry Signals (When to BUY)
Trinity looks for **4 out of 5** favorable conditions:

| # | Condition | Meaning | Threshold |
|---|-----------|---------|-----------|
| 1 | Regime Filter | Price above long-term average | Price > 200 SMA |
| 2 | Trend Strength | Strong uptrend confirmed | ADX > 25 |
| 3 | Price Bounce | Pullback and recovery | Price > 20 EMA |
| 4 | Momentum | Not yet overbought | RSI < 40 |
| 5 | Volume | Backing from buyers | Volume > Vol MA |

**If 4-5/5 met** → **ENTER TRADE**

### Position Sizing (How Much to Risk)
```
4/5 signals + 80% confidence → Buy 3% of capital
5/5 signals + 100% confidence → Buy 3% of capital
3/5 signals + 60% confidence → Buy 2% of capital
< 3/5 signals → No trade (wait for better setup)
```

### Exit Signals (When to SELL)
Trinity exits when ANY of these occur:

| Exit Type | Trigger | Meaning |
|-----------|---------|---------|
| **Technical Exit** | Supertrend turns red | Trailing stop hit |
| **Structural Exit** | Price < 200 SMA | Regime has changed |
| **Profit-Taking** | RSI > 75 | Too hot (overbought) |

---

## 🧪 Test Trinity Before Live Trading

### Run Test Suite
```bash
python3 test_trinity_signals.py

# Should output:
# ✅ All Trinity Signal Tests Passed!
```

### Check Specific Symbol
```python
import asyncio
from decimal import Decimal
from src.blocks.block_trinity_decision import TrinityDecisionBlock
from src.blocks.block_market_data import MarketSnapshot

async def check_signal():
    trinity = TrinityDecisionBlock()

    # Create market data with Trinity indicators
    market_data = {
        "BTC/USDT": MarketSnapshot(
            symbol="BTC/USDT",
            price=Decimal("42000"),
            confluence_score=85.0,
            signals={
                "regime_filter": True,
                "trend_strength": True,
                "price_bounced": True,
                "oversold": False,
                "volume_confirmed": True,
            }
        )
    }

    signals = await trinity.get_decisions(market_data, {})
    for symbol, signal in signals.items():
        print(f"Signal: {symbol} @ {signal.confidence:.0%}")

asyncio.run(check_signal())
```

---

## 📈 Monitor Trinity Trading

### What to Look For

#### Good Sign ✅
```
[TRINITY] BTC/USDT: BUY signal | Confluence: 85/100 | Signals: 4/5 | Confidence: 80%
```
- Confluence score > 75/100
- 4-5 signals met
- Confidence 60-100%

#### Warning ⚠️
```
[TRINITY] XRP/USDT: BUY signal | Confluence: 50/100 | Signals: 3/5 | Confidence: 60%
```
- Lower confluence (50-75)
- Only 3 signals met
- Smaller position (2% instead of 3%)

#### Skip 🚫
```
[TRINITY] ADA/USDT: No entry (confluence 25/100) | Signals: 1/5
```
- Confluence < 50/100
- Less than 3 signals
- No trade generated (correct behavior!)

---

## 🎯 Performance Metrics to Track

### After 10 Trades
Check these metrics:

| Metric | Good | Okay | Bad |
|--------|------|------|-----|
| Win Rate | > 50% | 40-50% | < 40% |
| Avg Confluence | > 80 | 70-80 | < 70 |
| Avg Confidence | > 70% | 60-70% | < 60% |
| Trades/Day | 2-5 | 1-2 | 0 (too few) |

### Confluence Score Distribution
```
Winning trades average confluence: ___
Losing trades average confluence: ___

If winning > losing by 20+ points → Trinity is working ✅
```

---

## 🔧 Tune Trinity (Optional)

### Adjust Confidence Thresholds
Edit `src/blocks/block_trinity_decision.py`:

```python
# Current settings (adjust if needed):
CONFIDENCE_STRONG = 0.8      # 4-5/5 signals
CONFIDENCE_MODERATE = 0.6    # 3/5 signals
CONFIDENCE_WEAK = 0.4        # <3/5 signals
```

### Adjust Position Sizing
```python
SIZE_HIGH = 0.03             # 3% for high confidence
SIZE_MEDIUM = 0.02           # 2% for medium
SIZE_LOW = 0.01              # 1% for low (if enabled)
```

### Adjust Indicator Thresholds
```python
RSI_OVERSOLD = 40            # Lower = more entry signals
ADX_MIN = 25                 # Lower = more entry signals
RSI_OVERBOUGHT = 75          # Lower = earlier exits
```

---

## 🔄 Switch Between Modes

### Trinity ↔ LLM
```python
# Switch to LLM (adaptive AI mode)
orchestrator.switch_decision_mode("llm")

# Switch back to Trinity (indicator mode)
orchestrator.switch_decision_mode("trinity")

# Check current mode
mode = orchestrator.get_decision_mode()
print(f"Currently using: {mode}")
```

### Why Switch?
- **Trinity**: More reliable signals, fewer trades, higher quality
- **LLM**: More adaptive, learns from experience, more trades
- **Hybrid**: Use Trinity for entry, LLM for exit adjustments

---

## ❌ Troubleshooting

### Problem: No Trinity Signals Generated
**Check**:
1. Is bot in Trinity mode? → Check logs for "📈 Using Trinity"
2. Do symbols have enough data? → Need 250 candles (200 for SMA_200)
3. Are indicators calculating? → MarketSnapshot should have confluence_score > 0

### Problem: Too Many False Signals
**Solution**:
1. Increase ADX minimum threshold (e.g., 30 instead of 25)
2. Increase RSI oversold threshold (e.g., 35 instead of 40)
3. Wait for 5/5 signals only (skip 3-4/5)

### Problem: Too Few Signals
**Solution**:
1. Decrease ADX minimum (e.g., 20 instead of 25)
2. Decrease RSI oversold (e.g., 45 instead of 40)
3. Accept 3/5 signals as valid entries

---

## 📚 Learn More

### Core Files
- `src/blocks/block_indicators.py` - Indicator calculations
- `src/blocks/block_trinity_decision.py` - Signal generation
- `src/blocks/orchestrator.py` - Mode switching

### Documentation
- `TRINITY_INTEGRATION.md` - Full architecture
- `TRINITY_TECHNICAL_GUIDE.md` - Implementation details
- `TRINITY_TEST_RESULTS.md` - Test validation

### Test Examples
- `test_trinity_signals.py` - Unit tests and examples

---

## 🎯 Expected Behavior

### Normal Trading Cycle
```
1. Fetch market data (every 3 minutes)
   ↓
2. Calculate Trinity indicators
   ↓
3. Check each symbol:
   - BTC/USDT: 5/5 signals → ENTER (3%, 100% confidence)
   - ETH/USDT: 2/5 signals → WAIT (not enough confluence)
   - SOL/USDT: 3/5 signals → ENTER (2%, 60% confidence)
   ↓
4. Check existing positions for exits
   ↓
5. Next cycle in 3 minutes...
```

### Sample Log Output
```
[TRINITY] BTC/USDT: BUY signal | Confluence: 100/100 | Signals: 5/5 | Confidence: 100%
LONG BTC/USDT @ $42000.00
Position recorded: size=30000 USDT, 3% of capital

[Trinity] ETH/USDT: Entry conditions not met (2/5 signals) - waiting for more confirmation

[TRINITY] SOL/USDT: BUY signal | Confluence: 60/100 | Signals: 3/5 | Confidence: 60%
LONG SOL/USDT @ $140.00
Position recorded: size=300 SOL, 2% of capital

[Position Update] BTC/USDT: current price $42100 | P&L: +$3000
[Trinity] SOL/USDT: Exit triggered - Supertrend turned red
CLOSE SOL/USDT @ $142.50 | Profit: +$750
```

---

## ✅ Checklist Before Going Live

- [ ] Bot starts with Trinity mode enabled
- [ ] Test suite passes (4/4 cases)
- [ ] Market data fetches successfully
- [ ] Indicators calculate (confluence_score visible)
- [ ] Signals generate for strong setups
- [ ] Position sizing matches confidence
- [ ] Exit conditions trigger correctly
- [ ] Can switch between modes without restart
- [ ] Database persists trades correctly
- [ ] Logging shows Trinity decisions

---

## 🚀 Deploy!

Once checklist complete:

```bash
# Start bot with Trinity mode
python3 -m uvicorn src.main:app --port 8000 --log-level info

# Monitor first trading session
# Expected: 2-5 trades in first hour
# Look for: Confluence scores 60-100, Confidence 60-100%

# After 10 trades, assess:
# Win rate should be > 50%
# Average confluence should be > 70
```

---

**Status**: 🟢 Ready for Live Trading
**Framework**: Trinity Indicator Confluence Scoring
**Confidence**: ✅ Fully Tested and Validated

🎯 **Deploy and let Trinity signals do the trading!**
