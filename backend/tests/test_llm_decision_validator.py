"""
Unit tests for LLM Decision Validator.
Tests validation and fix logic for LLM trading decisions.
"""

import pytest
from src.services.llm_decision_validator import LLMDecisionValidator


class TestLLMDecisionValidator:
    """Test suite for LLM Decision Validator."""

    def test_hold_signal_always_valid(self):
        """HOLD signals should always pass without modification."""
        decision = {"signal": "hold", "confidence": 0.5}
        is_valid, reason, fixed = LLMDecisionValidator.validate_and_fix_decision(
            decision, current_price=100.0, symbol="BTC/USDT"
        )
        assert is_valid is True
        assert "HOLD" in reason

    def test_exit_signal_always_valid(self):
        """EXIT/CLOSE signals should always pass."""
        decision = {"signal": "close", "confidence": 0.7}
        is_valid, reason, fixed = LLMDecisionValidator.validate_and_fix_decision(
            decision, current_price=100.0, symbol="ETH/USDT"
        )
        assert is_valid is True
        assert "EXIT" in reason

    def test_valid_long_entry(self):
        """Valid LONG entry with correct SL/TP relationship."""
        decision = {
            "signal": "buy_to_enter",
            "confidence": 0.75,
            "entry_price": 100.0,
            "stop_loss": 96.5,  # 3.5% below
            "take_profit": 107.0,  # 7% above
        }
        is_valid, reason, fixed = LLMDecisionValidator.validate_and_fix_decision(
            decision, current_price=100.0, symbol="BTC/USDT"
        )
        assert is_valid is True
        assert fixed["stop_loss"] == 96.5
        assert fixed["take_profit"] == 107.0

    def test_valid_short_entry(self):
        """Valid SHORT entry with correct SL/TP relationship."""
        decision = {
            "signal": "sell_to_enter",
            "confidence": 0.70,
            "entry_price": 100.0,
            "stop_loss": 103.5,  # 3.5% above
            "take_profit": 93.0,  # 7% below
        }
        is_valid, reason, fixed = LLMDecisionValidator.validate_and_fix_decision(
            decision, current_price=100.0, symbol="ETH/USDT"
        )
        assert is_valid is True
        assert fixed["stop_loss"] == 103.5
        assert fixed["take_profit"] == 93.0

    def test_confidence_too_low_rejected(self):
        """Low confidence entries should be converted to HOLD."""
        decision = {
            "signal": "buy_to_enter",
            "confidence": 0.40,  # Below 50% threshold
            "entry_price": 100.0,
            "stop_loss": 96.5,
            "take_profit": 107.0,
        }
        is_valid, reason, fixed = LLMDecisionValidator.validate_and_fix_decision(
            decision, current_price=100.0, symbol="SOL/USDT"
        )
        assert is_valid is False
        assert fixed["signal"] == "hold"
        assert "Confidence" in reason

    def test_invalid_sl_tp_gets_defaults_long(self):
        """Invalid SL/TP for LONG should get default values applied."""
        decision = {
            "signal": "buy_to_enter",
            "confidence": 0.75,
            "entry_price": 100.0,
            "stop_loss": 105.0,  # INVALID: SL above entry for LONG
            "take_profit": 95.0,  # INVALID: TP below entry for LONG
        }
        is_valid, reason, fixed = LLMDecisionValidator.validate_and_fix_decision(
            decision, current_price=100.0, symbol="BTC/USDT"
        )
        # Should be fixed, not rejected
        assert is_valid is True
        assert "Fixed" in reason or "recalculated" in reason.lower()
        # SL should now be below entry, TP above
        assert fixed["stop_loss"] < 100.0
        assert fixed["take_profit"] > 100.0

    def test_invalid_sl_tp_gets_defaults_short(self):
        """Invalid SL/TP for SHORT should get default values applied."""
        decision = {
            "signal": "sell_to_enter",
            "confidence": 0.75,
            "entry_price": 100.0,
            "stop_loss": 95.0,  # INVALID: SL below entry for SHORT
            "take_profit": 110.0,  # INVALID: TP above entry for SHORT
        }
        is_valid, reason, fixed = LLMDecisionValidator.validate_and_fix_decision(
            decision, current_price=100.0, symbol="ETH/USDT"
        )
        assert is_valid is True
        # SL should now be above entry, TP below
        assert fixed["stop_loss"] > 100.0
        assert fixed["take_profit"] < 100.0

    def test_sl_too_tight_gets_default(self):
        """SL that is too tight (< 0.5%) should be reset to default."""
        decision = {
            "signal": "buy_to_enter",
            "confidence": 0.75,
            "entry_price": 100.0,
            "stop_loss": 99.9,  # Only 0.1% - too tight
            "take_profit": 107.0,
        }
        is_valid, reason, fixed = LLMDecisionValidator.validate_and_fix_decision(
            decision, current_price=100.0, symbol="BTC/USDT"
        )
        assert is_valid is True
        # SL should be reset to default (3.5% = 96.5)
        assert fixed["stop_loss"] < 99.0

    def test_sl_too_far_gets_default(self):
        """SL that is too far (> 15%) should be reset to default."""
        decision = {
            "signal": "buy_to_enter",
            "confidence": 0.75,
            "entry_price": 100.0,
            "stop_loss": 80.0,  # 20% - too far
            "take_profit": 120.0,
        }
        is_valid, reason, fixed = LLMDecisionValidator.validate_and_fix_decision(
            decision, current_price=100.0, symbol="BTC/USDT"
        )
        assert is_valid is True
        # SL should be reset to default (3.5% = 96.5)
        assert fixed["stop_loss"] > 80.0

    def test_rr_ratio_gets_adjusted(self):
        """R/R ratio below 1.3 should get TP adjusted."""
        decision = {
            "signal": "buy_to_enter",
            "confidence": 0.75,
            "entry_price": 100.0,
            "stop_loss": 97.0,  # 3% SL
            "take_profit": 101.0,  # 1% TP - R/R = 0.33 (too low)
        }
        is_valid, reason, fixed = LLMDecisionValidator.validate_and_fix_decision(
            decision, current_price=100.0, symbol="SOL/USDT"
        )
        assert is_valid is True
        # TP should be adjusted for minimum R/R of 1.3
        # With 3% SL, TP should be at least 3.9% up
        assert fixed["take_profit"] >= 103.9

    def test_missing_sl_tp_gets_defaults(self):
        """Missing SL/TP should get default values."""
        decision = {
            "signal": "buy_to_enter",
            "confidence": 0.75,
            "entry_price": 100.0,
            # No stop_loss or take_profit
        }
        is_valid, reason, fixed = LLMDecisionValidator.validate_and_fix_decision(
            decision, current_price=100.0, symbol="BNB/USDT"
        )
        assert is_valid is True
        assert "stop_loss" in fixed
        assert "take_profit" in fixed
        assert fixed["stop_loss"] < 100.0
        assert fixed["take_profit"] > 100.0

    def test_unknown_signal_becomes_hold(self):
        """Unknown signal types should be converted to HOLD."""
        decision = {"signal": "maybe_buy", "confidence": 0.75}  # Unknown signal
        is_valid, reason, fixed = LLMDecisionValidator.validate_and_fix_decision(
            decision, current_price=100.0, symbol="XRP/USDT"
        )
        assert is_valid is True
        assert fixed["signal"] == "hold"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
