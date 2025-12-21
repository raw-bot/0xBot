"""Block: Market Data - Fetches prices and calculates indicators.

This block is responsible for:
- Fetching current prices from exchange
- Calculating technical indicators (RSI, EMA, ATR)
- Providing market snapshots for all trading symbols
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

from ..core.config import config
from ..core.exchange_client import get_exchange_client
from ..core.logger import get_logger
from ..services.indicator_service import IndicatorService
from ..services.market_data_service import MarketDataService

logger = get_logger(__name__)


@dataclass
class MarketSnapshot:
    """Market data snapshot for a single symbol."""

    symbol: str
    price: Decimal
    change_24h: float
    volume_24h: float
    rsi: Optional[float] = None
    ema_fast: Optional[float] = None
    ema_slow: Optional[float] = None
    atr: Optional[float] = None
    trend: str = "neutral"
    ohlcv_1h: Optional[list] = None
    ohlcv_4h: Optional[list] = None


class MarketDataBlock:
    """Fetches and processes market data for all trading symbols."""

    def __init__(self):
        self.exchange = get_exchange_client()
        self.market_data_service = MarketDataService(self.exchange)
        self.indicator_service = IndicatorService()
        self.symbols = config.ALLOWED_SYMBOLS

    async def fetch_all(self) -> Dict[str, MarketSnapshot]:
        """
        Fetch market data for all configured symbols.

        Returns:
            Dict mapping symbol to MarketSnapshot
        """
        snapshots = {}

        for symbol in self.symbols:
            try:
                snapshot = await self._fetch_symbol(symbol)
                if snapshot:
                    snapshots[symbol] = snapshot
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")

        logger.info(f"📊 Fetched market data for {len(snapshots)} symbols")
        return snapshots

    async def _fetch_symbol(self, symbol: str) -> Optional[MarketSnapshot]:
        """Fetch market data for a single symbol."""
        try:
            # Get current ticker
            ticker = await self.market_data_service.fetch_ticker(symbol)
            if not ticker:
                return None

            # Get OHLCV for indicators
            ohlcv_1h = await self.market_data_service.fetch_ohlcv(symbol, timeframe="1h", limit=50)
            ohlcv_4h = await self.market_data_service.fetch_ohlcv(symbol, timeframe="4h", limit=20)

            # Calculate indicators
            indicators = {}
            if ohlcv_1h and len(ohlcv_1h) >= 14:
                closes = [float(c.close) for c in ohlcv_1h]
                highs = [float(c.high) for c in ohlcv_1h]
                lows = [float(c.low) for c in ohlcv_1h]

                # RSI - get last value
                rsi_values = self.indicator_service.calculate_rsi(closes)
                indicators["rsi"] = rsi_values[-1] if rsi_values else None

                # EMAs for trend
                ema_fast = self.indicator_service.calculate_ema(closes, period=9)
                ema_slow = self.indicator_service.calculate_ema(closes, period=21)
                indicators["ema_fast"] = ema_fast[-1] if ema_fast else None
                indicators["ema_slow"] = ema_slow[-1] if ema_slow else None

                # ATR - get last value
                atr_values = self.indicator_service.calculate_atr(highs, lows, closes)
                indicators["atr"] = atr_values[-1] if atr_values else None

                # Determine trend from EMAs
                if indicators["ema_fast"] and indicators["ema_slow"]:
                    if indicators["ema_fast"] > indicators["ema_slow"]:
                        indicators["trend"] = "bullish"
                    elif indicators["ema_fast"] < indicators["ema_slow"]:
                        indicators["trend"] = "bearish"
                    else:
                        indicators["trend"] = "neutral"

            return MarketSnapshot(
                symbol=symbol,
                price=Decimal(str(ticker.last)),
                change_24h=ticker.percentage or 0,
                volume_24h=ticker.quote_volume or 0,
                rsi=indicators.get("rsi"),
                ema_fast=indicators.get("ema_fast"),
                ema_slow=indicators.get("ema_slow"),
                atr=indicators.get("atr"),
                trend=indicators.get("trend", "neutral"),
                ohlcv_1h=ohlcv_1h,
                ohlcv_4h=ohlcv_4h,
            )

        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return None

    async def get_price(self, symbol: str) -> Optional[Decimal]:
        """Get current price for a symbol."""
        try:
            ticker = await self.market_data_service.fetch_ticker(symbol)
            return Decimal(str(ticker.last)) if ticker else None
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None
