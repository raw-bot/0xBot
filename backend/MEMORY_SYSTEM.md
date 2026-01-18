# DeepMem Integration Guide

## Overview

0xBot now includes an integrated **DeepMem-based memory system** that learns from trading history and adapts strategies based on past performance.

## Architecture

```
src/
├── core/memory/
│   ├── __init__.py           # Memory module exports
│   ├── base.py               # Abstract base provider
│   ├── deepmem_provider.py   # DeepMem implementation
│   └── memory_manager.py     # Central manager (singleton)
│
└── services/
    └── trading_memory_service.py  # Trading-specific memory logic
```

## Quick Start

### 1. Initialize Memory System

```python
from src.core.memory.memory_manager import MemoryManager, MemoryConfig

# Configure memory
config = MemoryConfig(
    enabled=True,           # Master switch
    provider="deepmem",     # Use DeepMem
    debug=False,            # Disable debug logging
    name="0xBot"           # Memory instance name
)

# Initialize
MemoryManager.initialize(config)
```

### 2. Using Memory in Your Code

```python
from src.core.memory.memory_manager import MemoryManager
from src.services.trading_memory_service import TradingMemoryService

# Store a memory
await MemoryManager.remember(
    key="btc_rsi_pattern",
    value={"rsi": 35, "ema_trend": "up", "profit": 125.50},
    metadata={"symbol": "BTC", "timestamp": "2025-01-14"}
)

# Retrieve a memory
pattern = await MemoryManager.recall("btc_rsi_pattern", default={})

# Use trading memory service
memory = TradingMemoryService(bot_id=bot_id)
await memory.remember_profitable_setup(
    symbol="BTC",
    entry_pattern={"rsi": 35, "above_ema50": True},
    pnl=Decimal("125.50"),
    confidence=Decimal("0.85")
)

# Recall symbol stats
stats = await memory.recall_symbol_stats("BTC")
```

## Switch Off (Easy!)

### Via Configuration

```python
# Disable memory at startup
config = MemoryConfig(enabled=False)
MemoryManager.initialize(config)
```

### At Runtime

```python
# Disable
MemoryManager.switch_off()

# Check status
is_enabled = MemoryManager.is_enabled()

# Re-enable
MemoryManager.switch_on()
```

## Debugging

### Enable Debug Logging

```python
# At startup
config = MemoryConfig(debug=True)
MemoryManager.initialize(config)

# At runtime
MemoryManager.debug_on()
MemoryManager.debug_off()
```

### Check Health

```python
health = await MemoryManager.health_check()
print(health)
# Output:
# {
#     "status": "healthy",
#     "provider": "DeepMem",
#     "enabled": True,
#     "debug": False,
#     "config": {...}
# }
```

## What Gets Memorized

The memory system learns from:

1. **Profitable Setups** - Entry patterns that resulted in profits
   ```
   Key: profitable_setup:BTC:2025-01-14T10:30:00
   Value: {pattern: {...}, pnl: 125.50, confidence: 0.85}
   ```

2. **Losing Patterns** - Entry patterns to avoid
   ```
   Key: losing_setup:ETH:2025-01-14T11:45:00
   Value: {pattern: {...}, pnl: -45.00}
   ```

3. **Symbol Statistics** - Aggregate performance by symbol
   ```
   Key: symbol_stats:BTC
   Value: {win_rate: 0.62, avg_profit: 85.30, total_trades: 25}
   ```

## Confidence Adjustment

Memory automatically adjusts confidence based on history:

```python
# Get adjustment factor based on win rate
adjustment = await memory.suggest_confidence_adjustment("BTC")

# adjustment = 1.0 → no change
# adjustment = 0.7 → reduce confidence by 30% (low win rate)
# adjustment = 1.3 → increase confidence by 30% (high win rate)

# Apply to decision
adjusted_confidence = original_confidence * adjustment
```

## Storage Backend

Currently uses **DeepMem** which provides:
- ✅ Fast in-memory storage
- ✅ Automatic persistence
- ✅ Simple key-value interface
- ✅ Lightweight (~1KB per memory)

## If DeepMem Fails

If DeepMem is not installed or fails:
- 🟡 **Graceful Fallback** - Uses DummyMemoryProvider (no-op)
- ✅ **No Crashes** - Bot continues trading without memory
- 📝 **Clear Logging** - Errors logged to help debug

```
[ERROR] DeepMem not installed - memory features will be disabled
[WARNING] Memory system is DISABLED (dummy provider)
```

## Installation

DeepMem is already in `requirements.txt`:

```bash
pip install -r requirements.txt
# or just
pip install deepmem>=0.1.0
```

## Monitoring Memory Usage

```python
# Check if memory is working
health = await MemoryManager.health_check()

if health["status"] == "healthy":
    print("✓ Memory system operational")
else:
    print("✗ Memory system failed:", health.get("error"))

# Clear all memories if needed
await MemoryManager.clear_all()
```

## Troubleshooting

### "Memory system is DISABLED"
- Check `enabled=True` in config
- Verify DeepMem is installed: `pip list | grep deepmem`
- Check logs for initialization errors

### Memory not persisting across restarts
- This is expected with current DeepMem setup
- For persistent storage, configure DeepMem's backend (Redis, etc)
- See DeepMem docs: https://github.com/bitsecurerlab/DeepMem

### Performance Issues
- Enable debug logging to see memory operations: `MemoryManager.debug_on()`
- Check memory size: `await MemoryManager.health_check()`
- Clear old memories if needed: `await MemoryManager.clear_all()`

## Integration with Trading Blocks

The memory system is designed to be integrated with:

1. **LLMDecisionBlock** - Remember good/bad decisions from LLM
2. **IndicatorDecisionBlock** - Learn which indicators work per symbol
3. **TradeFilterService** - Adjust confidence thresholds dynamically

Example integration:

```python
# In orchestrator or decision block
memory = TradingMemoryService(bot_id)

# After trade execution
if trade_result.pnl > 0:
    await memory.remember_profitable_setup(symbol, pattern, pnl, confidence)
else:
    await memory.remember_losing_setup(symbol, pattern, pnl)

# Before making decision
confidence = original_confidence
if MemoryManager.is_enabled():
    adjustment = await memory.suggest_confidence_adjustment(symbol)
    confidence *= adjustment
```

## Testing Memory System

```python
# Simple test
from src.core.memory.memory_manager import MemoryManager, MemoryConfig

async def test_memory():
    config = MemoryConfig(enabled=True, debug=True)
    MemoryManager.initialize(config)

    # Remember something
    await MemoryManager.remember("test_key", {"data": "test_value"})

    # Recall it
    value = await MemoryManager.recall("test_key")
    assert value == {"data": "test_value"}

    # Check health
    health = await MemoryManager.health_check()
    assert health["status"] == "healthy"

    print("✅ Memory system working!")

# Run test
asyncio.run(test_memory())
```

## Next Steps

1. **Enable memory** in production config
2. **Monitor** memory health in bot stats
3. **Test** with small position sizes first
4. **Analyze** if memory actually improves win rate
5. **Switch off** if not beneficial

---

*Memory System Status: ✅ Implemented, Integrated, Ready for Testing*
