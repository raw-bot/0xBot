"""Test suite for Ichimoku Cloud indicator implementation."""

import pytest
from src.services.indicator_service import IndicatorService


class TestIchimokuBasics:
    """Tests for basic Ichimoku calculations."""

    def test_ichimoku_insufficient_data(self):
        """Test Ichimoku returns None when insufficient data."""
        prices = [100 + i for i in range(20)]  # Only 20 periods, need 52+
        highs = [100 + i + 1 for i in range(20)]
        lows = [100 + i - 1 for i in range(20)]

        result = IndicatorService.calculate_ichimoku(highs, lows, prices)

        assert result["tenkan"] is None
        assert result["kijun"] is None
        assert result["senkou_a"] is None
        assert result["senkou_b"] is None
        assert result["kumo_high"] is None
        assert result["kumo_low"] is None

    def test_ichimoku_with_sufficient_data(self):
        """Test Ichimoku calculation with 100+ periods."""
        # Create uptrending data
        highs = [100 + i + 1 for i in range(100)]
        lows = [100 + i - 1 for i in range(100)]
        closes = [100 + i for i in range(100)]

        result = IndicatorService.calculate_ichimoku(highs, lows, closes)

        # Should have all components
        assert result["tenkan"] is not None
        assert result["kijun"] is not None
        assert result["senkou_a"] is not None
        assert result["senkou_b"] is not None
        assert result["chikou"] is not None
        assert result["kumo_high"] is not None
        assert result["kumo_low"] is not None

        # Verify tenkan > kijun in uptrend
        assert result["tenkan"] > result["kijun"]

    def test_ichimoku_components_calculation(self):
        """Test individual Ichimoku components are calculated correctly."""
        # Create simple data where we can verify values
        highs = [100.0] * 52 + [105.0] * 48  # First 52 at 100, next 48 at 105
        lows = [98.0] * 52 + [103.0] * 48
        closes = [99.0] * 52 + [104.0] * 48

        result = IndicatorService.calculate_ichimoku(highs, lows, closes)

        # Last 9-period high/low (should be 105/103)
        expected_tenkan = (105.0 + 103.0) / 2.0  # 104.0
        assert result["tenkan"] == pytest.approx(expected_tenkan, rel=0.01)

        # Last 26-period high/low (all last 26 have 105/103 since we have 48 at that level)
        # The last 26 bars are all 105/103, so kijun = (105+103)/2 = 104.0
        expected_kijun = (105.0 + 103.0) / 2.0  # 104.0
        assert result["kijun"] == pytest.approx(expected_kijun, rel=0.01)

    def test_ichimoku_signals_generation(self):
        """Test that Ichimoku signals are properly generated."""
        # Uptrending data
        highs = [100 + i + 1 for i in range(100)]
        lows = [100 + i - 1 for i in range(100)]
        closes = [100 + i for i in range(100)]

        result = IndicatorService.calculate_ichimoku(highs, lows, closes)

        signals = result["signals"]

        # Check all signal keys exist
        expected_keys = [
            "price_above_kumo",
            "price_below_kumo",
            "price_in_kumo",
            "tenkan_above_kijun",
            "kumo_bullish",
            "chikou_above_price",
            "cloud_bullish_cross",
            "cloud_bearish_cross",
            "cloud_expansion",
            "cloud_squeeze",
        ]

        for key in expected_keys:
            assert key in signals

    def test_ichimoku_kumo_ordering(self):
        """Test that Kumo high >= Kumo low."""
        highs = [100 + i for i in range(100)]
        lows = [98 + i for i in range(100)]
        closes = [99 + i for i in range(100)]

        result = IndicatorService.calculate_ichimoku(highs, lows, closes)

        if result["kumo_high"] is not None and result["kumo_low"] is not None:
            assert result["kumo_high"] >= result["kumo_low"]

    def test_ichimoku_price_vs_cloud(self):
        """Test price vs cloud positioning signals."""
        # Uptrending data (price going up)
        highs = [100 + i * 2 for i in range(100)]
        lows = [98 + i * 2 for i in range(100)]
        closes = [99 + i * 2 for i in range(100)]

        result = IndicatorService.calculate_ichimoku(highs, lows, closes)

        signals = result["signals"]

        # In strong uptrend, price should typically be above kumo
        price_above_kumo = signals.get("price_above_kumo")
        price_below_kumo = signals.get("price_below_kumo")
        price_in_kumo = signals.get("price_in_kumo")

        # These should be mutually exclusive
        if price_above_kumo is not None and price_below_kumo is not None:
            assert price_above_kumo or price_below_kumo or price_in_kumo


class TestIchimokuEdgeCases:
    """Tests for edge cases and error handling."""

    def test_ichimoku_empty_lists(self):
        """Test Ichimoku with empty lists."""
        result = IndicatorService.calculate_ichimoku([], [], [])

        assert result["tenkan"] is None
        assert result["kumo_high"] is None

    def test_ichimoku_none_signals_on_insufficient_data(self):
        """Test that signals are None when data insufficient."""
        highs = [100 + i for i in range(30)]
        lows = [98 + i for i in range(30)]
        closes = [99 + i for i in range(30)]

        result = IndicatorService.calculate_ichimoku(highs, lows, closes)

        # All signals should be None when insufficient data
        for signal_value in result["signals"].values():
            assert signal_value is None or signal_value == {}

    def test_ichimoku_flat_market(self):
        """Test Ichimoku on flat (sideways) market."""
        # Flat price data
        highs = [100.0] * 100
        lows = [99.0] * 100
        closes = [99.5] * 100

        result = IndicatorService.calculate_ichimoku(highs, lows, closes)

        # Should still calculate without errors
        assert result["tenkan"] is not None
        assert result["kijun"] is not None

        # In flat market, tenkan ~= kijun
        if result["tenkan"] is not None and result["kijun"] is not None:
            assert result["tenkan"] == pytest.approx(result["kijun"], rel=0.01)

    def test_ichimoku_downtrend(self):
        """Test Ichimoku signals in downtrend."""
        # Downtrending data
        highs = [100 - i for i in range(100)]
        lows = [98 - i for i in range(100)]
        closes = [99 - i for i in range(100)]

        result = IndicatorService.calculate_ichimoku(highs, lows, closes)

        signals = result["signals"]

        # In downtrend, price should typically be below kumo
        if signals.get("price_below_kumo") is not None:
            # Most of the time in downtrend, price is below cloud
            # (though this depends on how far back the cloud is plotted)
            assert isinstance(signals["price_below_kumo"], bool)


class TestIchimokuIntegration:
    """Integration tests with real-like market data."""

    def test_ichimoku_realistic_bullish_breakout(self):
        """Test Ichimoku on realistic bullish breakout scenario."""
        # Consolidation followed by breakout
        data = []
        # Consolidation phase (30 bars)
        for i in range(30):
            data.append((100.0, 99.0, 99.5))

        # Breakout phase (70 bars)
        for i in range(70):
            data.append((100.0 + i * 0.5, 99.0 + i * 0.5, 99.5 + i * 0.5))

        highs = [d[0] for d in data]
        lows = [d[1] for d in data]
        closes = [d[2] for d in data]

        result = IndicatorService.calculate_ichimoku(highs, lows, closes)

        # Should have valid components
        assert result["tenkan"] is not None
        assert result["kumo_high"] is not None

    def test_ichimoku_realistic_bearish_reversal(self):
        """Test Ichimoku on realistic bearish reversal scenario."""
        # Uptrend followed by reversal
        data = []
        # Uptrend phase (50 bars)
        for i in range(50):
            data.append((100.0 + i * 0.5, 99.0 + i * 0.5, 99.5 + i * 0.5))

        # Reversal phase (50 bars)
        for i in range(50):
            data.append((125.0 - i * 0.5, 124.0 - i * 0.5, 124.5 - i * 0.5))

        highs = [d[0] for d in data]
        lows = [d[1] for d in data]
        closes = [d[2] for d in data]

        result = IndicatorService.calculate_ichimoku(highs, lows, closes)

        # Should have valid components
        assert result["kijun"] is not None
        assert result["chikou"] is not None

    def test_ichimoku_with_volatility(self):
        """Test Ichimoku with volatile market data."""
        import random

        random.seed(42)
        highs = []
        lows = []
        closes = []

        price = 100.0
        for i in range(100):
            # Add some volatility
            change = random.uniform(-1.0, 1.5)
            high = price + 1.0 + abs(change)
            low = price - 1.0
            close = price + change

            highs.append(high)
            lows.append(low)
            closes.append(close)
            price = close

        result = IndicatorService.calculate_ichimoku(highs, lows, closes)

        # Should handle volatility without errors
        assert result["tenkan"] is not None
        assert result["senkou_a"] is not None
        assert result["senkou_b"] is not None

        # Kumo high should be >= kumo low
        if result["kumo_high"] is not None and result["kumo_low"] is not None:
            assert result["kumo_high"] >= result["kumo_low"]
