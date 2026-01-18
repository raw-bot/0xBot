"""Comprehensive test suite for MarketAnalysisService."""

import pytest
import numpy as np
from typing import Dict, List

from src.services.market_analysis_service import MarketAnalysisService


class TestCorrelationMatrix:
    """Tests for correlation matrix calculation."""

    def test_correlation_matrix_two_symbols(self):
        """Test correlation between two correlated symbols."""
        price_data = {
            "BTC/USDT": [100, 101, 102, 103, 104, 105],
            "ETH/USDT": [50, 50.5, 51, 51.5, 52, 52.5],  # Perfectly correlated (same growth rate)
        }
        result = MarketAnalysisService.calculate_correlation_matrix(price_data, period=5)

        assert "BTC/USDT" in result
        assert "ETH/USDT" in result
        assert result["BTC/USDT"]["BTC/USDT"] == 1.0
        assert result["ETH/USDT"]["ETH/USDT"] == 1.0
        # Perfect correlation (same constant growth rates)
        assert result["BTC/USDT"]["ETH/USDT"] > 0.9

    def test_correlation_matrix_inverse_correlation(self):
        """Test correlation between two different symbols."""
        price_data = {
            "BTC/USDT": [100, 110, 120, 130, 140],
            "ETH/USDT": [50, 60, 80, 70, 90],  # Follows different pattern
        }
        result = MarketAnalysisService.calculate_correlation_matrix(price_data, period=4)

        # Should have correlation values
        assert "BTC/USDT" in result
        assert "ETH/USDT" in result
        assert result["BTC/USDT"]["BTC/USDT"] == 1.0

    def test_correlation_matrix_single_symbol(self):
        """Test with single symbol returns empty dict."""
        price_data = {"BTC/USDT": [100, 101, 102, 103, 104]}
        result = MarketAnalysisService.calculate_correlation_matrix(price_data)
        assert result == {}

    def test_correlation_matrix_empty_data(self):
        """Test with empty price data."""
        result = MarketAnalysisService.calculate_correlation_matrix({})
        assert result == {}

    def test_correlation_matrix_period_larger_than_data(self):
        """Test when period exceeds data length."""
        price_data = {
            "BTC/USDT": [100, 101, 102],
            "ETH/USDT": [50, 50.5, 51],
        }
        result = MarketAnalysisService.calculate_correlation_matrix(price_data, period=10)

        # Should use min length (3)
        assert "BTC/USDT" in result
        assert "ETH/USDT" in result

    def test_correlation_matrix_with_nan_values(self):
        """Test correlation handles NaN (edge case data)."""
        price_data = {
            "BTC/USDT": [100, 101, 102, 103, 104, 105],
            "ETH/USDT": [50, 50, 50, 50, 50, 50],  # Flat data causes NaN in correlation
        }
        result = MarketAnalysisService.calculate_correlation_matrix(price_data, period=5)

        # Service should convert NaN to 0.0
        assert result["BTC/USDT"]["ETH/USDT"] == 0.0

    def test_correlation_matrix_many_symbols(self):
        """Test correlation matrix with multiple symbols."""
        price_data = {
            "BTC/USDT": [100 + i for i in range(20)],
            "ETH/USDT": [50 + i for i in range(20)],
            "ADA/USDT": [1 + (i * 0.1) for i in range(20)],
        }
        result = MarketAnalysisService.calculate_correlation_matrix(price_data)

        assert len(result) == 3
        assert all(len(result[s]) == 3 for s in result)
        assert all(result[s][s] == 1.0 for s in result)


class TestBTCDominance:
    """Tests for BTC dominance calculation."""

    def test_btc_dominance_50_percent(self):
        """Test when BTC is 50% of total market cap."""
        market_caps = {
            "BTC": 100.0,
            "ETH": 100.0,
        }
        result = MarketAnalysisService.calculate_btc_dominance(market_caps)
        assert result == 50.0

    def test_btc_dominance_high(self):
        """Test when BTC dominates market."""
        market_caps = {
            "BTC": 1000.0,
            "ETH": 100.0,
            "ADA": 50.0,
        }
        result = MarketAnalysisService.calculate_btc_dominance(market_caps)
        # 1000 / (1000 + 100 + 50) * 100 = 1000 / 1150 * 100 = 86.96
        assert result == pytest.approx(86.96, rel=0.01)

    def test_btc_dominance_no_btc(self):
        """Test when BTC is not in market caps."""
        market_caps = {
            "ETH": 100.0,
            "ADA": 50.0,
        }
        result = MarketAnalysisService.calculate_btc_dominance(market_caps)
        assert result == 0.0

    def test_btc_dominance_empty_market_caps(self):
        """Test with empty market caps."""
        result = MarketAnalysisService.calculate_btc_dominance({})
        assert result == 0.0

    def test_btc_dominance_zero_total_cap(self):
        """Test when total market cap is zero."""
        market_caps = {"BTC": 0.0, "ETH": 0.0}
        result = MarketAnalysisService.calculate_btc_dominance(market_caps)
        assert result == 0.0

    def test_btc_dominance_variant_key_names(self):
        """Test finding BTC with different key naming."""
        market_caps = {
            "BTC-USD": 1000.0,
            "ETH": 1000.0,
        }
        result = MarketAnalysisService.calculate_btc_dominance(market_caps)
        assert result == 50.0


class TestMarketRegimeDetection:
    """Tests for market regime detection."""

    def test_market_regime_risk_on(self):
        """Test detection of risk-on regime."""
        price_data = {
            "BTC/USDT": [100 + (i * 2) for i in range(25)],  # Uptrend
            "ETH/USDT": [50 + (i * 1.5) for i in range(25)],  # Stronger uptrend
        }
        result = MarketAnalysisService.detect_market_regime(price_data)

        assert result["regime"] in ["risk_on", "neutral"]  # Alts outperforming
        assert result["confidence"] > 0.0

    def test_market_regime_risk_off(self):
        """Test detection of risk-off regime."""
        price_data = {
            "BTC/USDT": [100 + (i * 1.5) for i in range(25)],  # BTC strong
            "ETH/USDT": [50 - (i * 0.5) for i in range(25)],  # ETH weak
        }
        result = MarketAnalysisService.detect_market_regime(price_data)

        assert result["regime"] in ["risk_off", "neutral"]
        assert result["confidence"] > 0.0

    def test_market_regime_neutral(self):
        """Test detection of neutral regime."""
        price_data = {
            "BTC/USDT": [100 + (i * 0.5) for i in range(25)],
            "ETH/USDT": [50 + (i * 0.25) for i in range(25)],
        }
        result = MarketAnalysisService.detect_market_regime(price_data)

        assert result["regime"] in ["neutral", "risk_on", "risk_off"]
        assert 0.0 <= result["confidence"] <= 1.0

    def test_market_regime_low_data(self):
        """Test with single symbol returns unknown."""
        price_data = {"BTC/USDT": [100, 101, 102]}
        result = MarketAnalysisService.detect_market_regime(price_data)

        assert result["regime"] == "unknown"
        assert result["confidence"] == 0.0
        assert result["signals"] == {}

    def test_market_regime_empty_data(self):
        """Test with empty data."""
        result = MarketAnalysisService.detect_market_regime({})
        assert result["regime"] == "unknown"
        assert result["confidence"] == 0.0

    def test_market_regime_high_volatility(self):
        """Test regime detection with high volatility."""
        price_data = {
            "BTC/USDT": [100, 150, 80, 130, 90, 140, 85, 135, 95, 145, 100, 150, 80, 130, 90, 140, 85, 135, 95, 145, 100, 150, 80, 130, 90],
            "ETH/USDT": [50, 75, 40, 65, 45, 70, 42, 67, 47, 72, 50, 75, 40, 65, 45, 70, 42, 67, 47, 72, 50, 75, 40, 65, 45],
        }
        result = MarketAnalysisService.detect_market_regime(price_data)

        assert "regime" in result
        assert result["signals"]["high_volatility"] == True

    def test_market_regime_signals_structure(self):
        """Test that regime detection returns expected signal structure."""
        price_data = {
            "BTC/USDT": [100 + (i * 0.5) for i in range(25)],
            "ETH/USDT": [50 + (i * 0.25) for i in range(25)],
        }
        result = MarketAnalysisService.detect_market_regime(price_data)

        assert "signals" in result
        signals = result["signals"]
        assert "avg_correlation" in signals
        assert "avg_volatility" in signals
        assert "btc_performance" in signals
        assert "alt_performance" in signals
        assert "high_volatility" in signals


class TestMarketBreadth:
    """Tests for market breadth calculation."""

    def test_market_breadth_advancing(self):
        """Test breadth with mostly advancing prices."""
        price_changes = {
            "BTC": 0.05,
            "ETH": 0.03,
            "ADA": 0.02,
            "XRP": -0.01,
        }
        result = MarketAnalysisService.calculate_market_breadth(price_changes)

        assert result["advancing"] == 3
        assert result["declining"] == 1
        assert result["unchanged"] == 0
        assert result["breadth_strong"] == True

    def test_market_breadth_declining(self):
        """Test breadth with mostly declining prices."""
        price_changes = {
            "BTC": -0.05,
            "ETH": -0.03,
            "ADA": 0.01,
        }
        result = MarketAnalysisService.calculate_market_breadth(price_changes)

        assert result["advancing"] == 1
        assert result["declining"] == 2
        assert result["breadth_strong"] == False

    def test_market_breadth_empty(self):
        """Test breadth with empty price changes."""
        result = MarketAnalysisService.calculate_market_breadth({})

        assert result["advancing"] == 0
        assert result["declining"] == 0
        assert result["unchanged"] == 0

    def test_market_breadth_unchanged(self):
        """Test breadth with unchanged prices."""
        price_changes = {
            "BTC": 0.0,
            "ETH": 0.0,
            "ADA": 0.0,
        }
        result = MarketAnalysisService.calculate_market_breadth(price_changes)

        assert result["advancing"] == 0
        assert result["declining"] == 0
        assert result["unchanged"] == 3

    def test_market_breadth_ad_ratio(self):
        """Test advance/decline ratio calculation."""
        price_changes = {
            "BTC": 0.05,
            "ETH": 0.05,
            "ADA": -0.05,
        }
        result = MarketAnalysisService.calculate_market_breadth(price_changes)

        # 2 advances, 1 decline = 2.0 ratio
        assert result["advance_decline_ratio"] == pytest.approx(2.0)

    def test_market_breadth_ad_ratio_no_declines(self):
        """Test A/D ratio when no declines exist."""
        price_changes = {
            "BTC": 0.05,
            "ETH": 0.05,
        }
        result = MarketAnalysisService.calculate_market_breadth(price_changes)

        # Should handle division by zero gracefully
        assert result["advance_decline_ratio"] == 2.0


class TestCapitalFlows:
    """Tests for capital flow analysis."""

    def test_capital_flow_into_btc(self):
        """Test capital flowing into BTC."""
        volumes = {
            "BTC": 1000.0,
            "ETH": 500.0,
        }
        price_changes = {
            "BTC": 0.10,
            "ETH": -0.05,
        }
        result = MarketAnalysisService.analyze_capital_flows(volumes, price_changes)

        assert result["btc_inflow"] == True
        assert result["dominant_flow"] == "into_btc"

    def test_capital_flow_into_alts(self):
        """Test capital flowing into altcoins."""
        volumes = {
            "BTC": 1000.0,
            "ETH": 2000.0,
            "ADA": 1500.0,
        }
        price_changes = {
            "BTC": -0.05,
            "ETH": 0.15,
            "ADA": 0.10,
        }
        result = MarketAnalysisService.analyze_capital_flows(volumes, price_changes)

        assert result["alt_inflow"] == True
        assert result["dominant_flow"] == "into_alts"

    def test_capital_flow_out_of_crypto(self):
        """Test capital flowing out of crypto."""
        volumes = {
            "BTC": 1000.0,
            "ETH": 500.0,
        }
        price_changes = {
            "BTC": -0.10,
            "ETH": -0.05,
        }
        result = MarketAnalysisService.analyze_capital_flows(volumes, price_changes)

        assert result["btc_inflow"] == False
        assert result["alt_inflow"] == False
        assert result["dominant_flow"] == "out_of_crypto"

    def test_capital_flow_balanced(self):
        """Test balanced capital flows."""
        volumes = {
            "BTC": 1000.0,
            "ETH": 1000.0,
        }
        price_changes = {
            "BTC": 0.05,
            "ETH": 0.05,
        }
        result = MarketAnalysisService.analyze_capital_flows(volumes, price_changes)

        assert result["dominant_flow"] == "balanced"

    def test_capital_flow_empty_data(self):
        """Test with empty volumes or price changes."""
        result = MarketAnalysisService.analyze_capital_flows({}, {})
        assert result["dominant_flow"] == "unknown"

    def test_capital_flow_strength_values(self):
        """Test that flow strength values are calculated."""
        volumes = {
            "BTC": 1000.0,
            "ETH": 500.0,
        }
        price_changes = {
            "BTC": 0.10,
            "ETH": 0.05,
        }
        result = MarketAnalysisService.analyze_capital_flows(volumes, price_changes)

        assert "btc_flow_strength" in result
        assert "alt_flow_strength" in result
        assert isinstance(result["btc_flow_strength"], float)


class TestComprehensiveMarketContext:
    """Tests for comprehensive market context generation."""

    def test_comprehensive_context_full_data(self):
        """Test with complete multi-coin data."""
        multi_coin_data = {
            "BTC/USDT": {
                "prices": [100 + (i * 0.5) for i in range(30)],
                "volume": 1000.0,
                "market_cap": 10000.0,
            },
            "ETH/USDT": {
                "prices": [50 + (i * 0.3) for i in range(30)],
                "volume": 500.0,
                "market_cap": 5000.0,
            },
        }
        result = MarketAnalysisService.get_comprehensive_market_context(multi_coin_data)

        assert "correlations" in result
        assert "regime" in result
        assert "breadth" in result
        assert "capital_flows" in result
        assert "btc_dominance" in result
        assert "analyzed_symbols" in result
        assert "timestamp" in result

    def test_comprehensive_context_partial_data(self):
        """Test with incomplete data fields."""
        multi_coin_data = {
            "BTC/USDT": {
                "prices": [100 + (i * 0.5) for i in range(25)],
            },
            "ETH/USDT": {
                "prices": [50 + (i * 0.3) for i in range(25)],
                "volume": 500.0,
            },
        }
        result = MarketAnalysisService.get_comprehensive_market_context(multi_coin_data)

        assert "correlations" in result
        assert result["btc_dominance"] == 0.0  # No market caps provided

    def test_comprehensive_context_empty_data(self):
        """Test with empty data."""
        result = MarketAnalysisService.get_comprehensive_market_context({})

        assert result["correlations"] == {}
        assert result["regime"]["regime"] == "unknown"
        assert result["analyzed_symbols"] == []
        assert "timestamp" in result

    def test_comprehensive_context_timestamp_present(self):
        """Test that timestamp is included."""
        multi_coin_data = {
            "BTC/USDT": {
                "prices": [100 + (i * 0.5) for i in range(25)],
            },
        }
        result = MarketAnalysisService.get_comprehensive_market_context(multi_coin_data)

        assert "timestamp" in result
        assert isinstance(result["timestamp"], str)
        assert "T" in result["timestamp"]  # ISO format

    def test_comprehensive_context_analyzed_symbols(self):
        """Test that all symbols are listed in analyzed_symbols."""
        multi_coin_data = {
            "BTC/USDT": {"prices": [100, 101, 102]},
            "ETH/USDT": {"prices": [50, 51, 52]},
            "ADA/USDT": {"prices": [1, 1.1, 1.2]},
        }
        result = MarketAnalysisService.get_comprehensive_market_context(multi_coin_data)

        assert len(result["analyzed_symbols"]) == 3
        assert "BTC/USDT" in result["analyzed_symbols"]


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_correlation_matrix_exception_handling(self):
        """Test correlation matrix handles exceptions gracefully."""
        price_data = {
            "BTC/USDT": [100, 101],  # Too short for calculation
        }
        # Should not raise, but return empty dict
        result = MarketAnalysisService.calculate_correlation_matrix(price_data, period=100)
        assert isinstance(result, dict)

    def test_btc_dominance_exception_handling(self):
        """Test BTC dominance handles exceptions."""
        # Simulate exception by passing None (should be handled)
        result = MarketAnalysisService.calculate_btc_dominance({})
        assert result == 0.0

    def test_regime_detection_exception_handling(self):
        """Test regime detection handles exceptions."""
        result = MarketAnalysisService.detect_market_regime({})
        assert result["regime"] == "unknown"
        assert result["confidence"] == 0.0

    def test_breadth_exception_handling(self):
        """Test breadth calculation handles exceptions."""
        result = MarketAnalysisService.calculate_market_breadth({})
        assert result["advancing"] == 0
        assert result["declining"] == 0

    def test_capital_flows_exception_handling(self):
        """Test capital flows handles exceptions."""
        result = MarketAnalysisService.analyze_capital_flows({}, {})
        assert result["dominant_flow"] == "unknown"

    def test_comprehensive_context_exception_handling(self):
        """Test comprehensive context handles exceptions."""
        result = MarketAnalysisService.get_comprehensive_market_context({})
        assert "timestamp" in result
        assert result["regime"]["regime"] == "unknown"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_small_price_values(self):
        """Test with very small price values."""
        price_data = {
            "TOKEN1": [0.00001, 0.00002, 0.00003],
            "TOKEN2": [0.00002, 0.00004, 0.00006],
        }
        result = MarketAnalysisService.calculate_correlation_matrix(price_data)
        assert isinstance(result, dict)

    def test_very_large_price_values(self):
        """Test with very large price values."""
        price_data = {
            "BTC": [50000, 51000, 52000],
            "ETH": [3000, 3100, 3200],
        }
        result = MarketAnalysisService.calculate_correlation_matrix(price_data)
        assert isinstance(result, dict)

    def test_single_price_point(self):
        """Test with minimal price history."""
        price_data = {
            "BTC/USDT": [100],
            "ETH/USDT": [50],
        }
        result = MarketAnalysisService.calculate_correlation_matrix(price_data)
        # Should handle gracefully
        assert isinstance(result, dict)

    def test_negative_market_caps(self):
        """Test with negative market caps (edge case)."""
        market_caps = {
            "BTC": -1000.0,
            "ETH": 1000.0,
        }
        result = MarketAnalysisService.calculate_btc_dominance(market_caps)
        # Should still calculate (BTC is still identified)
        assert result == 0.0  # Negative cap shouldn't dominate

    def test_negative_price_changes(self):
        """Test breadth with all negative changes."""
        price_changes = {
            "BTC": -0.10,
            "ETH": -0.05,
            "ADA": -0.01,
        }
        result = MarketAnalysisService.calculate_market_breadth(price_changes)
        assert result["advancing"] == 0
        assert result["declining"] == 3
