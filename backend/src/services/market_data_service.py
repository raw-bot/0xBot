"""Market data service for fetching and processing market data."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from ..core.exchange_client import ExchangeClient, get_exchange_client
from ..core.logger import get_logger

logger = get_logger(__name__)


def _safe_decimal(value, default="0") -> Optional[Decimal]:
    """Convert value to Decimal, handling None and invalid values."""
    if value in (None, "", "None"):
        return Decimal(default) if default else None
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default) if default else None


class OHLCV:
    """OHLCV candlestick data."""

    def __init__(
        self, timestamp: int, open: float, high: float, low: float, close: float, volume: float
    ):
        self.timestamp = timestamp
        self.datetime = datetime.fromtimestamp(timestamp / 1000)
        self.open = Decimal(str(open))
        self.high = Decimal(str(high))
        self.low = Decimal(str(low))
        self.close = Decimal(str(close))
        self.volume = Decimal(str(volume))

    def __repr__(self) -> str:
        return f"<OHLCV({self.datetime}, O:{self.open}, H:{self.high}, L:{self.low}, C:{self.close})>"


class Ticker:
    """Current market ticker data."""

    def __init__(self, data: dict):
        self.symbol = data.get("symbol", "")
        self.last = _safe_decimal(data.get("last"), "0")
        self.bid = _safe_decimal(data.get("bid"), None)
        self.ask = _safe_decimal(data.get("ask"), None)
        self.volume = _safe_decimal(data.get("baseVolume") or data.get("volume"), "0")
        self.quote_volume = _safe_decimal(data.get("quoteVolume"), "0")
        self.high = _safe_decimal(data.get("high"), None)
        self.low = _safe_decimal(data.get("low"), None)
        self.change = _safe_decimal(data.get("change"), None)
        self.percentage = _safe_decimal(data.get("percentage"), None)
        self.timestamp = data.get("timestamp", 0)
        self.datetime = datetime.fromtimestamp(self.timestamp / 1000) if self.timestamp else None

    def __repr__(self) -> str:
        return f"<Ticker({self.symbol}, last:{self.last}, vol:{self.volume})>"


class MarketDataService:
    """Service for fetching and processing market data."""

    def __init__(self, exchange_client: Optional[ExchangeClient] = None):
        self.exchange = exchange_client or get_exchange_client()

    async def fetch_ohlcv(
        self, symbol: str, timeframe: str = "1h", limit: int = 100
    ) -> list[OHLCV]:
        """Fetch OHLCV candlestick data."""
        try:
            raw_ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit)
            return [
                OHLCV(
                    timestamp=int(candle[0]),
                    open=float(candle[1]),
                    high=float(candle[2]),
                    low=float(candle[3]),
                    close=float(candle[4]),
                    volume=float(candle[5]),
                )
                for candle in raw_ohlcv
            ]
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            raise

    async def fetch_ticker(self, symbol: str) -> Ticker:
        """Fetch current ticker data."""
        try:
            ticker_data = await self.exchange.fetch_ticker(symbol)
            if not ticker_data.get("last"):
                logger.warning(f"Ticker missing last price for {symbol}")
            else:
                logger.debug(f"Ticker {symbol}: {ticker_data.get('last')}")
            return Ticker(ticker_data)
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            raise

    async def get_current_price(self, symbol: str) -> Decimal:
        """Get current market price for a symbol."""
        ticker = await self.fetch_ticker(symbol)
        return ticker.last

    async def get_funding_rate(self, symbol: str) -> float:
        """Get current funding rate for perpetual futures."""
        try:
            return await self.exchange.get_funding_rate(symbol)
        except Exception as e:
            logger.error(f"Error fetching funding rate: {e}")
            return 0.0

    async def get_open_interest(self, symbol: str) -> dict:
        """Get open interest data for perpetual futures."""
        try:
            oi_data = await self.exchange.fetch_open_interest(symbol)
            latest = float(oi_data.get("openInterest", 0)) if oi_data else 0
            return {"latest": latest, "average": latest}
        except Exception as e:
            logger.error(f"Error fetching open interest for {symbol}: {e}")
            return {"latest": 0, "average": 0}

    def extract_closes(self, ohlcv_list: list[OHLCV]) -> list[float]:
        """Extract closing prices from OHLCV data."""
        return [float(candle.close) for candle in ohlcv_list]

    def extract_highs(self, ohlcv_list: list[OHLCV]) -> list[float]:
        """Extract high prices from OHLCV data."""
        return [float(candle.high) for candle in ohlcv_list]

    def extract_lows(self, ohlcv_list: list[OHLCV]) -> list[float]:
        """Extract low prices from OHLCV data."""
        return [float(candle.low) for candle in ohlcv_list]

    def extract_volumes(self, ohlcv_list: list[OHLCV]) -> list[float]:
        """Extract volumes from OHLCV data."""
        return [float(candle.volume) for candle in ohlcv_list]

    async def get_market_snapshot(self, symbol: str, timeframe: str = "1h") -> dict:
        """Get complete market snapshot with OHLCV, indicators, and series data."""
        try:
            from .indicator_service import IndicatorService

            ohlcv = await self.fetch_ohlcv(symbol, timeframe, limit=100)
            ticker = await self.fetch_ticker(symbol)
            funding_rate = await self.get_funding_rate(symbol)
            open_interest = await self.get_open_interest(symbol)

            closes = self.extract_closes(ohlcv)
            highs = self.extract_highs(ohlcv)
            lows = self.extract_lows(ohlcv)
            volumes = self.extract_volumes(ohlcv)
            avg_volume = sum(volumes) / len(volumes) if volumes else 0

            ema20_series = IndicatorService.calculate_ema(closes, 20)
            ema50_series = IndicatorService.calculate_ema(closes, 50)
            rsi7_series = IndicatorService.calculate_rsi(closes, 7)
            rsi14_series = IndicatorService.calculate_rsi(closes, 14)
            macd_data = IndicatorService.calculate_macd(closes)
            atr3_series = IndicatorService.calculate_atr(highs, lows, closes, 3)
            atr14_series = IndicatorService.calculate_atr(highs, lows, closes, 14)

            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "ohlcv": ohlcv,
                "ticker": ticker,
                "current_price": float(ticker.last),
                "funding_rate": funding_rate,
                "open_interest": open_interest,
                "timestamp": datetime.utcnow(),
                "price_series": closes,
                "ema20_series": ema20_series,
                "ema50_series": ema50_series,
                "macd_series": macd_data["macd"],
                "rsi7_series": rsi7_series,
                "rsi14_series": rsi14_series,
                "technical_indicators": {
                    "5m": {
                        "ema20": _get_last_valid(ema20_series) or 0,
                        "ema50": _get_last_valid(ema50_series) or 0,
                        "macd": _get_last_valid(macd_data["macd"]) or 0,
                        "rsi7": _get_last_valid(rsi7_series) or 50,
                        "rsi14": _get_last_valid(rsi14_series) or 50,
                    },
                    "1h": {
                        "ema20": 0,
                        "ema50": 0,
                        "macd": 0,
                        "rsi14": 50,
                        "atr3": _get_last_valid(atr3_series) or 0,
                        "atr14": _get_last_valid(atr14_series) or 0,
                        "volume": volumes[-1] if volumes else 0,
                        "avg_volume": avg_volume,
                    },
                },
            }
        except Exception as e:
            logger.error(f"Error creating market snapshot: {e}")
            raise

    async def get_market_data_multi_timeframe(
        self, symbol: str, timeframe_short: str = "1h", timeframe_long: str = "4h"
    ) -> dict:
        """Get market data for multiple timeframes with full series data."""
        snapshot = await self.get_market_snapshot(symbol, timeframe_short)

        try:
            from .indicator_service import IndicatorService

            ohlcv_long = await self.fetch_ohlcv(symbol, timeframe_long, limit=100)
            if not ohlcv_long:
                return snapshot

            closes = self.extract_closes(ohlcv_long)
            highs = self.extract_highs(ohlcv_long)
            lows = self.extract_lows(ohlcv_long)
            volumes = self.extract_volumes(ohlcv_long)
            avg_volume = sum(volumes) / len(volumes) if volumes else 0

            ema20 = IndicatorService.calculate_ema(closes, 20)
            ema50 = IndicatorService.calculate_ema(closes, 50)
            macd = IndicatorService.calculate_macd(closes)
            rsi14 = IndicatorService.calculate_rsi(closes, 14)
            atr3 = IndicatorService.calculate_atr(highs, lows, closes, 3)
            atr14 = IndicatorService.calculate_atr(highs, lows, closes, 14)

            snapshot["macd_series_4h"] = macd["macd"]
            snapshot["rsi14_series_4h"] = rsi14
            snapshot["technical_indicators"]["1h"] = {
                "ema20": _get_last_valid(ema20) or 0,
                "ema50": _get_last_valid(ema50) or 0,
                "macd": _get_last_valid(macd["macd"]) or 0,
                "rsi14": _get_last_valid(rsi14) or 50,
                "atr3": _get_last_valid(atr3) or 0,
                "atr14": _get_last_valid(atr14) or 0,
                "volume": volumes[-1] if volumes else 0,
                "avg_volume": avg_volume,
            }
            return snapshot
        except Exception as e:
            logger.error(f"Error fetching {timeframe_long} data for {symbol}: {e}")
            return snapshot


def _get_last_valid(series: list) -> Optional[float]:
    """Get last non-None value from series."""
    if not series:
        return None
    for val in reversed(series):
        if val is not None:
            return val
    return None
