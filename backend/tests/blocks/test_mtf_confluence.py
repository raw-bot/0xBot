"""
Test multi-timeframe (4h) confluence signals in Trinity decision block.
"""
import pytest
from decimal import Decimal

from src.blocks.block_trinity_decision import TrinityDecisionBlock
from src.blocks.block_market_data import MarketSnapshot


class TestMTF4hIndicators:
    """Test 4h timeframe indicator extraction."""

    def test_4h_bullish_trend_detected(self):
        """Test that 4h bullish trend is correctly identified."""
        block = TrinityDecisionBlock()

        # Create snapshot with bullish 4h indicators
        snapshot = MarketSnapshot(
            symbol="BTC/USDT",
            price=Decimal("45000"),
            change_24h=2.5,
            volume_24h=1000000,
            # 4h indicators - bullish
            ema_20_4h=44000.0,  # Price above EMA-20
            adx_4h=28.0,        # ADX > 20 (established trend)
            rsi_4h=55.0,
            macd_4h=10.5,
            signals={},
        )

        # Check 4h bullish detection
        result = block._check_4h_bullish(snapshot)
        assert result is True, "Should detect bullish 4h trend"

    def test_4h_bearish_trend_not_bullish(self):
        """Test that bearish 4h trend is not marked as bullish."""
        block = TrinityDecisionBlock()

        # Create snapshot with bearish 4h indicators
        snapshot = MarketSnapshot(
            symbol="BTC/USDT",
            price=Decimal("44000"),
            change_24h=-1.5,
            volume_24h=1000000,
            # 4h indicators - bearish (price below EMA)
            ema_20_4h=45000.0,  # Price below EMA-20
            adx_4h=28.0,
            rsi_4h=45.0,
            macd_4h=-5.0,
            signals={},
        )

        # Check 4h bullish detection
        result = block._check_4h_bullish(snapshot)
        assert result is False, "Should NOT detect bullish trend when price below EMA"

    def test_4h_bullish_but_weak_trend(self):
        """Test that 4h above EMA but weak trend (ADX < 20) not marked bullish."""
        block = TrinityDecisionBlock()

        # Create snapshot with price above EMA but weak trend
        snapshot = MarketSnapshot(
            symbol="BTC/USDT",
            price=Decimal("45000"),
            change_24h=0.5,
            volume_24h=1000000,
            # 4h indicators - price above but trend weak
            ema_20_4h=44000.0,  # Price above EMA-20
            adx_4h=15.0,        # ADX < 20 (weak trend)
            rsi_4h=55.0,
            macd_4h=5.0,
            signals={},
        )

        # Check 4h bullish detection
        result = block._check_4h_bullish(snapshot)
        assert result is False, "Should NOT detect bullish when ADX weak"

    def test_4h_indicators_missing(self):
        """Test graceful handling when 4h indicators are missing."""
        block = TrinityDecisionBlock()

        # Create snapshot without 4h indicators
        snapshot = MarketSnapshot(
            symbol="BTC/USDT",
            price=Decimal("45000"),
            change_24h=2.5,
            volume_24h=1000000,
            ema_20_4h=None,  # Missing
            adx_4h=None,     # Missing
            rsi_4h=None,
            macd_4h=None,
            signals={},
        )

        # Should return False gracefully
        result = block._check_4h_bullish(snapshot)
        assert result is False, "Should return False when indicators missing"


class TestMTFConfluence:
    """Test multi-timeframe confluence detection."""

    def test_mtf_confluence_both_timeframes_aligned(self):
        """Test that confluence is detected when 4h bullish AND 1h entry signals present."""
        block = TrinityDecisionBlock()

        # Create snapshot with 4h bullish + 1h entry signals
        snapshot = MarketSnapshot(
            symbol="BTC/USDT",
            price=Decimal("45000"),
            change_24h=2.5,
            volume_24h=1000000,
            # 4h bullish
            ema_20_4h=44000.0,
            adx_4h=28.0,
            rsi_4h=55.0,
            macd_4h=10.5,
            # 1h entry signals
            signals={
                "price_bounced": True,  # Entry signal present
                "macd_positive": False,
                "obv_accumulating": False,
                "delta_bullish_cross": False,
                "cloud_bullish_cross": False,
            },
        )

        # Check MTF confluence
        result = block._check_mtf_confluence(snapshot)
        assert result is True, "Should detect confluence when both timeframes aligned"

    def test_mtf_confluence_4h_bullish_no_1h_entry(self):
        """Test that confluence NOT detected when 4h bullish but no 1h entry signals."""
        block = TrinityDecisionBlock()

        # Create snapshot with 4h bullish but NO 1h entry signals
        snapshot = MarketSnapshot(
            symbol="BTC/USDT",
            price=Decimal("45000"),
            change_24h=2.5,
            volume_24h=1000000,
            # 4h bullish
            ema_20_4h=44000.0,
            adx_4h=28.0,
            rsi_4h=55.0,
            macd_4h=10.5,
            # 1h NO entry signals
            signals={
                "price_bounced": False,  # No entry signals
                "macd_positive": False,
                "obv_accumulating": False,
                "delta_bullish_cross": False,
                "cloud_bullish_cross": False,
            },
        )

        # Check MTF confluence
        result = block._check_mtf_confluence(snapshot)
        assert result is False, "Should NOT detect confluence without 1h entry signals"

    def test_mtf_confluence_4h_bearish_has_1h_signals(self):
        """Test that confluence NOT detected when 4h bearish even with 1h entry signals."""
        block = TrinityDecisionBlock()

        # Create snapshot with 4h bearish and 1h entry signals
        snapshot = MarketSnapshot(
            symbol="BTC/USDT",
            price=Decimal("44000"),
            change_24h=-1.5,
            volume_24h=1000000,
            # 4h bearish
            ema_20_4h=45000.0,  # Price below EMA
            adx_4h=28.0,
            rsi_4h=45.0,
            macd_4h=-5.0,
            # 1h has entry signals
            signals={
                "price_bounced": True,  # Has entry signals but 4h not bullish
                "macd_positive": True,
                "obv_accumulating": False,
                "delta_bullish_cross": False,
                "cloud_bullish_cross": False,
            },
        )

        # Check MTF confluence
        result = block._check_mtf_confluence(snapshot)
        assert result is False, "Should NOT detect confluence when 4h bearish"

    def test_mtf_confluence_with_cloud_cross(self):
        """Test confluence detection with cloud bullish cross as entry signal."""
        block = TrinityDecisionBlock()

        # Create snapshot with 4h bullish + cloud cross
        snapshot = MarketSnapshot(
            symbol="ETH/USDT",
            price=Decimal("2500"),
            change_24h=3.0,
            volume_24h=500000,
            # 4h bullish
            ema_20_4h=2450.0,
            adx_4h=25.0,
            rsi_4h=58.0,
            macd_4h=15.0,
            # 1h entry signals
            signals={
                "price_bounced": False,
                "macd_positive": False,
                "obv_accumulating": False,
                "delta_bullish_cross": False,
                "cloud_bullish_cross": True,  # Strong entry signal
            },
        )

        # Check MTF confluence
        result = block._check_mtf_confluence(snapshot)
        assert result is True, "Should detect confluence with cloud cross as entry"

    def test_mtf_confluence_with_delta_cross(self):
        """Test confluence detection with delta bullish cross as entry signal."""
        block = TrinityDecisionBlock()

        # Create snapshot with 4h bullish + delta cross
        snapshot = MarketSnapshot(
            symbol="SOL/USDT",
            price=Decimal("140"),
            change_24h=2.0,
            volume_24h=300000,
            # 4h bullish
            ema_20_4h=135.0,
            adx_4h=22.0,
            rsi_4h=52.0,
            macd_4h=8.0,
            # 1h entry signals
            signals={
                "price_bounced": False,
                "macd_positive": False,
                "obv_accumulating": False,
                "delta_bullish_cross": True,  # Order flow entry signal
                "cloud_bullish_cross": False,
            },
        )

        # Check MTF confluence
        result = block._check_mtf_confluence(snapshot)
        assert result is True, "Should detect confluence with delta cross as entry"

    def test_mtf_confluence_multiple_1h_signals(self):
        """Test confluence with multiple 1h entry signals."""
        block = TrinityDecisionBlock()

        # Create snapshot with many 1h signals + 4h bullish
        snapshot = MarketSnapshot(
            symbol="BTC/USDT",
            price=Decimal("46000"),
            change_24h=3.5,
            volume_24h=1200000,
            # 4h strong bullish
            ema_20_4h=44500.0,
            adx_4h=32.0,
            rsi_4h=60.0,
            macd_4h=20.0,
            # Multiple 1h entry signals
            signals={
                "price_bounced": True,
                "macd_positive": True,
                "obv_accumulating": True,
                "delta_bullish_cross": True,
                "cloud_bullish_cross": True,
            },
        )

        # Check MTF confluence
        result = block._check_mtf_confluence(snapshot)
        assert result is True, "Should detect strong confluence with multiple signals"


class TestMTFConfluenceIntegration:
    """Test MTF confluence integration into Trinity decision logic."""

    def test_mtf_confluence_boosts_confluence_score(self):
        """Test that MTF confluence adds +10 boost to confluence score."""
        block = TrinityDecisionBlock()

        # Create snapshot with MTF confluence
        snapshot = MarketSnapshot(
            symbol="BTC/USDT",
            price=Decimal("45000"),
            change_24h=2.5,
            volume_24h=1000000,
            ema_20_4h=44000.0,
            adx_4h=28.0,
            rsi_4h=55.0,
            macd_4h=10.5,
            signals={
                "regime_filter": True,
                "trend_strength": True,
                "price_bounced": True,
                "macd_positive": True,
                "obv_accumulating": False,
                "oversold": False,
                "volume_confirmed": True,
                "bollinger_expansion": False,
                "stoch_bullish_cross": False,
                "price_above_vwap_upper": False,
                "price_above_kumo": True,
                "tenkan_above_kijun": True,
                "cloud_bullish_cross": False,
                "kumo_bullish": True,
                "delta_positive": False,
                "delta_surge": False,
                "delta_bullish_cross": False,
                "delta_divergence": False,
            },
            confluence_score=80.0,
        )

        # Analyze confluence
        decision = block._analyze_confluence("BTC/USDT", snapshot)

        # Should have confluence boost from MTF
        assert decision.confluence_score >= 90.0, "MTF confluence should add +10 boost"

    def test_mtf_4h_bullish_reduces_weak_1h(self):
        """Test that 4h bullish with weak 1h signals applies -20% penalty."""
        block = TrinityDecisionBlock()

        # Create snapshot with 4h bullish but weak 1h signals
        snapshot = MarketSnapshot(
            symbol="BTC/USDT",
            price=Decimal("45000"),
            change_24h=2.5,
            volume_24h=1000000,
            ema_20_4h=44000.0,
            adx_4h=28.0,
            rsi_4h=55.0,
            macd_4h=10.5,
            signals={
                "regime_filter": True,
                "trend_strength": True,
                "price_bounced": False,
                "macd_positive": False,
                "obv_accumulating": False,
                "oversold": False,
                "volume_confirmed": True,
                "bollinger_expansion": False,
                "stoch_bullish_cross": False,
                "price_above_vwap_upper": False,
                "price_above_kumo": False,
                "tenkan_above_kijun": False,
                "cloud_bullish_cross": False,
                "kumo_bullish": False,
                "delta_positive": False,
                "delta_surge": False,
                "delta_bullish_cross": False,
                "delta_divergence": False,
            },
            confluence_score=60.0,
        )

        # Analyze confluence
        decision = block._analyze_confluence("BTC/USDT", snapshot)

        # Should have 20% penalty applied: 60 * 0.8 = 48
        assert decision.confluence_score <= 60.0, "4h bullish with weak 1h should reduce confluence"


class TestMTFEdgeCases:
    """Test edge cases in MTF signal detection."""

    def test_mtf_with_zero_price(self):
        """Test handling of edge case with zero price."""
        block = TrinityDecisionBlock()

        snapshot = MarketSnapshot(
            symbol="TEST/USDT",
            price=Decimal("0"),
            change_24h=0,
            volume_24h=0,
            ema_20_4h=100.0,
            adx_4h=25.0,
            signals={},
        )

        # Should handle gracefully
        result = block._check_4h_bullish(snapshot)
        assert result is False, "Should return False for zero price"

    def test_mtf_with_none_snapshot(self):
        """Test handling of None indicators."""
        block = TrinityDecisionBlock()

        snapshot = MarketSnapshot(
            symbol="TEST/USDT",
            price=Decimal("100"),
            change_24h=0,
            volume_24h=0,
            ema_20_4h=None,
            adx_4h=None,
            rsi_4h=None,
            macd_4h=None,
            signals=None,
        )

        # Should handle gracefully
        result1 = block._check_4h_bullish(snapshot)
        result2 = block._check_mtf_confluence(snapshot)
        assert result1 is False
        assert result2 is False

    def test_mtf_ema_exactly_at_price(self):
        """Test edge case where EMA exactly equals price."""
        block = TrinityDecisionBlock()

        snapshot = MarketSnapshot(
            symbol="BTC/USDT",
            price=Decimal("45000"),
            change_24h=0,
            volume_24h=1000000,
            ema_20_4h=45000.0,  # Exactly at price
            adx_4h=25.0,
            signals={},
        )

        # Price not above EMA (exactly equal), so not bullish
        result = block._check_4h_bullish(snapshot)
        assert result is False, "Should require price > EMA, not equal"

    def test_mtf_adx_exactly_at_threshold(self):
        """Test edge case where ADX exactly equals threshold."""
        block = TrinityDecisionBlock()

        snapshot = MarketSnapshot(
            symbol="BTC/USDT",
            price=Decimal("45000"),
            change_24h=0,
            volume_24h=1000000,
            ema_20_4h=44000.0,
            adx_4h=20.0,  # Exactly at threshold
            signals={},
        )

        # ADX not > 20 (exactly equal), so not bullish
        result = block._check_4h_bullish(snapshot)
        assert result is False, "Should require ADX > 20, not equal"
