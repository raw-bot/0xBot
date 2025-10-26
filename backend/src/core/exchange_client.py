"""CCXT Exchange client wrapper for OKX trading."""

import os
from typing import Any, Dict, List, Optional

import ccxt.async_support as ccxt
from decimal import Decimal

from ..core.logger import get_logger

logger = get_logger(__name__)


class ExchangeClient:
    """
    Wrapper for CCXT exchange operations.
    
    Provides unified interface for fetching market data and executing trades.
    """
    
    def __init__(self, paper_trading: bool = True):
        """
        Initialize exchange client.
        
        Args:
            paper_trading: If True, use demo mode
        """
        self.paper_trading = paper_trading
        
        # Get API credentials from environment
        api_key = os.getenv("OKX_API_KEY", "")
        secret_key = os.getenv("OKX_SECRET_KEY", "")
        passphrase = os.getenv("OKX_PASSPHRASE", "")
        
        # Initialize OKX exchange
        # For paper trading, use public API (no authentication needed)
        # Trade execution is simulated by trade_executor_service
        if paper_trading:
            # Paper trading: Use public API only (no authentication)
            exchange_options = {
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'swap',  # Use perpetual swaps (equivalent to futures)
                }
            }
        else:
            # Live trading: Use authenticated API
            exchange_options = {
                'apiKey': api_key,
                'secret': secret_key,
                'password': passphrase,  # OKX requires a passphrase
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'swap',
                }
            }
        
        self.exchange = ccxt.okx(exchange_options)
        
        # In paper trading mode, use real market data but simulate trades
        # The trade_executor_service handles the simulation logic
        if paper_trading:
            logger.info("📝 Exchange client initialized in PAPER TRADING mode (OKX Demo)")
            logger.info("📊 Using real market data, trades will be simulated in database")
        else:
            logger.info("🔴 Exchange client initialized in LIVE TRADING mode (OKX)")
            logger.warning("⚠️  LIVE TRADING: Real orders will be placed on OKX!")
    
    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol for OKX swap markets.
        
        OKX requires format: BTC/USDT:USDT for perpetual swaps
        This converts BTC/USDT -> BTC/USDT:USDT automatically
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            
        Returns:
            Normalized symbol (e.g., 'BTC/USDT:USDT')
        """
        # If symbol already has settle currency, return as is
        if ':' in symbol:
            return symbol
        
        # For OKX swaps, append :USDT for USDT pairs
        if '/USDT' in symbol:
            return f"{symbol}:USDT"
        
        # Return original if not USDT pair
        return symbol
    
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1h',
        limit: int = 100
    ) -> List[List[float]]:
        """
        Fetch OHLCV (candlestick) data.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT' or 'BTC-USDT-SWAP')
            timeframe: Candle timeframe ('1m', '5m', '15m', '1h', '4h', '1d')
            limit: Number of candles to fetch
            
        Returns:
            List of OHLCV data: [[timestamp, open, high, low, close, volume], ...]
        """
        try:
            normalized_symbol = self._normalize_symbol(symbol)
            ohlcv = await self.exchange.fetch_ohlcv(normalized_symbol, timeframe, limit=limit)
            logger.info(f"Fetched {len(ohlcv)} candles for {normalized_symbol} ({timeframe})")
            return ohlcv
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            raise
    
    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch current ticker data.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT' or 'BTC-USDT-SWAP')
            
        Returns:
            Ticker data with current price, volume, etc.
        """
        try:
            normalized_symbol = self._normalize_symbol(symbol)
            ticker = await self.exchange.fetch_ticker(normalized_symbol)
            logger.debug(f"Fetched ticker for {normalized_symbol}: {ticker['last']}")
            return ticker
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            raise
    
    async def create_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        order_type: str = 'market'
    ) -> Dict[str, Any]:
        """
        Create an order.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT' or 'BTC-USDT-SWAP')
            side: 'buy' or 'sell'
            amount: Order amount in base currency
            price: Limit price (for limit orders)
            order_type: 'market' or 'limit'
            
        Returns:
            Order information
        """
        try:
            if order_type == 'market':
                order = await self.exchange.create_market_order(symbol, side, amount)
            else:
                if price is None:
                    raise ValueError("Price required for limit orders")
                order = await self.exchange.create_limit_order(symbol, side, amount, price)
            
            logger.info(f"Created {order_type} {side} order: {symbol} {amount} @ {price or 'market'}")
            return order
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            raise
    
    async def create_stop_loss_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        stop_price: float
    ) -> Dict[str, Any]:
        """
        Create a stop-loss order (OKX-compatible).
        
        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Order amount
            stop_price: Stop trigger price
            
        Returns:
            Order information
        """
        try:
            # OKX uses 'trigger' order type with specific parameters
            params = {
                'triggerPrice': stop_price,  # OKX uses triggerPrice instead of stopPrice
                'orderType': 'market',
                'triggerType': 'last',  # Trigger based on last price
            }
            order = await self.exchange.create_order(
                symbol,
                'trigger',  # OKX trigger order type
                side,
                amount,
                params=params
            )
            logger.info(f"Created stop-loss order: {symbol} {amount} @ {stop_price}")
            return order
        except Exception as e:
            logger.error(f"Error creating stop-loss order: {e}")
            raise
    
    async def create_take_profit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        take_profit_price: float
    ) -> Dict[str, Any]:
        """
        Create a take-profit order (OKX-compatible).
        
        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Order amount
            take_profit_price: Take profit trigger price
            
        Returns:
            Order information
        """
        try:
            # OKX uses 'trigger' order type with specific parameters
            params = {
                'triggerPrice': take_profit_price,  # OKX uses triggerPrice
                'orderType': 'market',
                'triggerType': 'last',  # Trigger based on last price
            }
            order = await self.exchange.create_order(
                symbol,
                'trigger',  # OKX trigger order type
                side,
                amount,
                params=params
            )
            logger.info(f"Created take-profit order: {symbol} {amount} @ {take_profit_price}")
            return order
        except Exception as e:
            logger.error(f"Error creating take-profit order: {e}")
            raise
    
    async def fetch_balance(self) -> Dict[str, Any]:
        """
        Fetch account balance.
        
        Returns:
            Balance information
        """
        try:
            balance = await self.exchange.fetch_balance()
            logger.debug("Fetched account balance")
            return balance
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            raise
    
    async def fetch_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch open positions.
        
        Args:
            symbol: Optional symbol to filter positions
            
        Returns:
            List of open positions
        """
        try:
            positions = await self.exchange.fetch_positions(symbol)
            # Filter out positions with zero contracts
            open_positions = [p for p in positions if float(p.get('contracts', 0)) > 0]
            logger.info(f"Fetched {len(open_positions)} open positions")
            return open_positions
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            raise
    
    async def get_funding_rate(self, symbol: str) -> float:
        """
        Get current funding rate for perpetual swaps (OKX-compatible).
        
        Args:
            symbol: Trading pair
            
        Returns:
            Current funding rate
        """
        try:
            normalized_symbol = self._normalize_symbol(symbol)
            funding_rate = await self.exchange.fetch_funding_rate(normalized_symbol)
            # OKX may use different field names, try multiple possibilities
            rate = float(
                funding_rate.get('fundingRate',
                funding_rate.get('rate',
                funding_rate.get('fundingRateValue', 0)))
            )
            logger.debug(f"Funding rate for {normalized_symbol}: {rate}")
            return rate
        except Exception as e:
            logger.error(f"Error fetching funding rate for {normalized_symbol}: {e}")
            logger.debug(f"Funding rate response structure: {funding_rate if 'funding_rate' in locals() else 'N/A'}")
            return 0.0
    
    async def close(self) -> None:
        """Close exchange connection."""
        await self.exchange.close()
        logger.info("Exchange connection closed")


# Global exchange client instance
_exchange_client: Optional[ExchangeClient] = None


def get_exchange_client(paper_trading: bool = True) -> ExchangeClient:
    """
    Get or create exchange client instance.
    
    Args:
        paper_trading: If True, use demo mode
        
    Returns:
        ExchangeClient instance
    """
    global _exchange_client
    
    if _exchange_client is None:
        _exchange_client = ExchangeClient(paper_trading=paper_trading)
    
    return _exchange_client