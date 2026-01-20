"""Block: Market Data - Fetches prices and calculates indicators."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Any

from ..core.config import config
from ..core.exchange_client import get_exchange_client
from ..core.logger import get_logger
from ..services.indicator_service import IndicatorService
from ..services.market_data_service import MarketDataService
from .block_indicators import IndicatorBlock

logger = get_logger(__name__)

MIN_CANDLES_FOR_INDICATORS = 14


@dataclass
class MarketSnapshot:
    """Market data snapshot for a single symbol with Trinity indicators."""

    symbol: str
    price: Decimal
    change_24h: float
    volume_24h: float

    # Legacy indicators (kept for compatibility)
    rsi: Optional[float] = None
    ema_fast: Optional[float] = None
    ema_slow: Optional[float] = None
    atr: Optional[float] = None
    trend: str = "neutral"
    ohlcv_1h: Optional[list[Any]] = None
    ohlcv_4h: Optional[list[Any]] = None

    # Trinity Framework Indicators
    sma_200: Optional[float] = None        # Regime filter
    ema_20: Optional[float] = None         # Entry zone
    adx: Optional[float] = None            # Trend strength
    supertrend: Optional[float] = None     # Exit signal
    supertrend_signal: str = "neutral"     # "buy" or "sell"
    volume_ma: Optional[float] = None      # Volume confirmation
    confluence_score: float = 0.0          # 0-100

    # Signal confluence dict
    signals: Dict[str, Any] = field(default_factory=dict)


class MarketDataBlock:
    """Fetches and processes market data for all trading symbols."""

    def __init__(self, paper_trading: bool = True):
        self.exchange = get_exchange_client(paper_trading=paper_trading)
        self.market_data_service = MarketDataService(self.exchange)
        self.indicator_service = IndicatorService()
        self.indicator_block = IndicatorBlock()  # Trinity framework indicators
        self.symbols = config.ALLOWED_SYMBOLS

    async def fetch_all(self) -> dict[str, MarketSnapshot]:
        """Fetch market data for all configured symbols."""
        snapshots: dict[str, MarketSnapshot] = {}
        for symbol in self.symbols:
            try:
                snapshot = await self._fetch_symbol(symbol)
                if snapshot:
                    snapshots[symbol] = snapshot
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")

        # Check if we have ANY market data
        if not snapshots:
            logger.error("🔴 CRITICAL: No market data fetched for ANY symbol! Trading cycle cannot proceed.")
            return {}  # Signal upstream that data fetch failed (return empty dict instead of None)

        logger.info(f"Fetched market data for {len(snapshots)} symbols")
        return snapshots

    async def _fetch_symbol(self, symbol: str) -> Optional[MarketSnapshot]:
        """Fetch market data for a single symbol with Trinity indicators."""
        ticker = await self.market_data_service.fetch_ticker(symbol)
        if not ticker:
            return None

        ohlcv_1h = await self.market_data_service.fetch_ohlcv(symbol, timeframe="1h", limit=250)
        ohlcv_4h = await self.market_data_service.fetch_ohlcv(symbol, timeframe="4h", limit=20)

        # Calculate legacy indicators
        legacy_indicators = self._calculate_indicators(ohlcv_1h)

        # Calculate Trinity indicators
        trinity_indicators = {}
        if ohlcv_1h and len(ohlcv_1h) >= 200:
            # Convert OHLCV objects back to raw format for indicator block
            ohlcv_raw = [
                [candle.timestamp, candle.open, candle.high, candle.low, candle.close, candle.volume]
                for candle in ohlcv_1h
            ]
            ohlcv_dict = self.indicator_block.convert_ccxt_to_dict(ohlcv_raw)
            trinity_indicators = self.indicator_block.calculate_indicators_from_ccxt(ohlcv_dict)

        return MarketSnapshot(
            symbol=symbol,
            price=Decimal(str(ticker.last)),
            change_24h=float(ticker.percentage or 0),
            volume_24h=float(ticker.quote_volume or 0),
            # Legacy indicators
            rsi=legacy_indicators.get("rsi"),
            ema_fast=legacy_indicators.get("ema_fast"),
            ema_slow=legacy_indicators.get("ema_slow"),
            atr=legacy_indicators.get("atr"),
            trend=legacy_indicators.get("trend", "neutral"),
            ohlcv_1h=ohlcv_1h,
            ohlcv_4h=ohlcv_4h,
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

    def _calculate_indicators(self, ohlcv: Optional[list[Any]]) -> dict[str, Any]:
        """Calculate technical indicators from OHLCV data."""
        if not ohlcv or len(ohlcv) < MIN_CANDLES_FOR_INDICATORS:
            return {}

        closes = [float(c.close) for c in ohlcv]
        highs = [float(c.high) for c in ohlcv]
        lows = [float(c.low) for c in ohlcv]

        rsi_values = self.indicator_service.calculate_rsi(closes)
        ema_fast = self.indicator_service.calculate_ema(closes, period=9)
        ema_slow = self.indicator_service.calculate_ema(closes, period=21)
        atr_values = self.indicator_service.calculate_atr(highs, lows, closes)

        indicators: dict[str, Any] = {
            "rsi": rsi_values[-1] if rsi_values else None,
            "ema_fast": ema_fast[-1] if ema_fast else None,
            "ema_slow": ema_slow[-1] if ema_slow else None,
            "atr": atr_values[-1] if atr_values else None,
            "trend": "neutral",
        }

        if indicators["ema_fast"] and indicators["ema_slow"]:
            if indicators["ema_fast"] > indicators["ema_slow"]:
                indicators["trend"] = "bullish"
            elif indicators["ema_fast"] < indicators["ema_slow"]:
                indicators["trend"] = "bearish"

        return indicators

    async def get_price(self, symbol: str) -> Optional[Decimal]:
        """Get current price for a symbol."""
        ticker = await self.market_data_service.fetch_ticker(symbol)
        return Decimal(str(ticker.last)) if ticker else None
