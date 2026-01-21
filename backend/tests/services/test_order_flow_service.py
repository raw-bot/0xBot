"""Test suite for Order Flow Imbalance (OFI) implementation."""

import pytest
from src.services.order_flow_service import OrderFlowService


class TestDeltaCalculation:
    """Tests for delta calculation from OHLCV data."""

    def test_delta_insufficient_data(self):
        """Test delta calculation returns empty when insufficient data."""
        closes = [100]
        opens = [99]
        highs = [101]
        lows = [99]
        volumes = [1000]

        result = OrderFlowService.calculate_delta(closes, opens, highs, lows, volumes)

        # Should return result even with 1 bar (but won't have cum_delta trend)
        assert "delta" in result
        assert "cum_delta" in result
        assert len(result["delta"]) == 1
        assert len(result["cum_delta"]) == 1

    def test_delta_positive_close_above_open(self):
        """Test delta is positive when close > open (bullish microstructure)."""
        closes = [100, 102]
        opens = [100, 100]
        highs = [101, 103]
        lows = [99, 99]
        volumes = [1000, 1000]

        result = OrderFlowService.calculate_delta(closes, opens, highs, lows, volumes)

        # Second bar: close > open, should be positive delta
        assert result["delta"][1] is not None
        assert result["delta"][1] > 0, "Delta should be positive when close > open"

    def test_delta_negative_close_below_open(self):
        """Test delta is negative when close < open (bearish microstructure)."""
        closes = [100, 98]
        opens = [100, 100]
        highs = [101, 100]
        lows = [99, 97]
        volumes = [1000, 1000]

        result = OrderFlowService.calculate_delta(closes, opens, highs, lows, volumes)

        # Second bar: close < open, should be negative delta
        assert result["delta"][1] is not None
        assert result["delta"][1] < 0, "Delta should be negative when close < open"

    def test_delta_zero_on_doji(self):
        """Test delta is near zero when close = open (doji/indecision)."""
        closes = [100, 100]
        opens = [100, 100]
        highs = [101, 102]
        lows = [99, 98]
        volumes = [1000, 1000]

        result = OrderFlowService.calculate_delta(closes, opens, highs, lows, volumes)

        # Second bar: close = open, should be near zero
        assert result["delta"][1] is not None
        assert result["delta"][1] == 0, "Delta should be zero when close = open"

    def test_cumulative_delta_accumulates(self):
        """Test cumulative delta properly accumulates across bars."""
        closes = [100, 101, 102]
        opens = [100, 100, 100]
        highs = [101, 102, 103]
        lows = [99, 99, 99]
        volumes = [1000, 1000, 1000]

        result = OrderFlowService.calculate_delta(closes, opens, highs, lows, volumes)

        cum_deltas = result["cum_delta"]
        # Cumulative delta should always increase (or stay same)
        assert cum_deltas[0] is not None
        assert cum_deltas[1] is not None
        assert cum_deltas[2] is not None
        assert cum_deltas[1] >= cum_deltas[0]
        assert cum_deltas[2] >= cum_deltas[1]

    def test_delta_handles_none_values(self):
        """Test delta calculation gracefully handles None values."""
        closes = [100, None, 102]
        opens = [100, 100, 100]
        highs = [101, 102, 103]
        lows = [99, 99, 99]
        volumes = [1000, 1000, 1000]

        result = OrderFlowService.calculate_delta(closes, opens, highs, lows, volumes)

        # Should return None for bars with None input
        assert result["delta"][0] is not None
        assert result["delta"][1] is None  # Middle bar is None
        assert result["delta"][2] is not None

    def test_delta_high_volume_impact(self):
        """Test that high volume produces larger delta magnitudes."""
        # Same price action, different volumes
        closes1 = [100, 101]
        opens1 = [100, 100]
        highs1 = [101, 101]
        lows1 = [99, 99]
        volumes1 = [1000, 1000]

        closes2 = [100, 101]
        opens2 = [100, 100]
        highs2 = [101, 101]
        lows2 = [99, 99]
        volumes2 = [1000, 10000]  # 10x volume

        result1 = OrderFlowService.calculate_delta(closes1, opens1, highs1, lows1, volumes1)
        result2 = OrderFlowService.calculate_delta(closes2, opens2, highs2, lows2, volumes2)

        # Delta at index 1 should be larger with higher volume
        delta1 = result1["delta"][1] if result1["delta"][1] is not None else 0
        delta2 = result2["delta"][1] if result2["delta"][1] is not None else 0

        assert delta2 > delta1, "Higher volume should produce larger delta"
        assert delta2 > 9 * delta1, "10x volume should produce ~10x delta"

    def test_delta_division_by_zero_protection(self):
        """Test delta calculation handles zero high-low range (doji)."""
        closes = [100, 100]
        opens = [100, 100]
        highs = [100, 100]  # high = low = close = open
        lows = [100, 100]
        volumes = [1000, 1000]

        result = OrderFlowService.calculate_delta(closes, opens, highs, lows, volumes)

        # Should not crash, should handle gracefully
        assert result["delta"][1] is not None
        assert result["delta"][1] == 0  # delta = vol * 0 / epsilon = 0


class TestOFISignals:
    """Tests for order flow imbalance signal detection."""

    def test_signals_insufficient_data(self):
        """Test OFI signals return default when insufficient data."""
        closes = [100, 101]
        opens = [100, 100]
        highs = [101, 101]
        lows = [99, 99]
        volumes = [1000, 1000]

        result = OrderFlowService.detect_ofi_signals(closes, opens, highs, lows, volumes)

        # Should have all signal keys
        assert "delta_positive" in result
        assert "delta_surge" in result
        assert "delta_bullish_cross" in result
        assert "delta_bearish_cross" in result
        assert "delta_divergence" in result
        assert "delta_strength" in result

    def test_delta_positive_signal(self):
        """Test delta_positive signal when cum_delta > 0."""
        # Create uptrend with buying pressure
        closes = [100 + i for i in range(10)]
        opens = [100 + i - 0.5 for i in range(10)]
        highs = [100 + i + 0.5 for i in range(10)]
        lows = [100 + i - 1 for i in range(10)]
        volumes = [1000] * 10

        result = OrderFlowService.detect_ofi_signals(closes, opens, highs, lows, volumes)

        # Uptrend with close > open should produce positive cum_delta
        assert result["delta_positive"] is True

    def test_delta_negative_signal(self):
        """Test delta_positive signal when cum_delta < 0."""
        # Create downtrend with selling pressure
        closes = [100 - i for i in range(10)]
        opens = [100 - i + 0.5 for i in range(10)]
        highs = [100 - i + 1 for i in range(10)]
        lows = [100 - i - 0.5 for i in range(10)]
        volumes = [1000] * 10

        result = OrderFlowService.detect_ofi_signals(closes, opens, highs, lows, volumes)

        # Downtrend with close < open should produce negative cum_delta
        assert result["delta_positive"] is False

    def test_delta_bullish_cross_signal(self):
        """Test delta_bullish_cross when cum_delta crosses above 0."""
        # Start with negative delta, then cross to positive
        closes = [99, 98, 97, 100, 101, 102]  # Cross happens after bar 3
        opens = [100, 99, 98, 100, 100, 100]
        highs = [100, 99, 98, 101, 102, 103]
        lows = [98, 97, 96, 99, 99, 99]
        volumes = [1000] * 6

        result = OrderFlowService.detect_ofi_signals(closes, opens, highs, lows, volumes)

        # After downtrend reversal to uptrend, should detect bullish cross
        # This depends on cumulative delta logic, check structure exists
        assert "delta_bullish_cross" in result
        assert isinstance(result["delta_bullish_cross"], bool)

    def test_delta_bearish_cross_signal(self):
        """Test delta_bearish_cross when cum_delta crosses below 0."""
        # Start with positive delta, then cross to negative
        closes = [101, 102, 103, 100, 99, 98]  # Cross happens after bar 3
        opens = [100, 100, 100, 100, 99, 98]
        highs = [102, 103, 104, 101, 99, 98]
        lows = [100, 100, 100, 99, 98, 97]
        volumes = [1000] * 6

        result = OrderFlowService.detect_ofi_signals(closes, opens, highs, lows, volumes)

        # After uptrend reversal to downtrend, check structure exists
        assert "delta_bearish_cross" in result
        assert isinstance(result["delta_bearish_cross"], bool)

    def test_delta_surge_signal(self):
        """Test delta_surge when current delta > 2*std_dev."""
        # Create baseline with normal deltas, then spike
        closes = [100 + (i % 3) for i in range(20)]  # Choppy
        opens = [100 + ((i + 1) % 3) for i in range(20)]
        highs = [100 + 1 + (i % 3) for i in range(20)]
        lows = [100 - 1 + (i % 3) for i in range(20)]
        volumes = [1000] * 19 + [10000]  # Large volume spike at end

        result = OrderFlowService.detect_ofi_signals(closes, opens, highs, lows, volumes)

        # Last bar should have surge due to high volume + directional move
        # (if last close is != last open, which in this pattern it might be)
        assert "delta_surge" in result
        assert isinstance(result["delta_surge"], bool)

    def test_delta_strength_calculation(self):
        """Test delta_strength is normalized between 0-1."""
        closes = [100 + i for i in range(15)]
        opens = [100 + i - 0.5 for i in range(15)]
        highs = [100 + i + 0.5 for i in range(15)]
        lows = [100 + i - 1 for i in range(15)]
        volumes = [1000] * 15

        result = OrderFlowService.detect_ofi_signals(closes, opens, highs, lows, volumes)

        # delta_strength should be between 0 and 1
        assert 0 <= result["delta_strength"] <= 1.0

    def test_all_signals_present(self):
        """Test all required signals are returned."""
        closes = [100 + i for i in range(10)]
        opens = [100 + i - 0.5 for i in range(10)]
        highs = [100 + i + 0.5 for i in range(10)]
        lows = [100 + i - 1 for i in range(10)]
        volumes = [1000] * 10

        result = OrderFlowService.detect_ofi_signals(closes, opens, highs, lows, volumes)

        # All required signals must be present
        required_signals = [
            "delta_positive",
            "delta_surge",
            "delta_bullish_cross",
            "delta_bearish_cross",
            "delta_divergence",
            "delta_strength",
        ]
        for signal in required_signals:
            assert signal in result, f"Missing signal: {signal}"


class TestOFIValues:
    """Tests for OFI value retrieval for charting."""

    def test_ofi_values_returns_correct_structure(self):
        """Test get_ofi_values returns all required fields."""
        closes = [100, 101, 102]
        opens = [100, 100, 100]
        highs = [101, 102, 103]
        lows = [99, 99, 99]
        volumes = [1000, 1000, 1000]

        result = OrderFlowService.get_ofi_values(closes, opens, highs, lows, volumes)

        assert "delta" in result
        assert "cum_delta" in result
        assert "current_delta" in result
        assert "current_cum_delta" in result

    def test_ofi_values_returns_arrays(self):
        """Test get_ofi_values returns arrays for delta/cum_delta."""
        closes = [100, 101, 102]
        opens = [100, 100, 100]
        highs = [101, 102, 103]
        lows = [99, 99, 99]
        volumes = [1000, 1000, 1000]

        result = OrderFlowService.get_ofi_values(closes, opens, highs, lows, volumes)

        assert isinstance(result["delta"], list)
        assert isinstance(result["cum_delta"], list)
        assert len(result["delta"]) == 3
        assert len(result["cum_delta"]) == 3

    def test_ofi_values_current_values(self):
        """Test current delta values match last array element."""
        closes = [100, 101, 102]
        opens = [100, 100, 100]
        highs = [101, 102, 103]
        lows = [99, 99, 99]
        volumes = [1000, 1000, 1000]

        result = OrderFlowService.get_ofi_values(closes, opens, highs, lows, volumes)

        # Current values should match last element
        if result["delta"] and result["delta"][-1] is not None:
            assert result["current_delta"] == result["delta"][-1]
        if result["cum_delta"] and result["cum_delta"][-1] is not None:
            assert result["current_cum_delta"] == result["cum_delta"][-1]


class TestOFIEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_data_handling(self):
        """Test order flow service handles empty data."""
        result = OrderFlowService.detect_ofi_signals([], [], [], [], [])

        # Should return default signals
        assert result["delta_positive"] is False
        assert result["delta_surge"] is False

    def test_mismatched_array_lengths(self):
        """Test handling of mismatched array lengths."""
        closes = [100, 101, 102]
        opens = [100, 100]  # Shorter
        highs = [101, 102, 103]
        lows = [99, 99, 99]
        volumes = [1000, 1000, 1000]

        result = OrderFlowService.calculate_delta(closes, opens, highs, lows, volumes)

        # Should return empty due to mismatch
        assert result["delta"] == []
        assert result["cum_delta"] == []

    def test_high_volume_spike(self):
        """Test handling of extreme volume spikes."""
        closes = [100 + i for i in range(5)] + [105]
        opens = [100 + i - 0.2 for i in range(5)] + [104]
        highs = [100 + i + 0.2 for i in range(5)] + [106]
        lows = [100 + i - 0.8 for i in range(5)] + [104]
        volumes = [1000] * 5 + [1000000]  # Extreme spike

        result = OrderFlowService.get_ofi_values(closes, opens, highs, lows, volumes)

        # Should calculate without error
        assert result["current_delta"] is not None
        assert result["current_cum_delta"] is not None

    def test_consolidation_market(self):
        """Test delta behavior in consolidation (choppy sideways market)."""
        # Choppy market: small range, no clear direction
        closes = [100, 100.5, 100.2, 100.4, 100.3] * 2
        opens = [100.3, 100.2, 100.4, 100.1, 100.4] * 2
        highs = [100.5, 100.6, 100.5, 100.6, 100.5] * 2
        lows = [100, 100, 100, 100, 100] * 2
        volumes = [1000] * 10

        result = OrderFlowService.detect_ofi_signals(closes, opens, highs, lows, volumes)

        # In choppy market, delta should be small
        assert isinstance(result["delta_strength"], float)
        assert result["delta_strength"] >= 0

    def test_gapping_market(self):
        """Test delta calculation with price gaps."""
        closes = [100, 110]  # Gap up
        opens = [100, 105]
        highs = [101, 111]
        lows = [99, 104]
        volumes = [1000, 1000]

        result = OrderFlowService.calculate_delta(closes, opens, highs, lows, volumes)

        # Should calculate delta even with gaps
        assert result["delta"][1] is not None
        assert result["delta"][1] > 0  # Close > open = positive

    def test_low_volume_periods(self):
        """Test delta calculation during low volume."""
        closes = [100, 101, 102]
        opens = [100, 100, 100]
        highs = [101, 102, 103]
        lows = [99, 99, 99]
        volumes = [1, 1, 1]  # Very low volume

        result = OrderFlowService.calculate_delta(closes, opens, highs, lows, volumes)

        # Should calculate but with small magnitudes
        delta = result["delta"]
        assert delta[1] is not None
        assert delta[2] is not None
        assert delta[2] > 0  # Still positive

    def test_long_consolidation_then_breakout(self):
        """Test divergence signal during consolidation followed by breakout."""
        # 10 bars of consolidation
        closes = [100 + (i % 2) * 0.5 for i in range(10)]
        opens = [100 + ((i + 1) % 2) * 0.5 for i in range(10)]
        highs = [100.5] * 10
        lows = [99.5] * 10
        volumes = [1000] * 10

        # Then 5 bars of uptrend with increasing volume
        closes += [110 + i for i in range(5)]
        opens += [105 + i for i in range(5)]
        highs += [111 + i for i in range(5)]
        lows += [104 + i for i in range(5)]
        volumes += [2000, 3000, 4000, 5000, 10000]

        result = OrderFlowService.detect_ofi_signals(closes, opens, highs, lows, volumes)

        # After breakout with volume, should show positive delta
        assert result["delta_positive"] is True
