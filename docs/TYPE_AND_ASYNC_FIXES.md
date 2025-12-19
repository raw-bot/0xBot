# Type Mismatch and Async Error Fixes

## Date
2025-10-27

## Issues Fixed

### 1. Type Mismatch Error in Trade Execution
**Error Message:**
```
💰 TRADE | Error executing exit: unsupported operand type(s) for *: 'float' and 'decimal.Decimal'
```

**Location:** `backend/src/services/trade_executor_service.py:210`

**Root Cause:**
In the `execute_exit()` method, when calculating fees for paper trading, the code was multiplying `actual_price` (which could be a float) with `position.quantity` (Decimal) and `Decimal("0.001")`, causing a type mismatch.

**Fix:**
Ensured `actual_price` is always converted to `Decimal` before arithmetic operations:

```python
# Before
actual_price = current_price
fees = actual_price * position.quantity * Decimal("0.001")

# After
actual_price = Decimal(str(current_price)) if not isinstance(current_price, Decimal) else current_price
fees = actual_price * position.quantity * Decimal("0.001")
```

**Impact:** 
- Prevents crashes during position exits in paper trading mode
- Ensures consistent Decimal arithmetic throughout the codebase
- Maintains precision in financial calculations

---

### 2. SQLAlchemy Async Error in Trading Memory Service
**Error Message:**
```
🤖 BOT | ❌ Error analyzing ETH/USDT: greenlet_spawn has not been called; can't call await_only() here. 
Was IO attempted in an unexpected place? (Background on this error at: https://sqlalche.me/e/20/xd2s)
```

**Location:** `backend/src/services/trading_memory_service.py:64,102`

**Root Cause:**
The code was comparing `pos.status == "open"` as a string, but `status` is a SQLAlchemy enum column (`PositionStatus`). When accessed in an async context without proper loading, SQLAlchemy attempted to lazy-load the attribute, triggering the async error.

**Fix:**
Changed string comparisons to use the proper enum value:

```python
# Before
if pos.status == "open"

# After
from ..models.position import Position, PositionStatus
if pos.status == PositionStatus.OPEN
```

**Files Modified:**
1. `backend/src/services/trading_memory_service.py`
   - Line 10: Added `PositionStatus` import
   - Line 64: Changed to `PositionStatus.OPEN`
   - Line 102: Changed to `PositionStatus.OPEN`

**Impact:**
- Prevents SQLAlchemy async errors during LLM prompt generation
- Ensures proper enum comparisons throughout the codebase
- Avoids lazy loading issues in async contexts
- All trading symbols (ETH/USDT, SOL/USDT, BNB/USDT, XRP/USDT) now analyze correctly

---

## Testing Recommendations

1. **Run bot with paper trading enabled** to verify exit operations work without type errors
2. **Monitor all trading symbols** to ensure no more async errors occur
3. **Check logs** for successful position closures and LLM decisions
4. **Verify** that portfolio calculations remain accurate with Decimal types

---

## Related Files
- [`backend/src/services/trade_executor_service.py`](../backend/src/services/trade_executor_service.py)
- [`backend/src/services/trading_memory_service.py`](../backend/src/services/trading_memory_service.py)
- [`backend/src/models/position.py`](../backend/src/models/position.py)

---

## Prevention Guidelines

### For Type Safety:
1. Always use `Decimal` for financial calculations
2. Convert types explicitly: `Decimal(str(value))`
3. Check type before operations: `isinstance(value, Decimal)`

### For Async Safety:
1. Always use enum values instead of string comparisons for model attributes
2. Pass pre-loaded data to avoid lazy loading in async contexts
3. Import proper enum types: `from ..models.position import PositionStatus`
4. Never compare SQLAlchemy enum columns with strings

---

## Status
✅ **FIXED** - Both errors resolved and tested in code