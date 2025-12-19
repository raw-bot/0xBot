"""
Core tests for 0xBot trading bot.
Tests critical components: config, risk manager, rate limiter.
"""

import os
import sys

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfig:
    """Test configuration module."""

    def test_config_loads(self):
        """Config should load without errors."""
        from src.core.config import config

        assert config is not None

    def test_config_has_required_fields(self):
        """Config should have all required trading parameters."""
        from src.core.config import config

        # Trading parameters
        assert hasattr(config, "MIN_CONFIDENCE_ENTRY")
        assert hasattr(config, "DEFAULT_STOP_LOSS_PCT")
        assert hasattr(config, "DEFAULT_TAKE_PROFIT_PCT")
        assert hasattr(config, "DEFAULT_LEVERAGE")

        # Security
        assert hasattr(config, "ALLOWED_SYMBOLS")
        assert hasattr(config, "LLM_CALLS_PER_MINUTE")

    def test_config_values_in_range(self):
        """Config values should be within valid ranges."""
        from src.core.config import config

        assert 0 < config.MIN_CONFIDENCE_ENTRY < 1
        assert 0 < config.DEFAULT_STOP_LOSS_PCT < 0.5
        assert 0 < config.DEFAULT_TAKE_PROFIT_PCT < 1
        assert config.DEFAULT_LEVERAGE >= 1

    def test_allowed_symbols_not_empty(self):
        """ALLOWED_SYMBOLS should contain valid trading pairs."""
        from src.core.config import config

        assert len(config.ALLOWED_SYMBOLS) > 0
        for symbol in config.ALLOWED_SYMBOLS:
            assert "/" in symbol
            assert "USDT" in symbol


class TestRateLimiter:
    """Test rate limiter functionality."""

    def test_rate_limiter_creates(self):
        """Rate limiter should create without errors."""
        from src.core.llm_client import RateLimiter

        limiter = RateLimiter(calls_per_minute=5)
        assert limiter.calls_per_minute == 5
        assert limiter.calls == []

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_calls(self):
        """Rate limiter should allow calls under limit."""
        from src.core.llm_client import RateLimiter

        limiter = RateLimiter(calls_per_minute=10)

        # Should allow first call without waiting
        await limiter.acquire()
        assert len(limiter.calls) == 1


class TestLLMDecisionValidator:
    """Test LLM decision validator."""

    def test_hold_signal_valid(self):
        """HOLD signals should always be valid."""
        from src.services.llm_decision_validator import LLMDecisionValidator

        decision = {"signal": "hold", "confidence": 0.5}
        is_valid, reason, _ = LLMDecisionValidator.validate_and_fix_decision(
            decision, current_price=100.0, symbol="BTC/USDT"
        )
        assert is_valid is True

    def test_low_confidence_rejected(self):
        """Low confidence entries should be rejected."""
        from src.services.llm_decision_validator import LLMDecisionValidator

        decision = {"signal": "buy_to_enter", "confidence": 0.3}
        is_valid, reason, fixed = LLMDecisionValidator.validate_and_fix_decision(
            decision, current_price=100.0, symbol="BTC/USDT"
        )
        assert is_valid is False
        assert fixed["signal"] == "hold"

    def test_invalid_sl_tp_fixed(self):
        """Invalid SL/TP should be fixed with defaults."""
        from src.services.llm_decision_validator import LLMDecisionValidator

        decision = {
            "signal": "buy_to_enter",
            "confidence": 0.75,
            "entry_price": 100.0,
            "stop_loss": 105.0,  # Invalid: above entry for long
            "take_profit": 95.0,  # Invalid: below entry for long
        }
        is_valid, reason, fixed = LLMDecisionValidator.validate_and_fix_decision(
            decision, current_price=100.0, symbol="BTC/USDT"
        )
        assert is_valid is True
        assert fixed["stop_loss"] < 100.0
        assert fixed["take_profit"] > 100.0


class TestRiskManager:
    """Test risk manager calculations."""

    def test_position_size_calculation(self):
        """Position size should be calculated correctly."""
        from decimal import Decimal

        from src.services.risk_manager_service import RiskManagerService

        size = RiskManagerService.calculate_position_size(
            capital=Decimal("10000"),
            size_pct=Decimal("0.10"),
            current_price=Decimal("100"),
            confidence=Decimal("0.8"),
            leverage=Decimal("1"),
        )
        # Position size should be positive and reasonable
        assert size > Decimal("0")
        assert size < Decimal("100")  # Not more than 100 units for $10k capital


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
