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
    
    async def get_open_interest(self, symbol: str) -> dict:
        """
        Get open interest data for perpetual futures.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Dictionary with 'latest' and 'average' open interest values
        """
        try:
            # Try to fetch open interest from exchange
            oi_data = await self.exchange.fetch_open_interest(symbol)
            
            # OKX returns openInterest as a number
            latest = float(oi_data.get('openInterest', 0)) if oi_data else 0
            
            # For average, we'd need historical data - for now use latest as average
            # TODO: Could fetch historical OI and calculate real average
            average = latest
            
            logger.debug(f"Open Interest for {symbol}: {latest}")
            return {
                'latest': latest,
                'average': average
            }
            
        except Exception as e:
            logger.error(f"Error fetching open interest for {symbol}: {e}")
            return {
                'latest': 0,
                'average': 0
            }
    
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
        Get complete market snapshot with OHLCV, indicators, and series data.
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            
        Returns:
            Dictionary with OHLCV data, current ticker, and series data
        """
        try:
            # Fetch both OHLCV and current ticker
            ohlcv = await self.fetch_ohlcv(symbol, timeframe, limit=100)
            ticker = await self.fetch_ticker(symbol)
            funding_rate = await self.get_funding_rate(symbol)
            open_interest = await self.get_open_interest(symbol)
            
            # Extract price series for indicators
            closes = self.extract_closes(ohlcv)
            highs = self.extract_highs(ohlcv)
            lows = self.extract_lows(ohlcv)
            volumes = self.extract_volumes(ohlcv)
            
            # Calculate indicators with series
            from .indicator_service import IndicatorService
            
            ema20_series = IndicatorService.calculate_ema(closes, 20)
            ema50_series = IndicatorService.calculate_ema(closes, 50)
            rsi7_series = IndicatorService.calculate_rsi(closes, 7)
            rsi14_series = IndicatorService.calculate_rsi(closes, 14)
            macd_data = IndicatorService.calculate_macd(closes)
            macd_series = macd_data['macd']
            atr3_series = IndicatorService.calculate_atr(highs, lows, closes, 3)
            atr14_series = IndicatorService.calculate_atr(highs, lows, closes, 14)
            
            # Calculate average volume (last 100 candles)
            avg_volume = sum(volumes) / len(volumes) if volumes else 0
            
            snapshot = {
                'symbol': symbol,
                'timeframe': timeframe,
                'ohlcv': ohlcv,
                'ticker': ticker,
                'current_price': float(ticker.last),
                'funding_rate': funding_rate,
                'open_interest': open_interest,
                'timestamp': datetime.utcnow(),
                
                # Series data (last 10 points for prompt)
                'price_series': closes,
                'ema20_series': ema20_series,
                'ema50_series': ema50_series,
                'macd_series': macd_series,
                'rsi7_series': rsi7_series,
                'rsi14_series': rsi14_series,
                
                # Technical indicators (current values)
                'technical_indicators': {
                    '5m': {  # Actually using the provided timeframe
                        'ema20': ema20_series[-1] if ema20_series and ema20_series[-1] is not None else 0,
                        'ema50': ema50_series[-1] if ema50_series and ema50_series[-1] is not None else 0,
                        'macd': macd_series[-1] if macd_series and macd_series[-1] is not None else 0,
                        'rsi7': rsi7_series[-1] if rsi7_series and rsi7_series[-1] is not None else 50,
                        'rsi14': rsi14_series[-1] if rsi14_series and rsi14_series[-1] is not None else 50,
                    },
                    '1h': {  # For longer-term context
                        'ema20': 0,  # Will be filled by get_market_data_multi_timeframe
                        'ema50': 0,
                        'macd': 0,
                        'rsi14': 50,
                        'atr3': atr3_series[-1] if atr3_series and atr3_series[-1] is not None else 0,
                        'atr14': atr14_series[-1] if atr14_series and atr14_series[-1] is not None else 0,
                        'volume': volumes[-1] if volumes else 0,
                        'avg_volume': avg_volume,
                    }
                }
            }
            
            logger.info(f"Created market snapshot for {symbol}")
            return snapshot
            
        except Exception as e:
            logger.error(f"Error creating market snapshot: {e}")
            raise
    
    async def get_market_data_multi_timeframe(
        self,
        symbol: str,
        timeframe_short: str = '1h',
        timeframe_long: str = '4h'
    ) -> dict:
        """
        Get market data for multiple timeframes with full series data.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe_short: Short timeframe (default: '1h' which is actually used as 3min proxy)
            timeframe_long: Long timeframe for context (default: '4h')
        
        Returns:
            Dictionary with complete snapshot including 4h series
        """
        logger.debug(f"Fetching multi-timeframe data for {symbol}: {timeframe_short} + {timeframe_long}")
        
        # Fetch short timeframe (existing data with series)
        snapshot = await self.get_market_snapshot(symbol, timeframe_short)
        
        # Fetch long timeframe (4H) and add to snapshot
        try:
            ohlcv_long = await self.fetch_ohlcv(symbol, timeframe_long, limit=100)
            
            if not ohlcv_long:
                logger.warning(f"No data returned for {symbol} on {timeframe_long}")
                return snapshot
            
            # Calculate indicators for 4H
            from .indicator_service import IndicatorService
            
            closes_4h = self.extract_closes(ohlcv_long)
            highs_4h = self.extract_highs(ohlcv_long)
            lows_4h = self.extract_lows(ohlcv_long)
            volumes_4h = self.extract_volumes(ohlcv_long)
            
            # Calculate all 4h indicators with series
            ema20_4h = IndicatorService.calculate_ema(closes_4h, 20)
            ema50_4h = IndicatorService.calculate_ema(closes_4h, 50)
            macd_4h = IndicatorService.calculate_macd(closes_4h)
            rsi14_4h = IndicatorService.calculate_rsi(closes_4h, 14)
            atr3_4h = IndicatorService.calculate_atr(highs_4h, lows_4h, closes_4h, 3)
            atr14_4h = IndicatorService.calculate_atr(highs_4h, lows_4h, closes_4h, 14)
            
            # Calculate average volume
            avg_volume_4h = sum(volumes_4h) / len(volumes_4h) if volumes_4h else 0
            
            # Add 4h series to snapshot
            snapshot['macd_series_4h'] = macd_4h['macd']
            snapshot['rsi14_series_4h'] = rsi14_4h
            
            # Update 1h (4h) technical indicators with actual values
            snapshot['technical_indicators']['1h'] = {
                'ema20': ema20_4h[-1] if ema20_4h and ema20_4h[-1] is not None else 0,
                'ema50': ema50_4h[-1] if ema50_4h and ema50_4h[-1] is not None else 0,
                'macd': macd_4h['macd'][-1] if macd_4h['macd'] and macd_4h['macd'][-1] is not None else 0,
                'rsi14': rsi14_4h[-1] if rsi14_4h and rsi14_4h[-1] is not None else 50,
                'atr3': atr3_4h[-1] if atr3_4h and atr3_4h[-1] is not None else 0,
                'atr14': atr14_4h[-1] if atr14_4h and atr14_4h[-1] is not None else 0,
                'volume': volumes_4h[-1] if volumes_4h else 0,
                'avg_volume': avg_volume_4h,
            }
            
            logger.debug(f"Successfully added {timeframe_long} data to snapshot for {symbol}")
            return snapshot
            
        except Exception as e:
            logger.error(f"Error fetching {timeframe_long} data for {symbol}: {e}")
            # Return snapshot with short timeframe data only
            return snapshot