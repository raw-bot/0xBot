"""CCXT Exchange client wrapper for OKX trading."""

import os
from typing import Any, Dict, List, Optional, cast

import ccxt.async_support as ccxt  # type: ignore[import-untyped]

from ..core.logger import get_logger

logger = get_logger(__name__)


class ExchangeClient:
    """Wrapper for CCXT exchange operations with unified interface."""

    def __init__(self, paper_trading: bool = True):
        """Initialize exchange client."""
        self.paper_trading = paper_trading

        exchange_options: Dict[str, Any] = {
            "enableRateLimit": True,
            "options": {"defaultType": "swap"},
        }

        if not paper_trading:
            # OKX demo/sandbox credentials - enable sandboxMode
            exchange_options["apiKey"] = os.getenv("OKX_API_KEY", "")
            exchange_options["secret"] = os.getenv("OKX_SECRET_KEY", "")
            exchange_options["password"] = os.getenv("OKX_PASSPHRASE", "")
            cast(Dict[str, Any], exchange_options["options"])["sandboxMode"] = True

        self.exchange = ccxt.okx(exchange_options)

        mode = "PAPER TRADING (Local)" if paper_trading else "LIVE TRADING (OKX Sandbox Demo)"
        logger.info(f"Exchange client initialized in {mode} mode")

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol for OKX swap markets (BTC/USDT -> BTC/USDT:USDT)."""
        if ":" in symbol:
            return symbol
        if "/USDT" in symbol:
            return f"{symbol}:USDT"
        return symbol

    async def fetch_ohlcv(
        self, symbol: str, timeframe: str = "1h", limit: int = 100
    ) -> List[List[float]]:
        """Fetch OHLCV candlestick data."""
        try:
            normalized_symbol = self._normalize_symbol(symbol)
            return cast(List[List[float]], await self.exchange.fetch_ohlcv(normalized_symbol, timeframe, limit=limit))
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            raise

    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch current ticker data."""
        try:
            normalized_symbol = self._normalize_symbol(symbol)
            ticker = cast(Dict[str, Any], await self.exchange.fetch_ticker(normalized_symbol))
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
        order_type: str = "market",
    ) -> Dict[str, Any]:
        """Create a market or limit order."""
        try:
            if order_type == "market":
                order = cast(Dict[str, Any], await self.exchange.create_market_order(symbol, side, amount))
            else:
                if price is None:
                    raise ValueError("Price required for limit orders")
                order = cast(Dict[str, Any], await self.exchange.create_limit_order(symbol, side, amount, price))

            logger.info(f"Created {order_type} {side} order: {symbol} {amount} @ {price or 'market'}")
            return order
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            raise

    async def _create_trigger_order(
        self, symbol: str, side: str, amount: float, trigger_price: float, order_name: str
    ) -> Dict[str, Any]:
        """Create a trigger order (stop-loss or take-profit)."""
        try:
            params = {
                "triggerPrice": trigger_price,
                "orderType": "market",
                "triggerType": "last",
            }
            order = cast(Dict[str, Any], await self.exchange.create_order(symbol, "trigger", side, amount, params=params))
            logger.info(f"Created {order_name} order: {symbol} {amount} @ {trigger_price}")
            return order
        except Exception as e:
            logger.error(f"Error creating {order_name} order: {e}")
            raise

    async def create_stop_loss_order(
        self, symbol: str, side: str, amount: float, stop_price: float
    ) -> Dict[str, Any]:
        """Create a stop-loss order."""
        return await self._create_trigger_order(symbol, side, amount, stop_price, "stop-loss")

    async def create_take_profit_order(
        self, symbol: str, side: str, amount: float, take_profit_price: float
    ) -> Dict[str, Any]:
        """Create a take-profit order."""
        return await self._create_trigger_order(symbol, side, amount, take_profit_price, "take-profit")

    async def fetch_balance(self) -> Dict[str, Any]:
        """Fetch account balance."""
        try:
            balance = cast(Dict[str, Any], await self.exchange.fetch_balance())
            logger.debug("Fetched account balance")
            return balance
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            raise

    async def fetch_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch open positions."""
        try:
            positions = await self.exchange.fetch_positions(symbol)
            open_positions = [p for p in positions if float(p.get("contracts", 0)) > 0]
            logger.info(f"Fetched {len(open_positions)} open positions")
            return open_positions
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            raise

    async def get_funding_rate(self, symbol: str) -> float:
        """Get current funding rate for perpetual swaps."""
        normalized_symbol = self._normalize_symbol(symbol)
        try:
            funding_rate = await self.exchange.fetch_funding_rate(normalized_symbol)
            rate = float(
                funding_rate.get("fundingRate")
                or funding_rate.get("rate")
                or funding_rate.get("fundingRateValue", 0)
            )
            logger.debug(f"Funding rate for {normalized_symbol}: {rate}")
            return rate
        except Exception as e:
            logger.error(f"Error fetching funding rate for {normalized_symbol}: {e}")
            return 0.0

    async def close(self) -> None:
        """Close exchange connection."""
        await self.exchange.close()
        logger.info("Exchange connection closed")


_exchange_client: Optional[ExchangeClient] = None
_exchange_client_mode: Optional[bool] = None


def get_exchange_client(paper_trading: bool = True) -> ExchangeClient:
    """Get or create exchange client instance.

    Note: Once created with a specific mode, the client is cached.
    If you need to switch modes, you must explicitly recreate.
    """
    global _exchange_client, _exchange_client_mode

    # If we have a cached client and it matches the requested mode, return it
    if _exchange_client is not None and _exchange_client_mode == paper_trading:
        return _exchange_client

    # If mode mismatch, recreate the client
    if _exchange_client is not None and _exchange_client_mode != paper_trading:
        logger.info(f"Recreating exchange client (mode change: {_exchange_client_mode} -> {paper_trading})")

    _exchange_client = ExchangeClient(paper_trading=paper_trading)
    _exchange_client_mode = paper_trading
    return _exchange_client
