# Dependency Graph - Current Architecture

**Date**: January 19, 2026
**Purpose**: Visual representation of service dependencies and data flow.

---

## Global Singletons at Module Level

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GLOBAL SINGLETONS                             │
│                     (Initialized at startup)                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  config (TradingConfig)          - App configuration & env vars      │
│  engine (AsyncEngine)            - SQLAlchemy database engine        │
│  redis_client (Redis)            - Redis connection (cache/sessions) │
│  llm_client (LLMClient)          - Claude LLM API client             │
│  exchange_client (ExchangeClient)- Binance API client               │
│  scheduler (APScheduler)         - Background job scheduler          │
│  trading_memory (TradeMemory)    - Persistent trade history         │
│  logger (Logger factory)         - Structured logging                │
│  cache_manager (CacheManager)    - Redis cache layer                │
│  db_session_factory (Session)    - SQLAlchemy session factory        │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Service Dependency Tree

### Tier 1: External Dependencies (No internal dependencies)

```
market_data_service
├── Input: Symbol list, timeframe
├── Depends On: exchange_client (global), cache_service
└── Output: OHLCV data, timestamps

indicator_service
├── Input: Price data (OHLCV)
├── Depends On: Redis cache (caching)
└── Output: Indicator values (RSI, MACD, BB, etc.)

market_sentiment_service
├── Input: Symbols, time window
├── Depends On: News API, social feeds, llm_client (global)
└── Output: Sentiment scores

cache_service
├── Input: Cache keys, TTL
├── Depends On: redis_client (global)
└── Output: Cached values

trading_memory_service
├── Input: Trade history
├── Depends On: Database, config
└── Output: Past trades, decisions
```

### Tier 2: Analysis Services (Depend on Tier 1)

```
market_analysis_service
├── Input: OHLCV data
├── Depends On: indicator_service
└── Output: Trend, momentum, volatility

indicator_strategy_service
├── Input: OHLCV, sentiment
├── Depends On: indicator_service, market_analysis_service
└── Output: Combined signals

fvg_detector_service
├── Input: Price data
├── Depends On: market_data_service
└── Output: FVG levels, support/resistance

pain_trade_analyzer
├── Input: Market data, positions
├── Depends On: market_data_service, position_service
└── Output: Pain trade analysis

narrative_analyzer
├── Input: Market context, news
├── Depends On: news_service, market_sentiment_service
└── Output: Narrative interpretation

news_service
├── Input: Symbols, time window
├── Depends On: Cache, API clients
└── Output: News sentiment, events

alpha_setup_generator
├── Input: Market data, patterns
├── Depends On: indicator_service, market_data_service
└── Output: Trade setups, opportunities
```

### Tier 3: Decision & Execution Services (Depend on Tier 1-2)

```
llm_decision_validator
├── Input: LLM decision
├── Depends On: config, risk_manager_service
└── Output: Validated decision

trade_filter_service
├── Input: Decision list
├── Depends On: config, strategy settings
└── Output: Filtered decisions

risk_manager_service
├── Input: Trade decision, current positions
├── Depends On: config, position_service, kelly_position_sizing_service
└── Output: Position size, risk approval

kelly_position_sizing_service
├── Input: Win rate, profit factor, account size
├── Depends On: config, trading_memory_service
└── Output: Optimal position size

position_service
├── Input: Active positions
├── Depends On: database, config
└── Output: Position data, P&L

trade_executor_service
├── Input: Approved trades
├── Depends On: exchange_client (global), position_service
└── Output: Execution results
```

### Tier 4: Prompt & Multi-Coin Services (Depend on Tier 1-3)

```
multi_coin_prompt_service
├── Input: Symbols, market conditions
├── Depends On:
│   ├── market_data_service
│   ├── market_analysis_service
│   ├── indicator_service
│   ├── indicator_strategy_service
│   ├── market_sentiment_service
│   ├── fvg_detector_service
│   ├── pain_trade_analyzer
│   ├── narrative_analyzer
│   ├── news_service
│   ├── trade_filter_service
│   ├── cache_service
│   └── llm_client (global)
├── Produces: LLM prompt (text)
└── Output: Structured prompt for LLM
```

### Tier 5: Orchestration Services (Depend on all tiers)

```
trading_engine_service (ORCHESTRATOR)
├── Input: Triggered by scheduler
├── Depends On: (all 24 services + all globals)
│   ├── market_data_service
│   ├── market_analysis_service
│   ├── indicator_service
│   ├── indicator_strategy_service
│   ├── market_sentiment_service
│   ├── multi_coin_prompt_service
│   ├── llm_client (global)
│   ├── llm_decision_validator
│   ├── trade_filter_service
│   ├── risk_manager_service
│   ├── kelly_position_sizing_service
│   ├── position_service
│   ├── trade_executor_service
│   ├── trading_memory_service
│   ├── strategy_performance_service
│   ├── scheduler (global)
│   └── database (global)
├── Orchestrates: Full trading cycle
└── Output: Execution results, state updates
```

### Tier 6: Support Services

```
strategy_performance_service
├── Input: Trades, positions
├── Depends On: database, trading_memory_service
└── Output: Performance metrics

bot_service
├── Input: Bot configuration
├── Depends On: database, config
└── Output: Bot state, lifecycle

service_interface
├── Input: (Base interface)
├── Depends On: None
└── Output: Protocol/base class
```

---

## Data Flow Diagram

### Trading Cycle Execution (High Level)

```
┌──────────────────────────────────────────────────────────────────────┐
│ Scheduler Triggers Trading Cycle (Every 5 minutes)                  │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 1: FETCH MARKET DATA                                           │
│ ├─ market_data_service.fetch(symbols)                               │
│ └─ Returns: OHLCV data (cached, 5-min TTL)                          │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 2: ANALYZE MARKET                                              │
│ ├─ indicator_service.calculate(prices)                              │
│ ├─ market_analysis_service.analyze(prices)                          │
│ ├─ market_sentiment_service.get_sentiment()                         │
│ ├─ fvg_detector_service.detect(prices)                              │
│ ├─ pain_trade_analyzer.analyze(positions)                           │
│ ├─ narrative_analyzer.analyze(context)                              │
│ ├─ news_service.get_news()                                          │
│ └─ Returns: Complete market analysis                                │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 3: GENERATE LLM PROMPT                                         │
│ └─ multi_coin_prompt_service.generate_prompt(analysis)              │
│    Returns: Structured prompt text                                  │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 4: GET LLM DECISION                                            │
│ └─ llm_client.make_decision(prompt)                                 │
│    Returns: Trading decisions (buy/sell/hold per symbol)            │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 5: VALIDATE & FILTER DECISIONS                                 │
│ ├─ llm_decision_validator.validate(decisions)                       │
│ ├─ trade_filter_service.filter(decisions)                           │
│ └─ Returns: Filtered, validated decisions                           │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 6: CALCULATE POSITION SIZE & RISK                              │
│ ├─ risk_manager_service.calculate_size(decision)                    │
│ ├─ kelly_position_sizing_service.calculate(decision)                │
│ └─ Returns: Position size, margin, risk metrics                     │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 7: EXECUTE TRADES                                              │
│ ├─ trade_executor_service.execute(approved_trades)                  │
│ ├─ exchange_client.place_orders(orders)                             │
│ └─ Returns: Execution results, order IDs                            │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 8: UPDATE STATE & MONITORING                                   │
│ ├─ position_service.update_positions(executed)                      │
│ ├─ trading_memory_service.log_decision(decision)                    │
│ ├─ strategy_performance_service.update_metrics(trades)              │
│ └─ Database: Store all execution data                               │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ▼
                   ✅ CYCLE COMPLETE
```

---

## Dependency Count by Service

```
Trading Engine Service
├── Direct Dependencies: 15+ services
└── Indirect Dependencies: 24 services + 10 globals
    ⚠️ Over-coupled (depends on too much)

Multi-Coin Prompt Service
├── Direct Dependencies: 10+ services
└── Indirect Dependencies: 20+ services
    ⚠️ High coupling

Trade Executor Service
├── Direct Dependencies: 3 services
└── Indirect Dependencies: 5 services
    ✅ Reasonable coupling

Market Data Service
├── Direct Dependencies: 2 (exchange, cache)
└── Indirect Dependencies: 2
    ✅ Low coupling

Indicator Service
├── Direct Dependencies: 1 (cache)
└── Indirect Dependencies: 1
    ✅ Low coupling
```

---

## Import Bottlenecks

### Most Imported Services

1. **market_data_service** - Imported by: 7 services
2. **indicator_service** - Imported by: 6 services
3. **market_analysis_service** - Imported by: 5 services
4. **cache_service** - Imported by: 8 services
5. **config** (global) - Imported by: All 24 services

### Most Imported Globals

1. **llm_client** - Used by: 8 services
2. **exchange_client** - Used by: 5 services
3. **config** - Used by: 24 services ⚠️
4. **redis_client** - Used by: 6 services
5. **database engine** - Used by: 10 services

---

## Circular Dependency Check

### Potential Cycles (to avoid during refactoring)

None currently detected because:
- Services are organized in tiers (1-6)
- Higher tiers depend on lower tiers only
- No backward dependencies

However, refactoring should maintain this layering.

---

## Global Access Patterns

### Pattern 1: Direct Global Import
```python
from src.core.config import config
from src.core.exchange_client import exchange_client
```
**Found in**: All services
**Problem**: Can't mock, can't test in isolation

### Pattern 2: Function Import
```python
from src.core.logging_config import get_logger
logger = get_logger(__name__)
```
**Found in**: Logging across services
**Problem**: Static logger, hard to control in tests

### Pattern 3: Database Session
```python
from src.core.database import get_session
```
**Found in**: Repository/service files
**Problem**: Hidden dependency in function calls

---

## Refactoring Target

### After Phase 6 Modular Refactoring

```
┌──────────────────────────────────────────────────────────────────────┐
│ SERVICE CONTAINER (Dependency Injection)                            │
│ ├─ register_factory("config", create_config)                        │
│ ├─ register_factory("database", create_database)                    │
│ ├─ register_factory("redis", create_redis)                          │
│ └─ ... (all 10 singletons)                                          │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
           ┌───────────┴──────────────┐
           │                          │
           ▼                          ▼
    ┌──────────────┐         ┌──────────────┐
    │ TradingEngine│         │ MultiCoinPr. │
    │ (3 modules)  │         │ (3 modules)  │
    └──────┬───────┘         └──────┬───────┘
           │                        │
           └────────┬───────────────┘
                    │
         (Injected dependencies)
```

---

## Summary

- **Current State**: Monolithic with global singletons
- **Issue**: Over-coupling, hard to test, hard to modify
- **Target State**: Modular with explicit dependency injection
- **Risk**: Maintainable without circular dependencies (tiers well-organized)
- **Effort**: Refactor 2 large services + create DI container

---

**Status**: Current architecture baseline
**Owner**: Ralph AI Agent
**Last Updated**: January 19, 2026
