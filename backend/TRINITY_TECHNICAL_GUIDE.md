# Trinity Framework - Technical Implementation Guide

**Version**: 1.0
**Last Updated**: 2026-01-16
**Status**: Phase 3C Complete - Ready for Phase 3D Testing

---

## 🔍 Code Architecture

### 1. IndicatorBlock (`src/blocks/block_indicators.py`)

**Purpose**: Pure Python indicator calculations without external dependencies

**Key Methods**:
```python
def sma(values: List[float], period: int) -> List[Optional[float]]
    # Simple Moving Average

def ema(values: List[float], period: int) -> List[Optional[float]]
    # Exponential Moving Average

def rsi(values: List[float], period: int = 14) -> List[float]
    # Relative Strength Index (0-100)

def atr(highs, lows, closes, period: int = 14) -> List[float]
    # Average True Range

def supertrend(highs, lows, closes, period: int = 10, multiplier: float = 3.0) -> Tuple
    # Returns (supertrend_values, supertrend_signal)
    # Signal: "buy" (green), "sell" (red), or "neutral"

def calculate_indicators_from_ccxt(ohlcv_dict) -> Dict
    # Main entry point - returns all Trinity indicators
    # Keys: sma_200, ema_20, rsi, adx, supertrend, supertrend_signal, volume_ma, confluence_score, signals
```

**Example Usage**:
```python
from src.blocks.block_indicators import IndicatorBlock

indicator_block = IndicatorBlock()

# Convert CCXT format to dict
ohlcv_dict = indicator_block.convert_ccxt_to_dict(ohlcv_list)

# Calculate all Trinity indicators
indicators = indicator_block.calculate_indicators_from_ccxt(ohlcv_dict)

print(f"Confluence Score: {indicators['confluence_score']}")
print(f"Signals: {indicators['signals']}")
```

---

### 2. MarketSnapshot Enhanced (`src/blocks/block_market_data.py`)

**Trinity Fields Added**:
```python
@dataclass
class MarketSnapshot:
    # ... existing fields ...

    # Trinity Framework Indicators
    sma_200: Optional[float] = None           # Regime filter
    ema_20: Optional[float] = None            # Entry zone
    adx: Optional[float] = None               # Trend strength
    supertrend: Optional[float] = None        # Exit level
    supertrend_signal: str = "neutral"        # "buy" or "sell"
    volume_ma: Optional[float] = None         # Volume confirmation
    confluence_score: float = 0.0             # 0-100 score
    signals: Dict[str, Any] = field(...)      # Signal dict
```

**Market Data Flow**:
```python
# In MarketDataBlock._fetch_symbol()
if ohlcv_1h and len(ohlcv_1h) >= 200:
    ohlcv_dict = self.indicator_block.convert_ccxt_to_dict(ohlcv_1h)
    trinity_indicators = self.indicator_block.calculate_indicators_from_ccxt(ohlcv_dict)

    return MarketSnapshot(
        # ... legacy fields ...
        # Trinity indicators
        sma_200=trinity_indicators.get("sma_200"),
        ema_20=trinity_indicators.get("ema_20"),
        adx=trinity_indicators.get("adx"),
        supertrend=trinity_indicators.get("supertrend"),
        supertrend_signal=trinity_indicators.get("supertrend_signal", "neutral"),
        volume_ma=trinity_indicators.get("volume_ma"),
        confluence_score=trinity_indicators.get("confluence_score", 0.0),
        signals=trinity_indicators.get("signals", {}),
    )
```

---

### 3. TrinityDecisionBlock (`src/blocks/block_trinity_decision.py`)

**Entry Analysis Logic**:
```python
class TrinityDecisionBlock:
    async def get_decisions(
        self,
        market_data: Dict[str, MarketSnapshot],
        portfolio_context: Dict,
    ) -> Optional[Dict[str, TradingSignal]]:
        """
        Returns: Dict[symbol -> TradingSignal] or None
        """

    def _analyze_confluence(self, symbol: str, snapshot: MarketSnapshot) -> TrinityDecision:
        """
        Analyzes confluence and returns TrinityDecision with:
        - should_enter: bool
        - entry_side: SignalSide (LONG/SHORT)
        - confidence: float (0-1)
        - confluence_score: float (0-100)
        - signals_met: int (0-5)
        """

    def should_exit(self, symbol: str, snapshot: MarketSnapshot) -> tuple[bool, str]:
        """
        Returns: (should_exit: bool, reason: str)
        """
```

**Confluence Scoring**:
```python
def _analyze_confluence(self, symbol: str, snapshot: MarketSnapshot):
    signals = snapshot.signals or {}
    confluence = snapshot.confluence_score or 0.0

    # Check 5 conditions
    regime_ok = signals.get("regime_filter", False)           # Price > 200 SMA
    trend_strength_ok = signals.get("trend_strength", False)  # ADX > 25
    pullback_detected = signals.get("pullback_detected", False)
    price_bounced = signals.get("price_bounced", False)       # Back above EMA
    oversold = signals.get("oversold", False)                 # RSI < 40
    volume_confirmed = signals.get("volume_confirmed", False)

    conditions = [regime_ok, trend_strength_ok, price_bounced, oversold, volume_confirmed]
    signals_met = sum(conditions)

    if signals_met >= 4:
        confidence = min(signals_met / 5, 1.0)  # 80-100%
        return TrinityDecision(
            should_enter=True,
            confidence=confidence,
            signals_met=signals_met,
            confluence_score=confluence,
        )
```

---

### 4. Orchestrator Integration (`src/blocks/orchestrator.py`)

**Initialization**:
```python
class TradingOrchestrator:
    def __init__(
        self,
        bot_id: uuid.UUID,
        cycle_interval: int = 180,
        llm_client: Optional[LLMClient] = None,
        decision_mode: str = "trinity",  # NEW: supports "trinity", "llm", "indicator"
    ):
        # Initialize ALL decision blocks
        self.trinity_decision = TrinityDecisionBlock()
        self.llm_decision = LLMDecisionBlock(...)
        self.indicator_decision = IndicatorDecisionBlock()

        # Select active based on mode
        if decision_mode == "trinity":
            self.decision = self.trinity_decision
```

**Signal Normalization**:
```python
async def _execute_decision(self, decision, market_data, portfolio_state):
    # Handle both TradingSignal (enum) and legacy formats
    signal_type = getattr(decision, 'signal_type', None)
    signal_str = str(signal_type) if signal_type else getattr(decision, 'signal', None)

    # Normalize side (enum or string)
    side = str(decision.side) if hasattr(decision.side, 'value') else decision.side

    # Convert Decimal prices to float for validation
    stop_loss = float(decision.stop_loss) if decision.stop_loss else None
    take_profit = float(decision.take_profit) if decision.take_profit else None
```

**Mode Switching**:
```python
def switch_decision_mode(self, mode: str) -> bool:
    """
    Switch between "trinity", "llm", or "indicator" modes
    """
    if mode == "trinity":
        self.decision = self.trinity_decision
        self.decision_mode = "trinity"
        logger.info("📈 Switched to Trinity indicator framework")
        return True
    # ... handle "llm" and "indicator" ...
```

---

### 5. TradingSignal Model (`src/models/signal.py`)

**Unified Signal Format**:
```python
@dataclass
class TradingSignal:
    symbol: str
    signal_type: SignalType  # Enum: BUY_TO_ENTER, SELL_TO_ENTER, CLOSE, HOLD
    side: Optional[SignalSide] = None  # Enum: LONG, SHORT
    confidence: float = 0.5  # 0-1
    reasoning: str = ""
    entry_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    size_pct: float = 0.0  # 0.01 = 1% of capital
    leverage: int = 1

    @property
    def is_entry_signal(self) -> bool:
        return self.signal_type in [SignalType.BUY_TO_ENTER, SignalType.SELL_TO_ENTER]
```

---

## 📊 Data Flow Example

### Complete Trading Cycle (Trinity Mode)

```
1. FETCH MARKET DATA
   MarketDataBlock.fetch_all()
   → For each symbol, fetch 250 1H candles (need 200 for SMA_200)

2. CALCULATE TRINITY INDICATORS
   IndicatorBlock.calculate_indicators_from_ccxt()
   → Calculates: SMA_200, EMA_20, RSI, ADX, Supertrend, Volume MA
   → Returns confluence_score (0-100) and signals dict

3. ENRICH MARKET SNAPSHOT
   MarketSnapshot now contains:
   {
       symbol: "BTC/USDT",
       price: 42000,
       sma_200: 41500,
       ema_20: 41800,
       adx: 28.5,
       supertrend: 41200,
       supertrend_signal: "buy",
       confluence_score: 75.0,
       signals: {
           "regime_filter": True,
           "trend_strength": True,
           "pullback_detected": True,
           "price_bounced": True,
           "oversold": False,
           "volume_confirmed": True,
       }
   }

4. GENERATE TRINITY DECISIONS
   TrinityDecisionBlock.get_decisions(market_data, portfolio_context)
   → For each symbol, analyze confluence
   → If signals_met >= 4: generate BUY_TO_ENTER signal
   → Return: Dict[symbol -> TradingSignal]

5. VALIDATE & EXECUTE
   Orchestrator._execute_decision(decision)
   → Normalize signal format (enum → string)
   → Validate with RiskBlock
   → Execute with ExecutionBlock
   → Log with ActivityLogger

6. UPDATE POSITIONS
   Check existing positions against Supertrend/RSI/SMA
   → If exit conditions met, close position
   → Record win/loss in memory
```

---

## 🧪 Testing Code

### Unit Test: Indicator Calculation

```python
import asyncio
from src.blocks.block_indicators import IndicatorBlock

async def test_indicators():
    block = IndicatorBlock()

    # Sample OHLCV data
    ohlcv_list = [...]  # 250 candles

    ohlcv_dict = block.convert_ccxt_to_dict(ohlcv_list)
    indicators = block.calculate_indicators_from_ccxt(ohlcv_dict)

    assert indicators['sma_200'] is not None
    assert indicators['ema_20'] is not None
    assert 0 <= indicators['confluence_score'] <= 100
    assert indicators['supertrend_signal'] in ["buy", "sell", "neutral"]

    print(f"✅ Confluence: {indicators['confluence_score']:.0f}/100")
    print(f"✅ Signals: {sum(indicators['signals'].values())}/5")

asyncio.run(test_indicators())
```

### Integration Test: Trinity Decision Block

```python
import asyncio
from src.blocks.block_market_data import MarketSnapshot
from src.blocks.block_trinity_decision import TrinityDecisionBlock
from decimal import Decimal

async def test_trinity_signals():
    trinity = TrinityDecisionBlock()

    # Create test market data
    market_data = {
        "BTC/USDT": MarketSnapshot(
            symbol="BTC/USDT",
            price=Decimal("42000"),
            change_24h=2.5,
            volume_24h=1000000,
            sma_200=41500,
            ema_20=41800,
            adx=28.5,
            supertrend=41200,
            supertrend_signal="buy",
            volume_ma=800000,
            confluence_score=80.0,
            signals={
                "regime_filter": True,
                "trend_strength": True,
                "price_bounced": True,
                "oversold": False,
                "volume_confirmed": True,
            }
        )
    }

    portfolio_context = {
        "cash": 10000,
        "equity": 15000,
        "return_pct": 0.5,
        "positions": [],
    }

    signals = await trinity.get_decisions(market_data, portfolio_context)

    assert signals is not None
    assert "BTC/USDT" in signals
    assert signals["BTC/USDT"].confidence >= 0.8

    print(f"✅ Generated {len(signals)} signals")

asyncio.run(test_trinity_signals())
```

---

## 🔧 Configuration Parameters

### Core Parameters (in `block_trinity_decision.py`)

```python
# Entry confidence levels
CONFIDENCE_STRONG = 0.8      # 4-5/5 signals
CONFIDENCE_MODERATE = 0.6    # 3/5 signals
CONFIDENCE_WEAK = 0.4        # < 3/5 signals

# Position sizing (% of capital)
SIZE_HIGH = 0.03             # 3% for high confidence
SIZE_MEDIUM = 0.02           # 2% for medium confidence
SIZE_LOW = 0.01              # 1% for low confidence

# Exit parameters
RSI_OVERBOUGHT = 75          # Exit if RSI > 75
```

### Indicator Parameters (in `block_indicators.py`)

```python
SMA_200_PERIOD = 200         # Regime filter
EMA_20_PERIOD = 20           # Entry zone
RSI_PERIOD = 14              # Momentum
RSI_OVERSOLD = 40            # Entry condition
ADX_PERIOD = 14              # Trend strength
ADX_MIN = 25                 # Strong trend threshold
ATR_PERIOD = 14              # For Supertrend
SUPERTREND_MULTIPLIER = 3.0  # Supertrend calculation
```

---

## 📈 Output Examples

### Log Output (Trinity Mode)

```
[TRINITY] BTC/USDT: Entry conditions not met (3/5 signals) - waiting for more confirmation
[TRINITY] ETH/USDT: Strong confluence (4/5 signals) | Confluence score: 85/100
[TRINITY] SOL/USDT: BUY signal | Confluence: 80/100 | Signals: 4/5 | Confidence: 80%
LONG SOL/USDT @ $140.50
[Position Update] SOL/USDT: current price: $142.30
[TRINITY] SOL/USDT: Position still valid (RSI: 55, Supertrend: HOLD)
[TRINITY] SOL/USDT: Exit triggered - RSI extreme overbought (76%)
CLOSE SOL/USDT @ $148.95 | P&L: +$336.75
```

### Confluence Score Components

```
Market: BTC/USDT | Price: $42,500
────────────────────────────────────
✅ Regime Filter    (Price > 200 SMA)      $42,500 > $41,500
✅ Trend Strength   (ADX > 25)             ADX: 28.5
✅ Price Bounce     (Above 20 EMA)         $42,500 > $41,800
❌ Momentum         (RSI < 40)             RSI: 48 (not oversold)
✅ Volume Confirm   (Vol > MA)             $950k > $800k
────────────────────────────────────
SIGNALS MET: 4/5 (80% CONFIDENCE)
CONFLUENCE: 80/100 → POSITION SIZE: 3%
```

---

## 🚀 Deployment Checklist

- ✅ Code compiles without errors
- ✅ No missing imports
- ✅ Indicator calculations verified
- ✅ Signal normalization handles both enum and string formats
- ✅ Mode switching works correctly
- ✅ Scheduler initialized with Trinity mode
- ✅ Logging contains confidence/confluence/signals info
- ✅ Compatible with existing ExecutionBlock
- ✅ Compatible with existing RiskBlock
- ⏳ Live testing pending (Phase 3D)

---

**Implementation Complete** ✅
**Ready for Phase 3D Testing**
