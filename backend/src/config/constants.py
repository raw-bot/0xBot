"""
Configuration constants for 0xBot trading system.

This module centralizes all magic numbers and configuration parameters
to improve maintainability and allow easy tuning of system behavior.

Categories:
- TRADING_CONFIG: Position sizing, leverage, stop loss, take profit
- TIMING_CONFIG: Intervals, timeouts, cache TTLs
- LIMITS_CONFIG: Risk limits, drawdown, max trades, exposure
- VALIDATION_CONFIG: Confidence thresholds, indicator parameters
- API_CONFIG: Rate limiting, fees, pricing
- DATABASE_CONFIG: Connection pool, timeouts
- INDICATOR_CONFIG: Technical indicator parameters
"""

from typing import Dict, Any

# ============================================================================
# TRADING CONFIG - Position Sizing & Leverage
# ============================================================================

TRADING_CONFIG: Dict[str, Any] = {
    # Position sizing (as % of capital)
    "DEFAULT_POSITION_SIZE_PCT": 0.35,  # 35% of capital per position
    "DEFAULT_BOT_MAX_POSITION_PCT": 0.08,  # 8% harmonized max (tighter)
    "DEFAULT_LEVERAGE": 5.0,  # Max leverage for long positions
    "SHORT_POSITION_SIZE_PCT": 0.25,  # 25% of capital for shorts
    "SHORT_MAX_LEVERAGE": 3.0,  # Max leverage for short positions

    # Stop loss & take profit defaults
    "DEFAULT_STOP_LOSS_PCT": 0.035,  # 3.5% stop loss
    "DEFAULT_TAKE_PROFIT_PCT": 0.08,  # 8% take profit
    "INDICATOR_STOP_LOSS_PCT": 0.025,  # 2.5% for indicator strategy
    "INDICATOR_TAKE_PROFIT_PCT": 0.05,  # 5% for indicator strategy

    # Strategy-specific position sizing
    "INDICATOR_BASE_SIZE_PCT": 0.10,  # 10% base for indicator strategy
    "INDICATOR_MAX_SIZE_PCT": 0.25,  # 25% max for indicator strategy
    "INDICATOR_DEFAULT_SIZE_PCT": 0.10,  # Default for indicator decisions
    "RISK_BLOCK_MAX_POSITION_PCT": 0.25,  # Max in RiskBlock
    "LLM_MAX_SIZE_PCT": 0.25,  # Max in LLM decision block

    # Kelly criterion sizing
    "KELLY_FRACTION": 0.25,  # 25% of Kelly optimal
    "KELLY_MIN_SIZE_PCT": 0.02,  # 2% minimum
    "KELLY_MAX_SIZE_PCT": 0.25,  # 25% maximum

    # Trading fees
    "PAPER_TRADING_FEE_PCT": 0.0005,  # 0.05% for paper trading
    "ROUND_TRIP_FEE_PCT": 0.0010,  # 0.10% total (0.05% entry + 0.05% exit)
}

# ============================================================================
# TIMING CONFIG - Intervals, Timeouts, TTLs
# ============================================================================

TIMING_CONFIG: Dict[str, Any] = {
    # News and data fetch intervals (in seconds)
    "NEWS_FETCH_INTERVAL_SECONDS": 300,  # 5 minutes
    "CYCLE_INTERVAL_SECONDS": 300,  # Default cycle: 5 minutes
    "SCHEDULER_CYCLE_INTERVAL_SECONDS": 180,  # Scheduler cycle: 3 minutes

    # Monitoring intervals
    "BOT_MONITOR_CHECK_INTERVAL_SECONDS": 30,  # Check every 30s
    "MONITOR_RETRY_INTERVAL_SECONDS": 30,  # Retry after 30s

    # Orchestrator intervals
    "ORCHESTRATOR_RETRY_DELAY_SECONDS": 30,  # Retry delay: 30 seconds
    "ORCHESTRATOR_CYCLE_INTERVAL_SECONDS": 180,  # Cycle: 3 minutes

    # API timeouts
    "API_TIMEOUT_SECONDS": 5,  # General API timeout: 5 seconds
    "NEWS_SERVICE_TIMEOUT_SECONDS": 5,  # News API timeout: 5 seconds

    # Cache TTLs
    "MARKET_SENTIMENT_CACHE_TTL": 300,  # 5 minutes

    # Database
    "DB_CONNECTION_TIMEOUT_SECONDS": 10,  # Connection timeout: 10s
    "DB_COMMAND_TIMEOUT_SECONDS": 5,  # Command timeout: 5s
    "DB_POOL_RECYCLE_SECONDS": 3600,  # Recycle connections after 1 hour

    # News freshness thresholds (in minutes)
    "FRESH_NEWS_THRESHOLD_MINUTES": 60,  # < 1 hour
    "RECENT_NEWS_THRESHOLD_MINUTES": 120,  # < 2 hours
    "STALE_NEWS_THRESHOLD_MINUTES": 360,  # > 6 hours
}

# ============================================================================
# LIMITS CONFIG - Risk Limits & Constraints
# ============================================================================

LIMITS_CONFIG: Dict[str, Any] = {
    # Drawdown & daily loss limits
    "BOT_MAX_DRAWDOWN_PCT": 0.15,  # 15% max drawdown before stopping
    "MAX_MARGIN_EXPOSURE_PCT": 0.95,  # 95% max total exposure

    # Trade frequency limits
    "BOT_MAX_TRADES_PER_DAY": 20,  # Max 20 trades per day
    "TARGET_TRADES_PER_DAY": 6,  # Target 6 trades per day
    "MAX_NEW_ENTRIES_PER_CYCLE": 2,  # Max 2 new entries per cycle

    # Risk metrics
    "MIN_SL_DISTANCE_PCT": 0.015,  # 1.5% minimum SL distance
    "MIN_RISK_REWARD_RATIO": 2.0,  # Minimum 2:1 R:R
    "MIN_NET_PROFIT_USD": 5.0,  # $5 minimum profit
    "MIN_POSITION_SIZE_USD": 100,  # $100 minimum position
    "MIN_POSITION_VALUE_USD": 50,  # $50 minimum in RiskBlock

    # Risk block specific
    "RISK_BLOCK_MAX_EXPOSURE_PCT": 0.95,  # 95% max exposure
    "RISK_BLOCK_MIN_R_R": 1.3,  # 1.3:1 minimum R:R in RiskBlock

    # Safety limits
    "SAFETY_MAX_SL_PCT": 0.25,  # 25% max stop loss (safety check)
    "MAX_LEVERAGE_VALIDATION": 10.0,  # 10x max leverage validation

    # Daily circuit breaker
    "MAX_DAILY_LOSS_USD": -100,  # Stop if lost $100 in a day

    # Drawdown warning
    "DRAWDOWN_WARNING_THRESHOLD": 0.80,  # Warn at 80% of max
    "TRADE_FREQUENCY_WARNING_THRESHOLD": 0.80,  # Warn at 80% of daily max
}

# ============================================================================
# VALIDATION CONFIG - Confidence & Decision Thresholds
# ============================================================================

VALIDATION_CONFIG: Dict[str, Any] = {
    # Entry/exit confidence thresholds
    "MIN_CONFIDENCE_ENTRY": 0.70,  # 70% min confidence for entry
    "MIN_CONFIDENCE_EXIT_EARLY": 0.60,  # 60% for early exit
    "MIN_CONFIDENCE_EXIT_NORMAL": 0.70,  # 70% for normal exit
    "SHORT_MIN_CONFIDENCE": 0.65,  # 65% for short-specific

    # Default confidence values
    "DEFAULT_MISSING_CONFIDENCE": 0.50,  # 50% for missing responses
    "DEFAULT_HOLD_CONFIDENCE": 0.6,  # 60% for HOLD decisions

    # Trade filter confidence
    "TRADE_FILTER_MIN_CONFIDENCE": 0.65,  # 65% minimum
    "MIN_WIN_PROBABILITY": 0.55,  # 55% minimum win probability
    "TRADE_FILTER_RR_RATIO_MIN": 1.5,  # 1.5:1 minimum R:R for filter

    # Trade profitability thresholds
    "MIN_PROFIT_PER_TRADE_PCT": 1.0,  # 1% minimum profit
    "MIN_PROFIT_PER_TRADE_USD": 10,  # $10 minimum profit

    # LLM validation fallback
    "FALLBACK_TP_PCT": 0.10,  # 10% fallback take profit

    # Kelly criterion confidence thresholds
    "KELLY_ADJUSTMENT_MIN": 0.50,  # 0.5x minimum adjustment
    "KELLY_ADJUSTMENT_MAX": 1.2,  # 1.2x maximum adjustment
    "KELLY_CONFIDENCE_MIN": 0.3,  # 30% min confidence
    "KELLY_CONFIDENCE_MAX": 0.9,  # 90% max confidence
    "KELLY_CONFIDENCE_RANGE": 0.6,  # Range denominator for scaling

    # Funding rate & squeeze thresholds
    "HIGH_FUNDING_THRESHOLD": 0.01,  # 0.01% per 8h = high
    "EXTREME_FUNDING_THRESHOLD": 0.05,  # 0.05% per 8h = extreme
    "HIGH_OI_PERCENTILE": 0.80,  # Top 20% = high OI
}

# ============================================================================
# DATABASE CONFIG - Connection & Pool Settings
# ============================================================================

DATABASE_CONFIG: Dict[str, Any] = {
    "POOL_SIZE": 20,  # Concurrent connections in pool
    "MAX_OVERFLOW": 80,  # Additional connections before blocking
    "ECHO_SQL": False,  # Set to True for SQL logging in dev
}

# ============================================================================
# API CONFIG - Rate Limiting, Pricing, Fees
# ============================================================================

API_CONFIG: Dict[str, Any] = {
    # Rate limiting (requests per minute)
    "LLM_CALLS_PER_MINUTE": 10,  # LLM rate limit: 10 calls/min
    "DEFAULT_RATE_LIMIT_RPM": 50,  # Default: 50 requests/min

    # LLM pricing ($ per 1M tokens)
    "CLAUDE_INPUT_COST_PER_1M": 3.0,
    "CLAUDE_OUTPUT_COST_PER_1M": 15.0,
    "GPT4_INPUT_COST_PER_1M": 10.0,
    "GPT4_OUTPUT_COST_PER_1M": 30.0,
    "DEEPSEEK_INPUT_COST_PER_1M": 0.14,
    "DEEPSEEK_OUTPUT_COST_PER_1M": 0.28,
    "QWEN_INPUT_COST_PER_1M": 0.20,
    "QWEN_OUTPUT_COST_PER_1M": 0.60,

    # Model rate limits (calls per minute)
    "MODEL_RATE_LIMITS": {
        "claude": 50,
        "gpt-4": 50,
        "deepseek": 50,
        "gemini": 50,
    },
}

# ============================================================================
# INDICATOR CONFIG - Technical Indicator Parameters
# ============================================================================

INDICATOR_CONFIG: Dict[str, Any] = {
    # RSI parameters
    "RSI_PERIOD": 14,  # RSI period: 14 candles
    "RSI_OVERSOLD_THRESHOLD": 40,  # Oversold: < 40
    "RSI_OVERBOUGHT_THRESHOLD": 80,  # Overbought: > 80
    "RSI_BREAKOUT_THRESHOLD": 60,  # Breakout: > 60

    # EMA parameters
    "EMA_FAST_PERIOD": 9,  # Fast EMA: 9 candles
    "EMA_SLOW_PERIOD": 21,  # Slow EMA: 21 candles
    "EMA_TREND_PERIOD": 50,  # Trend EMA: 50 candles (long-term)

    # ATR & Supertrend
    "ATR_PERIOD": 14,  # ATR period: 14 candles
    "SUPERTREND_PERIOD": 10,  # Supertrend period: 10 candles
    "SUPERTREND_MULTIPLIER": 3.0,  # Supertrend ATR multiplier: 3.0x

    # FVG detector
    "FVG_ATR_PERIOD": 14,  # Fair Value Gap ATR period: 14

    # Market data
    "MIN_CANDLES_FOR_INDICATORS": 14,  # Minimum candles needed
    "OHLCV_1H_LIMIT": 250,  # 1H candles to fetch: 250
    "OHLCV_4H_LIMIT": 20,  # 4H candles to fetch: 20
    "TRINITY_MIN_CANDLES": 200,  # Trinity indicators minimum: 200
    "DEFAULT_OHLCV_LIMIT": 100,  # Default OHLCV limit: 100

    # Timeframe offsets for multi-coin prompt
    "TIMEFRAME_CANDLE_OFFSETS": {
        "1h": 12,
        "4h": 48,
        "24h": 288,
    },
}

# ============================================================================
# KELLY CRITERION CONFIG
# ============================================================================

KELLY_CONFIG: Dict[str, Any] = {
    "MIN_TRADES_FOR_KELLY": 20,  # Minimum trades for Kelly calculation
    "BASE_SIZE_PCT": 0.10,  # 10% base position size
    "RISK_PER_TRADE_PCT": 0.02,  # 2% risk per trade
    "LOW_WINRATE_MULTIPLIER": 0.5,  # 0.5x multiplier for low win rate
    "WIN_RATE_THRESHOLD": 0.30,  # 30% win rate threshold
    "FRACTION_MIN": 0.01,  # 1% minimum Kelly fraction
    "FRACTION_MAX": 1.0,  # 100% maximum Kelly fraction
    "LOOKBACK_DAYS": 90,  # 90 days lookback for trades
}

# ============================================================================
# PERFORMANCE METRICS CONFIG
# ============================================================================

PERFORMANCE_CONFIG: Dict[str, Any] = {
    "DEFAULT_LOOKBACK_DAYS": 30,  # Default lookback: 30 days
    "WIN_PROBABILITY_LOOKBACK_DAYS": 30,  # 30 days for win prob
    "DAILY_RISK_FREE_RATE": 0.00005477,  # ~2% annual risk-free rate
}

# ============================================================================
# PROMPT GENERATION CONFIG
# ============================================================================

PROMPT_CONFIG: Dict[str, Any] = {
    # Example leverage values in prompts
    "EXAMPLE_SHORT_MAX_LEVERAGE": 3,  # Example: max leverage for sells
    "EXAMPLE_LONG_MAX_LEVERAGE": 5,  # Example: max leverage for buys
    "EXAMPLE_LEVERAGE_IN_PROMPT": 5,  # Example leverage in JSON
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_config(category: str) -> Dict[str, Any]:
    """
    Get configuration dictionary by category.

    Args:
        category: Config category ('trading', 'timing', 'limits', etc.)

    Returns:
        Configuration dictionary for the category

    Raises:
        ValueError: If category not found
    """
    configs = {
        "trading": TRADING_CONFIG,
        "timing": TIMING_CONFIG,
        "limits": LIMITS_CONFIG,
        "validation": VALIDATION_CONFIG,
        "database": DATABASE_CONFIG,
        "api": API_CONFIG,
        "indicator": INDICATOR_CONFIG,
        "kelly": KELLY_CONFIG,
        "performance": PERFORMANCE_CONFIG,
        "prompt": PROMPT_CONFIG,
    }

    if category.lower() not in configs:
        raise ValueError(
            f"Unknown config category: {category}. "
            f"Available: {', '.join(configs.keys())}"
        )

    return configs[category.lower()]


def get_constant(category: str, key: str, default: Any = None) -> Any:
    """
    Get a specific constant value.

    Args:
        category: Config category
        key: Constant key name
        default: Default value if not found

    Returns:
        Constant value or default

    Example:
        >>> get_constant("trading", "DEFAULT_POSITION_SIZE_PCT")
        0.35
    """
    try:
        config = get_config(category)
        return config.get(key, default)
    except ValueError:
        return default
