"""Tests for market data service."""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from src.services.market_data_service import (
    MarketDataService,
    OHLCV,
    Ticker,
    _safe_decimal,
    _get_last_valid,
)
from src.services.indicator_service import IndicatorService


class TestSafeDecimal:
    """Tests for _safe_decimal helper function."""

    def test_safe_decimal_valid_float(self):
        """Test converting valid float to Decimal."""
        result = _safe_decimal(123.45)
        assert result == Decimal("123.45")

    def test_safe_decimal_valid_string(self):
        """Test converting valid string to Decimal."""
        result = _safe_decimal("456.78")
        assert result == Decimal("456.78")

    def test_safe_decimal_none_returns_default(self):
        """Test None value returns default."""
        result = _safe_decimal(None, "100")
        assert result == Decimal("100")

    def test_safe_decimal_empty_string_returns_default(self):
        """Test empty string returns default."""
        result = _safe_decimal("", "50")
        assert result == Decimal("50")

    def test_safe_decimal_none_string_returns_default(self):
        """Test 'None' string returns default."""
        result = _safe_decimal("None", "75")
        assert result == Decimal("75")

    def test_safe_decimal_invalid_value_returns_default(self):
        """Test invalid value returns default."""
        result = _safe_decimal("invalid", "0")
        assert result == Decimal("0")

    def test_safe_decimal_none_with_no_default(self):
        """Test None with no default returns None."""
        result = _safe_decimal(None, None)
        assert result is None

    def test_safe_decimal_zero(self):
        """Test zero value."""
        result = _safe_decimal(0)
        assert result == Decimal("0")


class TestGetLastValid:
    """Tests for _get_last_valid helper function."""

    def test_get_last_valid_with_values(self):
        """Test getting last value from list with values."""
        result = _get_last_valid([1.0, 2.0, 3.0, 4.0])
        assert result == 4.0

    def test_get_last_valid_with_none_at_end(self):
        """Test getting last non-None value when None at end."""
        result = _get_last_valid([1.0, 2.0, 3.0, None, None])
        assert result == 3.0

    def test_get_last_valid_all_none(self):
        """Test all None values returns None."""
        result = _get_last_valid([None, None, None])
        assert result is None

    def test_get_last_valid_empty_list(self):
        """Test empty list returns None."""
        result = _get_last_valid([])
        assert result is None

    def test_get_last_valid_single_value(self):
        """Test single value in list."""
        result = _get_last_valid([42.0])
        assert result == 42.0


class TestOHLCV:
    """Tests for OHLCV candlestick class."""

    def test_ohlcv_initialization(self):
        """Test OHLCV initialization with valid data."""
        timestamp = 1704067200000  # 2024-01-01 00:00:00
        candle = OHLCV(timestamp, 45000.5, 46000.0, 44500.25, 45500.75, 1000.5)

        assert candle.timestamp == timestamp
        assert candle.open == Decimal("45000.5")
        assert candle.high == Decimal("46000.0")
        assert candle.low == Decimal("44500.25")
        assert candle.close == Decimal("45500.75")
        assert candle.volume == Decimal("1000.5")

    def test_ohlcv_datetime_conversion(self):
        """Test OHLCV datetime conversion from timestamp."""
        timestamp = 1704067200000  # 2024-01-01 00:00:00
        candle = OHLCV(timestamp, 100, 110, 90, 105, 1000)

        # Verify datetime is properly converted
        assert isinstance(candle.datetime, datetime)
        assert candle.datetime.year == 2024
        assert candle.datetime.month == 1
        assert candle.datetime.day == 1

    def test_ohlcv_repr(self):
        """Test OHLCV string representation."""
        timestamp = 1704067200000
        candle = OHLCV(timestamp, 45000, 46000, 44500, 45500, 1000)
        repr_str = repr(candle)

        assert "OHLCV" in repr_str
        assert "45000" in repr_str
        assert "45500" in repr_str


class TestTicker:
    """Tests for Ticker class."""

    def test_ticker_initialization_full_data(self):
        """Test Ticker initialization with complete data."""
        data = {
            "symbol": "BTC/USDT",
            "last": 45000.5,
            "bid": 45000.0,
            "ask": 45001.0,
            "baseVolume": 1000.0,
            "quoteVolume": 45000000.0,
            "high": 46000.0,
            "low": 44000.0,
            "change": 500.0,
            "percentage": 1.11,
            "timestamp": 1704067200000,
        }
        ticker = Ticker(data)

        assert ticker.symbol == "BTC/USDT"
        assert ticker.last == Decimal("45000.5")
        assert ticker.bid == Decimal("45000.0")
        assert ticker.ask == Decimal("45001.0")
        assert ticker.volume == Decimal("1000.0")
        assert ticker.quote_volume == Decimal("45000000.0")
        assert ticker.high == Decimal("46000.0")
        assert ticker.low == Decimal("44000.0")
        assert ticker.change == Decimal("500.0")
        assert ticker.percentage == Decimal("1.11")

    def test_ticker_initialization_minimal_data(self):
        """Test Ticker initialization with minimal data."""
        data = {"symbol": "ETH/USDT"}
        ticker = Ticker(data)

        assert ticker.symbol == "ETH/USDT"
        assert ticker.last == Decimal("0")
        assert ticker.bid is None
        assert ticker.ask is None
        assert ticker.volume == Decimal("0")

    def test_ticker_volume_fallback_to_volume(self):
        """Test Ticker uses 'volume' if 'baseVolume' not present."""
        data = {"symbol": "BTC/USDT", "volume": 500.0, "last": 45000}
        ticker = Ticker(data)

        assert ticker.volume == Decimal("500.0")

    def test_ticker_missing_timestamp(self):
        """Test Ticker with missing timestamp returns None datetime."""
        data = {"symbol": "BTC/USDT", "last": 45000}
        ticker = Ticker(data)

        assert ticker.timestamp == 0
        assert ticker.datetime is None

    def test_ticker_repr(self):
        """Test Ticker string representation."""
        data = {"symbol": "BTC/USDT", "last": 45000.5, "baseVolume": 1000}
        ticker = Ticker(data)
        repr_str = repr(ticker)

        assert "Ticker" in repr_str
        assert "BTC/USDT" in repr_str


class TestMarketDataService:
    """Tests for MarketDataService."""

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_success(self, mock_exchange):
        """Test successful OHLCV data fetching."""
        # Mock exchange response
        mock_exchange.fetch_ohlcv.return_value = [
            [1704067200000, 45000, 46000, 44500, 45500, 1000],
            [1704070800000, 45500, 46500, 45000, 46000, 1200],
            [1704074400000, 46000, 46500, 45500, 46200, 1100],
        ]

        service = MarketDataService(mock_exchange)
        result = await service.fetch_ohlcv("BTC/USDT", "1h", 3)

        assert len(result) == 3
        assert all(isinstance(candle, OHLCV) for candle in result)
        assert result[0].close == Decimal("45500")
        assert result[1].close == Decimal("46000")
        assert result[2].close == Decimal("46200")
        mock_exchange.fetch_ohlcv.assert_called_once_with("BTC/USDT", "1h", 3)

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_error_handling(self, mock_exchange):
        """Test OHLCV fetch error handling."""
        mock_exchange.fetch_ohlcv.side_effect = Exception("API Error")

        service = MarketDataService(mock_exchange)

        with pytest.raises(Exception, match="API Error"):
            await service.fetch_ohlcv("INVALID/USDT", "1h", 100)

    @pytest.mark.asyncio
    async def test_fetch_ticker_success(self, mock_exchange):
        """Test successful ticker data fetching."""
        mock_exchange.fetch_ticker.return_value = {
            "symbol": "BTC/USDT",
            "last": 45000.5,
            "bid": 45000.0,
            "ask": 45001.0,
            "baseVolume": 1000.0,
            "high": 46000.0,
            "low": 44000.0,
            "timestamp": 1704067200000,
        }

        service = MarketDataService(mock_exchange)
        result = await service.fetch_ticker("BTC/USDT")

        assert isinstance(result, Ticker)
        assert result.symbol == "BTC/USDT"
        assert result.last == Decimal("45000.5")
        mock_exchange.fetch_ticker.assert_called_once_with("BTC/USDT")

    @pytest.mark.asyncio
    async def test_fetch_ticker_missing_last_price(self, mock_exchange):
        """Test ticker fetch with missing last price."""
        mock_exchange.fetch_ticker.return_value = {
            "symbol": "BTC/USDT",
            "bid": 45000.0,
            "ask": 45001.0,
        }

        service = MarketDataService(mock_exchange)
        result = await service.fetch_ticker("BTC/USDT")

        assert isinstance(result, Ticker)
        assert result.last == Decimal("0")

    @pytest.mark.asyncio
    async def test_fetch_ticker_error_handling(self, mock_exchange):
        """Test ticker fetch error handling."""
        mock_exchange.fetch_ticker.side_effect = Exception("API Error")

        service = MarketDataService(mock_exchange)

        with pytest.raises(Exception, match="API Error"):
            await service.fetch_ticker("INVALID/USDT")

    @pytest.mark.asyncio
    async def test_get_current_price(self, mock_exchange):
        """Test getting current price."""
        mock_exchange.fetch_ticker.return_value = {
            "symbol": "BTC/USDT",
            "last": 45000.5,
        }

        service = MarketDataService(mock_exchange)
        price = await service.get_current_price("BTC/USDT")

        assert price == Decimal("45000.5")

    @pytest.mark.asyncio
    async def test_get_funding_rate_success(self, mock_exchange):
        """Test successful funding rate fetch."""
        mock_exchange.get_funding_rate.return_value = 0.0001

        service = MarketDataService(mock_exchange)
        rate = await service.get_funding_rate("BTC/USDT")

        assert rate == 0.0001
        mock_exchange.get_funding_rate.assert_called_once_with("BTC/USDT")

    @pytest.mark.asyncio
    async def test_get_funding_rate_error_returns_zero(self, mock_exchange):
        """Test funding rate error returns zero."""
        mock_exchange.get_funding_rate.side_effect = Exception("API Error")

        service = MarketDataService(mock_exchange)
        rate = await service.get_funding_rate("BTC/USDT")

        assert rate == 0.0
        mock_exchange.get_funding_rate.assert_called_once_with("BTC/USDT")

    @pytest.mark.asyncio
    async def test_get_open_interest_success(self, mock_exchange):
        """Test successful open interest fetch."""
        mock_exchange.fetch_open_interest.return_value = {"openInterest": 1000000.5}

        service = MarketDataService(mock_exchange)
        oi = await service.get_open_interest("BTC/USDT")

        assert oi["latest"] == 1000000.5
        assert oi["average"] == 1000000.5

    @pytest.mark.asyncio
    async def test_get_open_interest_error_returns_zeros(self, mock_exchange):
        """Test open interest error returns zeros."""
        mock_exchange.fetch_open_interest.side_effect = Exception("API Error")

        service = MarketDataService(mock_exchange)
        oi = await service.get_open_interest("BTC/USDT")

        assert oi["latest"] == 0
        assert oi["average"] == 0

    def test_extract_closes(self, mock_exchange):
        """Test extracting closing prices from OHLCV."""
        ohlcv = [
            OHLCV(1704067200000, 45000, 46000, 44500, 45500, 1000),
            OHLCV(1704070800000, 45500, 46500, 45000, 46000, 1200),
            OHLCV(1704074400000, 46000, 46500, 45500, 46200, 1100),
        ]

        service = MarketDataService(mock_exchange)
        closes = service.extract_closes(ohlcv)

        assert len(closes) == 3
        assert closes[0] == 45500.0
        assert closes[1] == 46000.0
        assert closes[2] == 46200.0

    def test_extract_highs(self, mock_exchange):
        """Test extracting high prices from OHLCV."""
        ohlcv = [
            OHLCV(1704067200000, 45000, 46000, 44500, 45500, 1000),
            OHLCV(1704070800000, 45500, 46500, 45000, 46000, 1200),
        ]

        service = MarketDataService(mock_exchange)
        highs = service.extract_highs(ohlcv)

        assert highs == [46000.0, 46500.0]

    def test_extract_lows(self, mock_exchange):
        """Test extracting low prices from OHLCV."""
        ohlcv = [
            OHLCV(1704067200000, 45000, 46000, 44500, 45500, 1000),
            OHLCV(1704070800000, 45500, 46500, 45000, 46000, 1200),
        ]

        service = MarketDataService(mock_exchange)
        lows = service.extract_lows(ohlcv)

        assert lows == [44500.0, 45000.0]

    def test_extract_volumes(self, mock_exchange):
        """Test extracting volumes from OHLCV."""
        ohlcv = [
            OHLCV(1704067200000, 45000, 46000, 44500, 45500, 1000),
            OHLCV(1704070800000, 45500, 46500, 45000, 46000, 1500),
        ]

        service = MarketDataService(mock_exchange)
        volumes = service.extract_volumes(ohlcv)

        assert volumes == [1000.0, 1500.0]

    @pytest.mark.asyncio
    async def test_get_market_snapshot_success(self, mock_exchange):
        """Test getting complete market snapshot."""
        # Mock OHLCV data
        mock_exchange.fetch_ohlcv.return_value = [
            [1704067200000, 45000, 46000, 44500, 45500, 1000],
            [1704070800000, 45500, 46500, 45000, 46000, 1200],
            [1704074400000, 46000, 46500, 45500, 46200, 1100],
        ]

        # Mock ticker data
        mock_exchange.fetch_ticker.return_value = {
            "symbol": "BTC/USDT",
            "last": 46200.0,
        }

        # Mock funding rate
        mock_exchange.get_funding_rate.return_value = 0.0001

        # Mock open interest
        mock_exchange.fetch_open_interest.return_value = {"openInterest": 1000000}

        service = MarketDataService(mock_exchange)
        snapshot = await service.get_market_snapshot("BTC/USDT", "1h")

        assert snapshot["symbol"] == "BTC/USDT"
        assert snapshot["timeframe"] == "1h"
        assert snapshot["current_price"] == 46200.0
        assert snapshot["funding_rate"] == 0.0001
        assert snapshot["open_interest"]["latest"] == 1000000
        assert "ohlcv" in snapshot
        assert "ticker" in snapshot
        assert "price_series" in snapshot
        assert "ema20_series" in snapshot
        assert "ema50_series" in snapshot
        assert "rsi7_series" in snapshot
        assert "rsi14_series" in snapshot
        assert "macd_series" in snapshot
        assert "technical_indicators" in snapshot

    @pytest.mark.asyncio
    async def test_get_market_snapshot_error_handling(self, mock_exchange):
        """Test market snapshot error handling."""
        mock_exchange.fetch_ohlcv.side_effect = Exception("API Error")

        service = MarketDataService(mock_exchange)

        with pytest.raises(Exception, match="API Error"):
            await service.get_market_snapshot("BTC/USDT")

    @pytest.mark.asyncio
    async def test_get_market_data_multi_timeframe_success(self, mock_exchange):
        """Test getting multi-timeframe market data."""
        # Mock 1h OHLCV
        mock_exchange.fetch_ohlcv.side_effect = [
            [  # 1h data
                [1704067200000, 45000, 46000, 44500, 45500, 1000],
                [1704070800000, 45500, 46500, 45000, 46000, 1200],
                [1704074400000, 46000, 46500, 45500, 46200, 1100],
            ],
            [  # 4h data
                [1704067200000, 44500, 46500, 44000, 45500, 4000],
                [1704081600000, 45500, 47000, 45000, 46800, 5000],
            ],
        ]

        # Mock ticker
        mock_exchange.fetch_ticker.return_value = {
            "symbol": "BTC/USDT",
            "last": 46200.0,
        }

        # Mock funding rate
        mock_exchange.get_funding_rate.return_value = 0.0001

        # Mock open interest
        mock_exchange.fetch_open_interest.return_value = {"openInterest": 1000000}

        service = MarketDataService(mock_exchange)
        data = await service.get_market_data_multi_timeframe("BTC/USDT", "1h", "4h")

        assert data["symbol"] == "BTC/USDT"
        assert "macd_series_4h" in data
        assert "rsi14_series_4h" in data
        assert "technical_indicators" in data

    @pytest.mark.asyncio
    async def test_get_market_data_multi_timeframe_no_long_data(self, mock_exchange):
        """Test multi-timeframe with no long data returns short data only."""
        # Mock 1h OHLCV
        mock_exchange.fetch_ohlcv.side_effect = [
            [  # 1h data
                [1704067200000, 45000, 46000, 44500, 45500, 1000],
            ],
            [],  # 4h data is empty
        ]

        # Mock ticker
        mock_exchange.fetch_ticker.return_value = {
            "symbol": "BTC/USDT",
            "last": 45500.0,
        }

        # Mock funding rate
        mock_exchange.get_funding_rate.return_value = 0.0001

        # Mock open interest
        mock_exchange.fetch_open_interest.return_value = {"openInterest": 1000000}

        service = MarketDataService(mock_exchange)
        data = await service.get_market_data_multi_timeframe("BTC/USDT", "1h", "4h")

        assert data["symbol"] == "BTC/USDT"
        assert "macd_series_4h" not in data  # Should not add if no data

    @pytest.mark.asyncio
    async def test_get_market_data_multi_timeframe_error_fallback(self, mock_exchange):
        """Test multi-timeframe error handling falls back to short data."""
        # Mock successful 1h OHLCV
        mock_exchange.fetch_ohlcv.side_effect = [
            [  # 1h data
                [1704067200000, 45000, 46000, 44500, 45500, 1000],
            ],
            Exception("4h fetch failed"),  # 4h fails
        ]

        # Mock ticker
        mock_exchange.fetch_ticker.return_value = {
            "symbol": "BTC/USDT",
            "last": 45500.0,
        }

        # Mock funding rate
        mock_exchange.get_funding_rate.return_value = 0.0001

        # Mock open interest
        mock_exchange.fetch_open_interest.return_value = {"openInterest": 1000000}

        service = MarketDataService(mock_exchange)
        data = await service.get_market_data_multi_timeframe("BTC/USDT", "1h", "4h")

        # Should still have 1h data despite 4h error
        assert data["symbol"] == "BTC/USDT"
        assert "price_series" in data  # 1h data should be present

    def test_extract_closes_empty(self, mock_exchange):
        """Test extract_closes with empty list."""
        service = MarketDataService(mock_exchange)
        closes = service.extract_closes([])

        assert closes == []

    def test_extract_volumes_empty(self, mock_exchange):
        """Test extract_volumes with empty list."""
        service = MarketDataService(mock_exchange)
        volumes = service.extract_volumes([])

        assert volumes == []
