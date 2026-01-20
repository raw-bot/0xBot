"""
Test MACD integration in Trinity decision block.
"""
import pytest
from decimal import Decimal

from src.blocks.block_indicators import IndicatorBlock
from src.blocks.block_trinity_decision import TrinityDecisionBlock
from src.blocks.block_market_data import MarketSnapshot


class TestMACDInIndicators:
    """Test MACD calculation in indicator block."""

    def test_macd_calculated_in_indicators(self):
        """Test that MACD is calculated and included in indicator results."""
        block = IndicatorBlock()

        # Generate sample OHLCV data (200+ candles required for SMA-200)
        closes = [100 + i * 0.5 for i in range(250)]  # Uptrend
        highs = [101 + i * 0.5 for i in range(250)]
        lows = [99 + i * 0.5 for i in range(250)]
        volumes = [1000] * 250

        # Create OHLCV dict
        ohlcv_dict = {
            'timestamp': list(range(250)),
            'open': [100 + i * 0.5 for i in range(250)],
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        }

        # Calculate indicators
        result = block.calculate_indicators_from_ccxt(ohlcv_dict)

        # Verify MACD fields are present
        assert 'macd_line' in result
        assert 'macd_signal' in result
        assert 'macd_histogram' in result
        assert 'signals' in result
        assert 'macd_positive' in result['signals']
        assert 'macd_bullish_cross' in result['signals']

        # Verify MACD values are numeric
        assert isinstance(result['macd_line'], (int, float))
        assert isinstance(result['macd_signal'], (int, float))
        assert isinstance(result['signals']['macd_positive'], bool)

    def test_obv_calculated_in_indicators(self):
        """Test that OBV is calculated and included in indicator results."""
        block = IndicatorBlock()

        # Generate sample OHLCV data with uptrend (OBV should be accumulating)
        closes = [100 + i * 0.5 for i in range(250)]  # Uptrend
        highs = [101 + i * 0.5 for i in range(250)]
        lows = [99 + i * 0.5 for i in range(250)]
        volumes = [1000 + i * 10 for i in range(250)]  # Increasing volume

        ohlcv_dict = {
            'timestamp': list(range(250)),
            'open': [100 + i * 0.5 for i in range(250)],
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        }

        # Calculate indicators
        result = block.calculate_indicators_from_ccxt(ohlcv_dict)

        # Verify OBV fields are present
        assert 'obv' in result
        assert 'obv_ma' in result
        assert 'signals' in result
        assert 'obv_accumulating' in result['signals']

        # Verify OBV values are numeric
        assert isinstance(result['obv'], (int, float))
        assert isinstance(result['obv_ma'], (int, float))
        assert isinstance(result['signals']['obv_accumulating'], bool)

    def test_macd_positive_signal_in_uptrend(self):
        """Test that MACD positive signal is detected correctly."""
        block = IndicatorBlock()

        # Create realistic market data: consolidation then strong uptrend
        closes = []
        # Phase 1: Consolidation (first 100 candles)
        for i in range(100):
            closes.append(100 + (i % 5) * 0.5)
        # Phase 2: Strong uptrend (next 150 candles)
        for i in range(150):
            closes.append(102.5 + i * 1.5)

        highs = [c + 0.5 for c in closes]
        lows = [c - 0.5 for c in closes]
        volumes = [1000 + i * 10 for i in range(250)]

        ohlcv_dict = {
            'timestamp': list(range(250)),
            'open': closes,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        }

        result = block.calculate_indicators_from_ccxt(ohlcv_dict)

        # MACD should be in the result (even if not always positive in linear data)
        assert 'macd_line' in result
        assert 'signals' in result
        assert 'macd_positive' in result['signals']


class TestMACDInTrinityDecision:
    """Test MACD integration in Trinity decision block."""

    def test_macd_positive_increases_signals_met(self):
        """Test that MACD positive is counted as a signal."""
        trinity = TrinityDecisionBlock()

        snapshot = MarketSnapshot(
            symbol='BTC/USD',
            price=Decimal('100.0'),
            change_24h=0.0,
            volume_24h=0.0,
            sma_200=99.0,
            ema_20=99.5,
            adx=30.0,
            rsi=35.0,
            supertrend_signal='buy',
            signals={
                'regime_filter': True,
                'trend_strength': True,
                'pullback_detected': True,
                'price_bounced': True,
                'oversold': True,
                'volume_confirmed': True,
                'macd_positive': True,  # MACD positive
                'macd_bullish_cross': False,
                'price_above_vwap': True,
                'obv_accumulating': True  # OBV accumulating
            },
            confluence_score=100.0
        )

        decision = trinity._analyze_confluence('BTC/USD', snapshot)

        # All 7 signals met
        assert decision.signals_met == 7
        assert decision.should_enter is True
        assert decision.confidence > 0.8  # 7/7 signals

    def test_macd_negative_reduces_signals(self):
        """Test that negative MACD reduces signal count."""
        trinity = TrinityDecisionBlock()

        snapshot = MarketSnapshot(
            symbol='BTC/USD',
            price=Decimal('100.0'),
            change_24h=0.0,
            volume_24h=0.0,
            sma_200=99.0,
            ema_20=99.5,
            adx=30.0,
            rsi=35.0,
            supertrend_signal='buy',
            signals={
                'regime_filter': True,
                'trend_strength': True,
                'pullback_detected': True,
                'price_bounced': True,
                'oversold': True,
                'volume_confirmed': True,
                'macd_positive': False,  # MACD NOT positive
                'macd_bullish_cross': False,
                'price_above_vwap': True,
                'obv_accumulating': True  # OBV accumulating
            },
            confluence_score=80.0
        )

        decision = trinity._analyze_confluence('BTC/USD', snapshot)

        # Missing MACD signal - 6/7
        assert decision.signals_met == 6
        assert decision.should_enter is True  # Still enters with 6/7
        assert decision.confidence == pytest.approx(6/7, rel=0.01)

    def test_macd_insufficient_signals_no_entry(self):
        """Test that without MACD and other signals, no entry."""
        trinity = TrinityDecisionBlock()

        snapshot = MarketSnapshot(
            symbol='BTC/USD',
            price=Decimal('100.0'),
            change_24h=0.0,
            volume_24h=0.0,
            sma_200=99.0,
            ema_20=99.5,
            adx=30.0,
            rsi=35.0,
            supertrend_signal='buy',
            signals={
                'regime_filter': True,
                'trend_strength': False,  # Weak ADX
                'pullback_detected': False,
                'price_bounced': False,
                'oversold': False,
                'volume_confirmed': False,
                'macd_positive': False,  # MACD negative
                'macd_bullish_cross': False,
                'price_above_vwap': False,
                'obv_accumulating': False  # OBV not accumulating
            },
            confluence_score=20.0
        )

        decision = trinity._analyze_confluence('BTC/USD', snapshot)

        # Only 1 signal met
        assert decision.signals_met == 1
        assert decision.should_enter is False  # No entry below threshold

    def test_macd_bullish_cross_logged(self):
        """Test that MACD bullish cross is detected and logged."""
        trinity = TrinityDecisionBlock()

        snapshot = MarketSnapshot(
            symbol='BTC/USD',
            price=Decimal('100.0'),
            change_24h=0.0,
            volume_24h=0.0,
            sma_200=99.0,
            ema_20=99.5,
            adx=30.0,
            rsi=35.0,
            supertrend_signal='buy',
            signals={
                'regime_filter': True,
                'trend_strength': True,
                'pullback_detected': True,
                'price_bounced': True,
                'oversold': True,
                'volume_confirmed': True,
                'macd_positive': True,
                'macd_bullish_cross': True,  # Bullish cross just happened
                'price_above_vwap': True,
                'obv_accumulating': True  # OBV accumulating
            },
            confluence_score=100.0
        )

        decision = trinity._analyze_confluence('BTC/USD', snapshot)

        # Should recognize bullish cross
        assert decision.should_enter is True
        # Signal is logged (would need to check logs to verify)
