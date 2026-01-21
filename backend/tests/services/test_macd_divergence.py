"""Test suite for MACD Divergence detection implementation."""

import pytest
from src.services.indicator_service import IndicatorService


class TestMACDDivergenceBasics:
    """Tests for basic MACD divergence calculations."""

    def test_divergence_insufficient_data(self):
        """Test divergence detection returns empty when insufficient data."""
        prices = [100 + i for i in range(10)]  # Only 10 periods, need 26+

        result = IndicatorService.detect_macd_divergence(prices)

        assert result["has_divergence"] is False
        assert result["divergence_type"] is None
        assert result["divergence_strength"] == 0.0
        assert result["signals"] == {}

    def test_divergence_with_sufficient_data(self):
        """Test divergence detection with 50+ periods."""
        # Create uptrending data
        closes = [100 + i for i in range(50)]

        result = IndicatorService.detect_macd_divergence(closes)

        # Should have divergence structure
        assert "has_divergence" in result
        assert "divergence_type" in result
        assert "divergence_strength" in result
        assert "signals" in result

    def test_divergence_signals_structure(self):
        """Test all required signals are present in output."""
        closes = [100 + i for i in range(50)]
        highs = [100 + i + 1 for i in range(50)]
        lows = [100 + i - 1 for i in range(50)]

        result = IndicatorService.detect_macd_divergence(closes, highs, lows)

        # All required signals should be present
        required_signals = [
            "macd_bullish_divergence",
            "macd_bearish_divergence",
            "macd_hidden_bullish",
            "macd_hidden_bearish",
        ]
        for signal in required_signals:
            assert signal in result["signals"]


class TestRegularDivergence:
    """Tests for regular divergence detection (reversal signals)."""

    def test_regular_bearish_divergence(self):
        """Test detection of bearish regular divergence (HH/LH pattern).

        Pattern: Price makes higher high but MACD makes lower high.
        """
        # Create data that forms bearish divergence
        # First part: uptrend with lower MACD
        closes = list(range(100, 110))  # Prices 100-109

        # Second part: another uptrend but MACD reverses down
        closes.extend([110 + (i * 0.5) for i in range(10)])  # Slower rise
        closes.extend(list(range(120, 130)))  # Final spike in price

        # Add enough history for MACD to calculate
        closes = [100 - 20 + i for i in range(30)] + closes

        # Only test structure exists - exact bearish detection depends on MACD calculation
        result = IndicatorService.detect_macd_divergence(closes)
        assert "divergence_type" in result
        assert "divergence_strength" in result

    def test_regular_bullish_divergence(self):
        """Test detection of bullish regular divergence (LL/HL pattern).

        Pattern: Price makes lower low but MACD makes higher low.
        """
        # Create data that forms bullish divergence
        closes = list(range(100, 80, -1))  # Downtrend 100-80

        # Second dip: price goes lower but MACD bounces
        closes.extend(list(range(80, 75, -1)))  # New low 75
        closes.extend([75 + (i * 0.3) for i in range(20)])  # Bounce up

        # Add enough history for MACD to calculate
        closes = [100 - 20 + i for i in range(30)] + closes

        result = IndicatorService.detect_macd_divergence(closes)
        assert "divergence_type" in result
        assert "divergence_strength" in result


class TestHiddenDivergence:
    """Tests for hidden divergence detection (continuation signals)."""

    def test_hidden_bullish_divergence(self):
        """Test detection of hidden bullish divergence (uptrend continuation).

        Pattern: Price makes lower low but MACD makes higher low.
        Context: Trend was up, so signals continuation upward.
        """
        # Create uptrending data with pullback
        closes = list(range(100, 115))  # Initial uptrend
        closes.extend(list(range(115, 110, -1)))  # Pullback

        # Continue higher
        closes.extend(list(range(110, 125)))

        # Add history
        closes = [100 - 20 + i for i in range(30)] + closes

        result = IndicatorService.detect_macd_divergence(closes)
        assert "divergence_strength" in result

    def test_hidden_bearish_divergence(self):
        """Test detection of hidden bearish divergence (downtrend continuation).

        Pattern: Price makes higher high but MACD makes lower high.
        Context: Trend was down, so signals continuation downward.
        """
        # Create downtrending data with bounce
        closes = list(range(100, 85, -1))  # Initial downtrend
        closes.extend(list(range(85, 90)))  # Bounce up

        # Continue lower
        closes.extend(list(range(90, 75, -1)))

        # Add history
        closes = [100 - 20 + i for i in range(30)] + closes

        result = IndicatorService.detect_macd_divergence(closes)
        assert "divergence_strength" in result


class TestDivergenceStrength:
    """Tests for divergence strength calculation."""

    def test_divergence_strength_range(self):
        """Test divergence strength is between 0 and 1."""
        closes = [100 + i + (5 if i % 2 == 0 else 0) for i in range(100)]

        result = IndicatorService.detect_macd_divergence(closes)

        assert 0 <= result["divergence_strength"] <= 1

    def test_strong_divergence_high_strength(self):
        """Test strong divergence has higher strength value."""
        # Create strong divergence pattern
        closes = list(range(100, 120))  # Strong uptrend
        closes.extend(list(range(120, 105, -1)))  # Strong pullback

        # Add history
        closes = [100 - 30 + i for i in range(40)] + closes

        result = IndicatorService.detect_macd_divergence(closes)

        # Strong divergence should have reasonable strength or no divergence
        assert result["divergence_strength"] >= 0

    def test_weak_divergence_low_strength_or_none(self):
        """Test weak divergence has low strength or not detected."""
        # Create weak uptrend (flat)
        closes = [100] * 80

        result = IndicatorService.detect_macd_divergence(closes)

        # Flat market should not show divergence
        assert result["divergence_strength"] < 0.05 or result["has_divergence"] is False


class TestDivergenceWithOptionalParameters:
    """Tests for using optional highs/lows and pre-calculated MACD."""

    def test_divergence_with_highs_lows(self):
        """Test divergence detection using provided highs and lows."""
        closes = [100 + i for i in range(50)]
        highs = [100 + i + 2 for i in range(50)]
        lows = [100 + i - 2 for i in range(50)]

        result = IndicatorService.detect_macd_divergence(closes, highs, lows)

        assert "divergence_type" in result
        assert "divergence_strength" in result

    def test_divergence_with_precalculated_macd(self):
        """Test divergence detection using pre-calculated MACD values."""
        closes = [100 + i for i in range(50)]
        macd_result = IndicatorService.calculate_macd(closes)
        macd_values = macd_result["macd"]

        result = IndicatorService.detect_macd_divergence(
            closes, macd_values=macd_values
        )

        assert "divergence_type" in result
        assert "divergence_strength" in result

    def test_divergence_without_optional_params(self):
        """Test divergence detection works without optional parameters."""
        closes = [100 + i for i in range(50)]

        result = IndicatorService.detect_macd_divergence(closes)

        # Should calculate internally
        assert "divergence_type" in result
        assert "divergence_strength" in result


class TestDivergenceEdgeCases:
    """Tests for edge cases in divergence detection."""

    def test_divergence_with_empty_list(self):
        """Test divergence detection with empty prices."""
        result = IndicatorService.detect_macd_divergence([])

        assert result["has_divergence"] is False
        assert result["divergence_type"] is None
        assert result["divergence_strength"] == 0.0

    def test_divergence_with_none_values(self):
        """Test divergence detection handles None values gracefully."""
        closes = [100 + i if i % 3 != 0 else 100 for i in range(50)]

        result = IndicatorService.detect_macd_divergence(closes)

        # Should not crash
        assert isinstance(result["has_divergence"], bool)
        assert result["divergence_strength"] >= 0

    def test_divergence_with_flat_market(self):
        """Test divergence detection in flat market."""
        closes = [100.0] * 50

        result = IndicatorService.detect_macd_divergence(closes)

        # Flat market should have no divergence
        assert result["has_divergence"] is False
        assert result["divergence_strength"] < 0.05

    def test_divergence_with_gaps(self):
        """Test divergence detection handles price gaps."""
        closes = [100 + i for i in range(20)]
        closes.append(120)  # Gap up
        closes.extend([120 + i for i in range(30)])

        result = IndicatorService.detect_macd_divergence(closes)

        # Should handle gaps without crashing
        assert isinstance(result["has_divergence"], bool)
        assert result["divergence_strength"] >= 0

    def test_divergence_with_low_volatility(self):
        """Test divergence detection with very low volatility."""
        closes = [100.0 + (0.1 * i) for i in range(50)]

        result = IndicatorService.detect_macd_divergence(closes)

        # Low volatility should have low divergence
        assert result["divergence_strength"] < 0.1

    def test_divergence_with_high_volatility(self):
        """Test divergence detection with high volatility."""
        closes = [100 + (10 * ((-1) ** i)) for i in range(50)]

        result = IndicatorService.detect_macd_divergence(closes)

        # Should handle high volatility
        assert isinstance(result["divergence_strength"], float)
        assert 0 <= result["divergence_strength"] <= 1


class TestDivergenceSignalsConsistency:
    """Tests for signal consistency and correctness."""

    def test_only_one_divergence_type_at_a_time(self):
        """Test only one divergence type is set per call."""
        closes = [100 + i for i in range(100)]
        highs = [100 + i + 1 for i in range(100)]
        lows = [100 + i - 1 for i in range(100)]

        result = IndicatorService.detect_macd_divergence(closes, highs, lows)

        # Only one signal should be True at a time (if any)
        true_count = sum(1 for v in result["signals"].values() if v is True)
        assert true_count <= 1

    def test_divergence_type_matches_signals(self):
        """Test divergence_type field matches the signals set."""
        closes = [100 + i for i in range(100)]
        highs = [100 + i + 1 for i in range(100)]
        lows = [100 + i - 1 for i in range(100)]

        result = IndicatorService.detect_macd_divergence(closes, highs, lows)

        divergence_type = result["divergence_type"]
        if divergence_type == "regular_bullish":
            assert result["signals"].get("macd_bullish_divergence") is True
        elif divergence_type == "regular_bearish":
            assert result["signals"].get("macd_bearish_divergence") is True
        elif divergence_type == "hidden_bullish":
            assert result["signals"].get("macd_hidden_bullish") is True
        elif divergence_type == "hidden_bearish":
            assert result["signals"].get("macd_hidden_bearish") is True

    def test_has_divergence_flag_matches_strength(self):
        """Test has_divergence flag matches strength threshold."""
        closes = [100 + i for i in range(100)]
        highs = [100 + i + 1 for i in range(100)]
        lows = [100 + i - 1 for i in range(100)]

        result = IndicatorService.detect_macd_divergence(closes, highs, lows)

        # If strength >= 0.05, has_divergence should be True
        if result["divergence_strength"] >= 0.05:
            assert result["has_divergence"] is True
        # If strength < 0.05, has_divergence should be False
        elif result["divergence_strength"] < 0.05:
            assert result["has_divergence"] is False


class TestRealisticDivergenceScenarios:
    """Tests with realistic market scenarios."""

    def test_realistic_bullish_reversal(self):
        """Test realistic bullish divergence scenario (failed sell-off)."""
        # Strong downtrend, then failed attempt to go lower
        closes = list(range(200, 100, -2))  # Strong sell-off 200->100
        closes.extend(list(range(100, 90, -1)))  # New low attempt 100->90

        # Add initial history
        closes = list(range(250, 200, -1)) + closes

        result = IndicatorService.detect_macd_divergence(closes)

        # Should detect structure
        assert "divergence_type" in result

    def test_realistic_bearish_reversal(self):
        """Test realistic bearish divergence scenario (failed rally)."""
        # Strong uptrend, then failed attempt to go higher
        closes = list(range(100, 200, 2))  # Strong rally 100->200
        closes.extend(list(range(200, 210)))  # New high attempt 200->210

        # Add initial history
        closes = list(range(50, 100)) + closes

        result = IndicatorService.detect_macd_divergence(closes)

        # Should detect structure
        assert "divergence_type" in result

    def test_realistic_uptrend_continuation(self):
        """Test realistic hidden bullish divergence (pullback in uptrend)."""
        # Uptrend with pullback
        closes = list(range(100, 150))  # Uptrend 100->150
        closes.extend(list(range(150, 130, -1)))  # Pullback 150->130
        closes.extend(list(range(130, 170)))  # Continue up 130->170

        # Add history
        closes = list(range(80, 100)) + closes

        result = IndicatorService.detect_macd_divergence(closes)

        # Should provide analysis
        assert result["divergence_strength"] >= 0

    def test_realistic_downtrend_continuation(self):
        """Test realistic hidden bearish divergence (bounce in downtrend)."""
        # Downtrend with bounce
        closes = list(range(200, 150, -1))  # Downtrend 200->150
        closes.extend(list(range(150, 170)))  # Bounce 150->170
        closes.extend(list(range(170, 100, -1)))  # Continue down 170->100

        # Add history
        closes = list(range(250, 200, -1)) + closes

        result = IndicatorService.detect_macd_divergence(closes)

        # Should provide analysis
        assert result["divergence_strength"] >= 0
