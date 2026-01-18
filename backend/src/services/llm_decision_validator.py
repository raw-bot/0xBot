"""
LLM Decision Validator Service
Validates LLM trading decisions BEFORE execution.

PHILOSOPHY: Trust the LLM's intelligence. Only apply SAFETY LIMITS, not arbitrary defaults.
The LLM decides SL/TP based on market structure - we only intervene for extreme values.
"""

from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from ..core.config import config
from ..core.logger import get_logger

logger = get_logger(__name__)


class LLMDecisionValidator:
    """
    Validates LLM decisions for SAFETY only - not to override intelligent decisions.

    SAFETY LIMITS (absolute protection, not recommendations):
    - Max SL: 25% (prevent catastrophic loss)
    - Max TP: 100% (allows for big moves)
    - Min SL: 0.3% (prevent accidental stops from spread/slippage)
    - Min TP: 0.5% (must cover fees)

    These are SAFETY NETS, not defaults. The LLM's values are trusted unless they
    violate these safety limits.
    """

    # SAFETY LIMITS ONLY (not arbitrary recommendations)
    SAFETY_MAX_SL_PCT = 0.25  # 25% - absolute max loss allowed
    SAFETY_MAX_TP_PCT = 1.00  # 100% - allow for big runs
    SAFETY_MIN_SL_PCT = 0.003  # 0.3% - prevent accidental triggers
    SAFETY_MIN_TP_PCT = 0.005  # 0.5% - must cover fees

    # Only if LLM provides NOTHING, use these fallbacks
    FALLBACK_SL_PCT = 0.05  # 5% (used only when LLM gives no SL)
    FALLBACK_TP_PCT = 0.10  # 10% (used only when LLM gives no TP)

    @classmethod
    def validate_and_fix_decision(
        cls, decision: dict, current_price: float, symbol: str = "UNKNOWN"
    ) -> Tuple[bool, str, dict]:
        """
        Validate a single coin decision from LLM.

        PHILOSOPHY: Trust LLM decisions, only apply safety limits.
        - If LLM provides valid SL/TP: USE THEM (even if "unusual")
        - If LLM provides nothing: Apply fallback
        - If LLM values violate SAFETY limits: Clamp to safe range

        Args:
            decision: LLM decision dict
            current_price: Current market price
            symbol: Trading symbol for logging

        Returns:
            Tuple of (is_valid, reason, fixed_decision)
        """
        signal = decision.get("signal", "hold").lower()

        # HOLD/WAIT decisions are always valid
        if signal in ["hold", "wait", "no_trade"]:
            return True, "HOLD signal - no validation needed", decision

        # EXIT decisions are always valid
        if signal in ["close", "exit"]:
            return True, "EXIT signal - valid", decision

        # Validate entry signals
        if signal in ["buy_to_enter", "sell_to_enter", "buy", "sell", "entry"]:
            return cls._validate_entry_with_safety_limits(decision, current_price, symbol)

        # Unknown signal - treat as HOLD
        logger.warning(f"⚠️ {symbol} Unknown signal type: {signal}, treating as HOLD")
        fixed = decision.copy()
        fixed["signal"] = "hold"
        fixed["confidence"] = 0.5
        return True, f"Unknown signal fixed to HOLD", fixed

    @classmethod
    def _validate_entry_with_safety_limits(
        cls, decision: dict, current_price: float, symbol: str
    ) -> Tuple[bool, str, dict]:
        """
        Validate entry decision with SAFETY LIMITS only.

        TRUST the LLM's SL/TP unless they violate safety limits.
        """
        fixed = decision.copy()
        validation_notes = []

        # Extract values
        sl = decision.get("stop_loss", 0)
        tp = decision.get("take_profit", decision.get("profit_target", 0))
        entry = decision.get("entry_price", current_price) or current_price
        confidence = decision.get("confidence", 0)

        # Use current price if entry is invalid
        if not entry or entry <= 0:
            entry = current_price
            fixed["entry_price"] = entry
            validation_notes.append("entry_price set to market")

        # Check confidence (this is still needed for basic sanity)
        if confidence < 0.5:
            logger.warning(f"⚠️ {symbol} Confidence too low ({confidence:.0%}), skipping")
            fixed["signal"] = "hold"
            fixed["confidence"] = confidence
            return False, f"Confidence too low: {confidence:.0%}", fixed

        # Determine side from signal
        signal = decision.get("signal", "").lower()
        side = "short" if "sell" in signal else "long"

        # Check if LLM provided SL/TP
        has_sl = sl and sl > 0
        has_tp = tp and tp > 0

        # CASE 1: LLM provided nothing - use fallbacks
        if not has_sl or not has_tp:
            if not has_sl:
                if side == "long":
                    sl = entry * (1 - cls.FALLBACK_SL_PCT)
                else:
                    sl = entry * (1 + cls.FALLBACK_SL_PCT)
                fixed["stop_loss"] = sl
                validation_notes.append(f"SL fallback applied ({cls.FALLBACK_SL_PCT:.0%})")

            if not has_tp:
                if side == "long":
                    tp = entry * (1 + cls.FALLBACK_TP_PCT)
                else:
                    tp = entry * (1 - cls.FALLBACK_TP_PCT)
                fixed["take_profit"] = tp
                validation_notes.append(f"TP fallback applied ({cls.FALLBACK_TP_PCT:.0%})")
        else:
            # CASE 2: LLM provided values - TRUST THEM but apply safety limits
            fixed["stop_loss"] = sl
            fixed["take_profit"] = tp

        # Calculate actual distances
        sl_final = fixed.get("stop_loss", sl)
        tp_final = fixed.get("take_profit", tp)
        sl_dist, tp_dist = cls._calculate_distances(sl_final, entry, tp_final, side)

        # Apply SAFETY LIMITS only (clamp, don't override)
        safety_applied = False

        # SL safety: prevent too tight or too wide
        if sl_dist < cls.SAFETY_MIN_SL_PCT:
            # Too tight - clamp to minimum
            if side == "long":
                sl_final = entry * (1 - cls.SAFETY_MIN_SL_PCT)
            else:
                sl_final = entry * (1 + cls.SAFETY_MIN_SL_PCT)
            fixed["stop_loss"] = sl_final
            validation_notes.append(f"SL clamped to min safety ({cls.SAFETY_MIN_SL_PCT:.1%})")
            safety_applied = True
        elif sl_dist > cls.SAFETY_MAX_SL_PCT:
            # Too wide - clamp to maximum
            if side == "long":
                sl_final = entry * (1 - cls.SAFETY_MAX_SL_PCT)
            else:
                sl_final = entry * (1 + cls.SAFETY_MAX_SL_PCT)
            fixed["stop_loss"] = sl_final
            validation_notes.append(f"SL clamped to max safety ({cls.SAFETY_MAX_SL_PCT:.0%})")
            safety_applied = True

        # TP safety: prevent too tight or too ambitious
        if tp_dist < cls.SAFETY_MIN_TP_PCT:
            # Too tight - clamp to minimum
            if side == "long":
                tp_final = entry * (1 + cls.SAFETY_MIN_TP_PCT)
            else:
                tp_final = entry * (1 - cls.SAFETY_MIN_TP_PCT)
            fixed["take_profit"] = tp_final
            validation_notes.append(f"TP clamped to min safety ({cls.SAFETY_MIN_TP_PCT:.1%})")
            safety_applied = True
        elif tp_dist > cls.SAFETY_MAX_TP_PCT:
            # Too ambitious - clamp to maximum
            if side == "long":
                tp_final = entry * (1 + cls.SAFETY_MAX_TP_PCT)
            else:
                tp_final = entry * (1 - cls.SAFETY_MAX_TP_PCT)
            fixed["take_profit"] = tp_final
            validation_notes.append(f"TP clamped to max safety ({cls.SAFETY_MAX_TP_PCT:.0%})")
            safety_applied = True

        # Verify price relationships (SL/Entry/TP order)
        if not cls._check_price_relationships(
            fixed["stop_loss"], entry, fixed["take_profit"], side
        ):
            # Swap if inverted
            fixed["stop_loss"], fixed["take_profit"] = fixed["take_profit"], fixed["stop_loss"]
            validation_notes.append("SL/TP swapped (were inverted)")

        if validation_notes:
            logger.info(f"🔧 {symbol} Safety applied: {'; '.join(validation_notes)}")
            return True, f"Safety applied: {'; '.join(validation_notes)}", fixed
        else:
            logger.debug(f"✅ {symbol} LLM decision trusted as-is")
            return True, "LLM decision trusted (no safety limits triggered)", fixed

    @classmethod
    def _check_price_relationships(cls, sl: float, entry: float, tp: float, side: str) -> bool:
        """Check if SL/TP prices make sense for the given side."""
        if not sl or sl <= 0 or not tp or tp <= 0 or not entry or entry <= 0:
            return False

        if side == "long":
            # LONG: SL < Entry < TP
            return sl < entry < tp
        else:
            # SHORT: TP < Entry < SL
            return tp < entry < sl

    @classmethod
    def _calculate_distances(
        cls, sl: float, entry: float, tp: float, side: str
    ) -> Tuple[float, float]:
        """Calculate SL and TP distances as percentages."""
        if entry <= 0:
            return 0, 0

        if side == "long":
            sl_distance = (entry - sl) / entry if sl > 0 else 0
            tp_distance = (tp - entry) / entry if tp > 0 else 0
        else:
            sl_distance = (sl - entry) / entry if sl > 0 else 0
            tp_distance = (entry - tp) / entry if tp > 0 else 0

        return abs(sl_distance), abs(tp_distance)


# Convenience function for direct import
def validate_llm_decision(
    decision: dict, current_price: float, symbol: str = "UNKNOWN"
) -> Tuple[bool, str, dict]:
    """
    Convenience function to validate and fix an LLM decision.

    Returns:
        Tuple of (is_valid, reason, fixed_decision)
    """
    return LLMDecisionValidator.validate_and_fix_decision(decision, current_price, symbol)
