"""Market data service for fetching and processing market data."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from ..core.exchange_client import ExchangeClient, get_exchange_client
from ..core.logger import get_logger

logger = get_logger(__name__)


class OHLCV:
    """OHLCV candlestick data."""
    
    def __init__(
        self,
        timestamp: int,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: float
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
        """Initialize ticker with safe decimal conversion."""
        self.symbol = data.get('symbol', '')
        
        # Helper function to safely convert to Decimal
        def safe_decimal(value, default='0'):
            """Convert value to Decimal, handling None and invalid values."""
            if value in (None, '', 'None'):
                return Decimal(default) if default else None
            try:
                return Decimal(str(value))
            except Exception:
                return Decimal(default) if default else None
        
        # Required fields
        self.last = safe_decimal(data.get('last'), '0')
        
        # Optional fields with safe conversion
        self.bid = safe_decimal(data.get('bid'), None)
        self.ask = safe_decimal(data.get('ask'), None)
        
        # Volume fields - OKX might use 'volume' instead of 'baseVolume'
        base_vol = data.get('baseVolume') or data.get('volume')
        self.volume = safe_decimal(base_vol, '0')
        self.quote_volume = safe_decimal(data.get('quoteVolume'), '0')
        
        # Price range
        self.high = safe_decimal(data.get('high'), None)
        self.low = safe_decimal(data.get('low'), None)
        
        # Change metrics
        self.change = safe_decimal(data.get('change'), None)
        self.percentage = safe_decimal(data.get('percentage'), None)
        
        # Timestamp
        self.timestamp = data.get('timestamp', 0)
        self.datetime = datetime.fromtimestamp(self.timestamp / 1000) if self.timestamp else None
    
    def __repr__(self) -> str:
        return f"<Ticker({self.symbol}, last:{self.last}, vol:{self.volume})>"


class MarketDataService:
    """Service for fetching and processing market data."""
    
    def __init__(self, exchange_client: Optional[ExchangeClient] = None):
        """
        Initialize market data service.
        
        Args:
            exchange_client: Optional exchange client, will create default if not provided
        """
        self.exchange = exchange_client or get_exchange_client()
    
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1h',
        limit: int = 100
    ) -> list[OHLCV]:
        """
        Fetch OHLCV candlestick data.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candle timeframe ('1m', '5m', '15m', '1h', '4h', '1d')
            limit: Number of candles to fetch
            
        Returns:
            List of OHLCV objects
        """
        try:
            raw_ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit)
            
            # Convert to OHLCV objects
            ohlcv_list = [
                OHLCV(
                    timestamp=int(candle[0]),
                    open=float(candle[1]),
                    high=float(candle[2]),
                    low=float(candle[3]),
                    close=float(candle[4]),
                    volume=float(candle[5])
                )
                for candle in raw_ohlcv
            ]
            
            logger.debug(f"Fetched {len(ohlcv_list)} candles for {symbol} ({timeframe})")
            return ohlcv_list
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            raise
    
    async def fetch_ticker(self, symbol: str) -> Ticker:
        """
        Fetch current ticker data.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            
        Returns:
            Ticker object with current market data
        """
        try:
            ticker_data = await self.exchange.fetch_ticker(symbol)
            ticker = Ticker(ticker_data)
            
            logger.debug(f"Fetched ticker for {symbol}: {ticker.last}")
            return ticker
            
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            raise
    
    async def get_current_price(self, symbol: str) -> Decimal:
        """
        Get current market price for a symbol.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Current price as Decimal
        """
        ticker = await self.fetch_ticker(symbol)
        return ticker.last
    
    async def get_funding_rate(self, symbol: str) -> float:
        """
        Get current funding rate for perpetual futures.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Current funding rate as percentage
        """
        try:
            rate = await self.exchange.get_funding_rate(symbol)
            logger.debug(f"Funding rate for {symbol}: {rate}")
            return rate
            
        except Exception as e:
            logger.error(f"Error fetching funding rate: {e}")
            return 0.0
    
    def extract_closes(self, ohlcv_list: list[OHLCV]) -> list[float]:
        """
        Extract closing prices from OHLCV data.
        
        Args:
            ohlcv_list: List of OHLCV objects
            
        Returns:
            List of closing prices as floats
        """
        return [float(candle.close) for candle in ohlcv_list]
    
    def extract_highs(self, ohlcv_list: list[OHLCV]) -> list[float]:
        """
        Extract high prices from OHLCV data.
        
        Args:
            ohlcv_list: List of OHLCV objects
            
        Returns:
            List of high prices as floats
        """
        return [float(candle.high) for candle in ohlcv_list]
    
    def extract_lows(self, ohlcv_list: list[OHLCV]) -> list[float]:
        """
        Extract low prices from OHLCV data.
        
        Args:
            ohlcv_list: List of OHLCV objects
            
        Returns:
            List of low prices as floats
        """
        return [float(candle.low) for candle in ohlcv_list]
    
    def extract_volumes(self, ohlcv_list: list[OHLCV]) -> list[float]:
        """
        Extract volumes from OHLCV data.
        
        Args:
            ohlcv_list: List of OHLCV objects
            
        Returns:
            List of volumes as floats
        """
        return [float(candle.volume) for candle in ohlcv_list]
    
    async def get_market_snapshot(self, symbol: str, timeframe: str = '1h') -> dict:
        """
        Get complete market snapshot with OHLCV and current ticker.
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            
        Returns:
            Dictionary with OHLCV data and current ticker
        """
        try:
            # Fetch both OHLCV and current ticker
            ohlcv = await self.fetch_ohlcv(symbol, timeframe, limit=100)
            ticker = await self.fetch_ticker(symbol)
            funding_rate = await self.get_funding_rate(symbol)
            
            snapshot = {
                'symbol': symbol,
                'timeframe': timeframe,
                'ohlcv': ohlcv,
                'ticker': ticker,
                'current_price': ticker.last,
                'funding_rate': funding_rate,
                'timestamp': datetime.utcnow()
            }
            
            logger.info(f"Created market snapshot for {symbol}")
            return snapshot
            
        except Exception as e:
            logger.error(f"Error creating market snapshot: {e}")
    
    async def get_market_data_multi_timeframe(
        self,
        symbol: str,
        timeframe_short: str = '1h',
        timeframe_long: str = '4h'
    ) -> dict:
        """
        Get market data for multiple timeframes.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe_short: Short timeframe (default: '1h' which is actually used as 3min proxy)
            timeframe_long: Long timeframe for context (default: '4h')
        
        Returns:
            Dictionary with both timeframes data
        """
        logger.debug(f"Fetching multi-timeframe data for {symbol}: {timeframe_short} + {timeframe_long}")
        
        # Fetch short timeframe (existing data)
        data_short = await self.get_market_snapshot(symbol, timeframe_short)
        
        # Fetch long timeframe (4H)
        try:
            ohlcv_long = await self.fetch_ohlcv(symbol, timeframe_long, limit=100)
            
            if not ohlcv_long:
                logger.warning(f"No data returned for {symbol} on {timeframe_long}")
                return {
                    'short': data_short,
                    'long': None
                }
            
            # Calculate indicators for 4H
            from .indicator_service import IndicatorService
            
            closes = self.extract_closes(ohlcv_long)
            highs = self.extract_highs(ohlcv_long)
            lows = self.extract_lows(ohlcv_long)
            
            indicators_long = IndicatorService.calculate_all_indicators(closes, highs, lows)
            
            # Get current values from 4H
            latest_4h = IndicatorService.get_latest_values(indicators_long)
            
            logger.debug(f"Successfully fetched {timeframe_long} data for {symbol}")
            
            return {
                'short': data_short,
                'long': latest_4h
            }
            
        except Exception as e:
            logger.error(f"Error fetching {timeframe_long} data for {symbol}: {e}")
            return {
                'short': data_short,
                'long': None
            }
            raise