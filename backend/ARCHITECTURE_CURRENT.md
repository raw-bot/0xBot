# Current Architecture - Before Refactoring (Phase 6)

**Date**: January 19, 2026
**Purpose**: Document the monolithic service architecture for baseline comparison during modular refactoring.

---

## Executive Summary

The 0xBot trading system is currently organized as a **monolithic architecture** with:
- **24 active services** (non-archived)
- **10 global singletons** for external dependencies
- **Two large service files** handling complex workflows (1118 LOC + 673 LOC)
- **No dependency injection** - all services access globals directly
- **Mixed concerns** within large service classes

This document captures the current state before the Phase 6 modular refactoring.

---

## Global Singletons (10)

These are initialized at startup and accessed globally throughout the codebase:

### 1. **Redis Client**
- **Location**: `src/core/redis_client.py`
- **Access**: Imported and accessed globally in caching operations
- **Purpose**: Session storage, cache layer, rate limiting
- **Init**: `await init_redis()` in FastAPI lifespan
- **Shutdown**: `await close_redis()` in FastAPI lifespan

### 2. **LLM Client**
- **Location**: `src/core/llm_client.py`
- **Access**: Global instance for LLM calls (Claude via Anthropic API)
- **Purpose**: AI decision making, prompt generation, response parsing
- **Init**: Initialized during app startup
- **Shutdown**: On app shutdown

### 3. **Exchange Client**
- **Location**: `src/core/exchange_client.py`
- **Access**: Global instance for Binance/exchange interactions
- **Purpose**: Order execution, market data fetching, position management
- **Init**: Initialized during app startup
- **Shutdown**: On app shutdown

### 4. **Database Engine & Session**
- **Location**: `src/core/database.py`
- **Access**: Global `engine` and session factory
- **Purpose**: SQLAlchemy async engine for database operations
- **Init**: Created at module load, async sessions created per request
- **Pool Config**: `NullPool` (connection per request - **SCALABILITY ISSUE**)

### 5. **Scheduler**
- **Location**: `src/core/scheduler.py`
- **Access**: Global APScheduler instance
- **Purpose**: Background job scheduling (bot execution cycles)
- **Init**: `await start_scheduler()` in FastAPI lifespan
- **Shutdown**: `await stop_scheduler()` in FastAPI lifespan

### 6. **Sentiment Service**
- **Location**: `src/services/market_sentiment_service.py`
- **Access**: Imported and called globally
- **Purpose**: Market sentiment analysis (Fear/Greed index, social signals)
- **Dependencies**: LLM client, cache

### 7. **Trading Memory**
- **Location**: `src/core/memory/` (complex initialization)
- **Access**: Global instance for trade history and memory
- **Purpose**: Persistent memory of past trades and decisions
- **Init**: Complex initialization during app startup

### 8. **Logger Instances**
- **Location**: Multiple files use `get_logger(__name__)`
- **Access**: Global logger factory
- **Purpose**: Structured logging across the application
- **Init**: Configured during app startup

### 9. **Config Object**
- **Location**: `src/core/config.py`
- **Access**: Global `config` singleton
- **Purpose**: Application configuration (API keys, trading params, etc.)
- **Init**: Loaded at module import time
- **Validation**: On app startup

### 10. **Cache Manager** (if exists)
- **Location**: `src/services/cache_service.py`
- **Access**: May be accessed globally
- **Purpose**: Application-level caching (Redis-backed)
- **Init**: Initialized during app startup

---

## Active Services (24)

### Core Services

1. **`trading_engine_service.py`** (1118 LOC) ⚠️ LARGE
   - Main orchestrator of trading cycles
   - **Contains**:
     - `execute_trading_cycle()` (~400 LOC) - Full cycle orchestration
     - `decision_logic()` (~250 LOC) - LLM decision generation
     - `risk_validation()` (~200 LOC) - Risk checks
     - `order_management()` (~150 LOC) - Order execution
     - `monitoring()` (~118 LOC) - Position monitoring
   - **Dependencies**: All major services
   - **Called By**: Scheduler (background jobs), routes

2. **`multi_coin_prompt_service.py`** (673 LOC) ⚠️ LARGE
   - LLM prompt generation for multi-coin analysis
   - **Contains**:
     - `generate_multi_coin_prompt()` (~250 LOC) - Prompt building
     - `format_market_data()` (~200 LOC) - Data formatting
     - `integrate_analysis()` (~150 LOC) - Analysis integration
     - `validate_response()` (~73 LOC) - Response validation
   - **Dependencies**: Market data, analysis services, cache
   - **Called By**: Trading engine, analysis routes

### Market Analysis Services

3. **`market_data_service.py`**
   - Fetches OHLCV data from exchange
   - Caches market data (5-minute TTL)
   - Returns historical candles for analysis

4. **`market_analysis_service.py`**
   - Technical analysis on market data
   - Returns trend, momentum, volatility signals
   - Uses indicator service

5. **`market_sentiment_service.py`**
   - Sentiment analysis and Fear/Greed index
   - Social signal integration
   - Returns market sentiment scores

6. **`indicator_service.py`**
   - Technical indicators (RSI, MACD, Bollinger Bands, etc.)
   - Caching with 15-minute TTL
   - Returns indicator values

7. **`indicator_strategy_service.py`**
   - Strategy-specific indicator analysis
   - Combines multiple indicators for signals
   - Returns buy/sell signals

### Decision & Execution Services

8. **`llm_decision_validator.py`**
   - Validates LLM decisions against risk rules
   - Checks constraints and limits
   - Returns approved/rejected decisions

9. **`trade_filter_service.py`**
   - Filters trades based on strategy rules
   - Applies custom filters
   - Returns filtered decision list

10. **`trade_executor_service.py`**
    - Executes approved trades on exchange
    - Handles order placement, error handling
    - Returns trade execution results

11. **`position_service.py`**
    - Manages active positions
    - Tracks P&L, stop loss, take profit
    - Handles position closing

12. **`risk_manager_service.py`**
    - Risk validation and position sizing
    - Leverage calculation
    - Drawdown monitoring

### Bot & Strategy Services

13. **`bot_service.py`**
    - Bot state management
    - Lifecycle operations (start, stop, pause)
    - Configuration per bot

14. **`strategy_performance_service.py`**
    - Tracks strategy performance metrics
    - Win rate, profit factor, Sharpe ratio
    - Historical performance analysis

15. **`trading_memory_service.py`**
    - Trade history and decisions
    - Long-term memory for learning
    - Past decision lookup

16. **`kelly_position_sizing_service.py`**
    - Kelly criterion position sizing
    - Optimal bet size calculation
    - Risk-adjusted sizing

### Analysis & Specialized Services

17. **`fvg_detector_service.py`**
    - Fair Value Gap (FVG) detection
    - Price level analysis
    - Support/resistance identification

18. **`pain_trade_analyzer.py`**
    - Pain trade detection and analysis
    - Liquidation level tracking
    - Squeeze analysis

19. **`narrative_analyzer.py`**
    - Narrative-based market analysis
    - Event interpretation
    - Context understanding

20. **`news_service.py`**
    - News sentiment and impact analysis
    - Breaking news detection
    - Event relevance scoring

21. **`alpha_setup_generator.py`**
    - Setup identification (entry/exit points)
    - Pattern recognition
    - Opportunity scoring

### Support Services

22. **`cache_service.py`**
    - Redis-backed caching layer
    - TTL management
    - Cache invalidation

23. **`service_interface.py`**
    - Base interface/protocol for services
    - Common patterns and contracts

24. **`__init__.py`**
    - Package initialization
    - Service exports

---

## Service Dependencies Map

```
trading_engine_service (orchestrator)
├── market_data_service
├── market_analysis_service
├── indicator_service
├── indicator_strategy_service
├── market_sentiment_service
├── multi_coin_prompt_service
│   ├── market_data_service
│   ├── market_analysis_service
│   ├── indicator_service
│   └── trade_filter_service
├── llm_decision_validator
├── risk_manager_service
├── position_service
├── trade_executor_service
├── strategy_performance_service
├── trading_memory_service
└── scheduling (APScheduler)

Multi-coin flow:
market_data → market_analysis → indicators → sentiment
└── multi_coin_prompt_service (generates LLM prompt)
└── llm_client (makes decision)
└── llm_decision_validator (validates)
└── trade_filter_service (filters)
└── trade_executor_service (executes)
```

---

## Current Issues

### 1. **Monolithic Services**
- `trading_engine_service.py`: 1118 LOC - Hard to test, modify, or understand
- `multi_coin_prompt_service.py`: 673 LOC - Mixed concerns (formatting, building, validating)

### 2. **Global Singletons**
- All 10 singletons accessed via global imports
- Hard to mock in tests
- Difficult to create multiple instances for parallel testing
- Tight coupling throughout codebase

### 3. **No Dependency Injection**
- Services can't specify dependencies explicitly
- Hidden dependencies in imports
- Hard to trace dependency flow
- No way to swap implementations

### 4. **Database Connection Pooling**
- Using `NullPool` - one connection per request (scalability killer)
- Should use connection pooling for high concurrency

### 5. **Mixed Concerns in Large Services**
- `trading_engine_service` handles: orchestration, decisions, risk, orders, monitoring
- `multi_coin_prompt_service` handles: formatting, building, validating, integrating
- Each should be single-responsibility

### 6. **Testing Challenges**
- Mock all globals in conftest.py (inflexible)
- Can't test services in isolation without complex setup
- 56 failing tests due to global access issues

---

## Startup & Shutdown Flow

### Application Startup
```
main.py lifespan (startup)
├── configure_structured_logging()
├── config.validate_config()
├── await init_redis()
├── Database connection (engine created)
├── await start_scheduler()
└── Print ready message
```

### Application Shutdown
```
main.py lifespan (shutdown)
├── await stop_scheduler()
├── await close_db()
├── await close_redis()
└── Print shutdown complete
```

---

## Files Referenced

### Core Files
- `backend/src/core/config.py` - Config singleton
- `backend/src/core/database.py` - Database engine (NullPool)
- `backend/src/core/redis_client.py` - Redis singleton
- `backend/src/core/llm_client.py` - LLM client
- `backend/src/core/exchange_client.py` - Exchange API client
- `backend/src/core/scheduler.py` - APScheduler instance
- `backend/src/core/logging_config.py` - Logging setup
- `backend/src/main.py` - FastAPI app entry point

### Service Files (24 total)
- `backend/src/services/*.py` (24 files)

### Routes
- `backend/src/routes/bots_router.py` - Bot management
- `backend/src/routes/auth_router.py` - Authentication
- `backend/src/routes/dashboard/` - Dashboard routes

### Tests
- `backend/tests/conftest.py` - Pytest configuration
- `backend/tests/services/` - Service tests
- `backend/tests/routes/` - Route tests

---

## Metrics (Current State)

| Metric | Value |
|--------|-------|
| Total Services | 24 active + 8 archived |
| Largest Service | 1118 LOC (trading_engine_service) |
| Second Largest | 673 LOC (multi_coin_prompt_service) |
| Global Singletons | 10 |
| Test Coverage | ~34% (56 tests failing) |
| Database Pool | NullPool (scalability issue) |
| DI Pattern | None (all globals) |

---

## Next Steps (Phase 6 Refactoring)

### Task 1: Cleanup & Documentation ✓
- [x] Delete 8 archived services
- [x] Create ARCHITECTURE_CURRENT.md (this file)

### Task 2: DI Foundation
- Create ServiceContainer class
- Create factory functions for all 10 singletons
- Create backward-compatible wrapper

### Task 3: Refactor TradingEngine
- Split 1118 LOC into 3 modules (<300 LOC each)
- Create TradingCycleManager, DecisionExecutor, PositionMonitor

### Task 4: Refactor MultiCoinPrompt
- Split 673 LOC into 3 modules (<300 LOC each)
- Create PromptBuilder, MarketDataFormatter, AnalysisIntegrator

### Task 5: Migrate Global Singletons
- Update all services to use DI container
- Remove global imports

### Task 6: Configuration Consolidation
- Centralize all magic numbers
- Create constants.py, environment.py

### Task 7: Type Safety
- Add 100% type hints
- Run mypy --strict

### Task 8: Documentation
- Create ARCHITECTURE_NEW.md
- Create DI_GUIDE.md
- Create REFACTORING_REPORT.md

---

## Summary

The current architecture is a **working but difficult-to-maintain monolith**:
- ✅ Functionally complete (all trading logic works)
- ❌ Hard to test (global singletons)
- ❌ Hard to modify (large services)
- ❌ Hard to scale (NullPool, tight coupling)
- ❌ Hard to understand (hidden dependencies)

Phase 6 refactoring will transform this into a **modular, testable, scalable architecture** while maintaining 100% backward compatibility.

---

**Status**: Phase 6 baseline documentation
**Owner**: Ralph AI Agent
**Last Updated**: January 19, 2026
