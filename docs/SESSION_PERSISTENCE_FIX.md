# SQLAlchemy Session Persistence Fix

## Problem
Error: `Instance '<Bot at 0x113292350>' is not persistent within this Session`

This error occurred in the trading engine because the bot instance became detached from its database session, causing issues when trying to access or refresh it.

## Root Cause
The trading engine was storing `self.bot` as an instance variable and trying to refresh it with `await self.db.refresh(self.bot)` after sleeping. However, the bot instance could have been:
1. Created in a different session
2. Detached from the session after operations
3. Associated with a closed/expired session

## Solution
Refactored the trading engine to use session-independent patterns:

### 1. Store Bot ID Instead of Instance
```python
# Before:
self.bot = bot

# After:
self.bot_id = bot.id
self.bot = bot  # Keep for backward compatibility but don't rely on it
```

### 2. Reload Bot Status Per Cycle
```python
async def _get_bot_status(self) -> BotStatus:
    """Get the current bot status from database."""
    async with AsyncSessionLocal() as fresh_db:
        query = select(Bot).where(Bot.id == self.bot_id)
        result = await fresh_db.execute(query)
        bot = result.scalar_one()
        return bot.status
```

### 3. Return Bot Instance with Portfolio State
```python
async def _get_portfolio_state(self) -> tuple[dict, Bot]:
    """Get current portfolio state and bot."""
    async with AsyncSessionLocal() as fresh_db:
        # Reload bot from database
        query = select(Bot).where(Bot.id == self.bot_id)
        result = await fresh_db.execute(query)
        bot = result.scalar_one()
        
        # ... calculate portfolio ...
        
        return portfolio, bot  # Return both
```

### 4. Use Local Bot Instance in Trading Cycle
```python
async def _trading_cycle(self) -> None:
    # Get fresh bot instance each cycle
    portfolio_state, current_bot = await self._get_portfolio_state()
    
    # Use current_bot instead of self.bot
    logger.info(f"🤖 {current_bot.name}")
    # ... rest of cycle ...
```

### 5. Pass Bot to Methods That Need It
```python
async def _handle_entry_decision(
    self, 
    decision: dict, 
    current_price: Decimal, 
    portfolio_state: dict, 
    current_bot: Bot  # Accept fresh bot instance
) -> None:
    # Use current_bot instead of self.bot
    is_valid, message = RiskManagerService.validate_complete_decision(
        bot=current_bot,
        # ... rest of params ...
    )
```

## Key Changes
1. **start()**: Uses `_get_bot_status()` instead of `refresh()`
2. **stop()**: Creates fresh session to update bot status
3. **_get_portfolio_state()**: Returns tuple of (portfolio, bot)
4. **_trading_cycle()**: Uses returned bot instance locally
5. **_handle_entry_decision()**: Accepts bot as parameter
6. **_save_llm_decision()**: Uses `self.bot_id` instead of `self.bot.id`
7. **_get_trades_today_count()**: Uses `self.bot_id`
8. **_update_position_prices()**: Uses `self.bot_id`

## Benefits
- ✅ No more session persistence errors
- ✅ Each operation uses fresh, properly-attached instances
- ✅ Better separation of concerns
- ✅ More reliable across async operations
- ✅ Handles session expiration gracefully

## Testing
After this fix, the trading engine should:
1. Start without session errors
2. Run multiple cycles successfully
3. Handle bot status checks reliably
4. Update portfolio state correctly
5. Execute trades without persistence issues

## Files Modified
- [`backend/src/services/trading_engine_service.py`](../backend/src/services/trading_engine_service.py)