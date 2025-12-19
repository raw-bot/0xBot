"""
LLM Decision Validator Service
Validates LLM trading decisions BEFORE execution.
Option B: Fallback to default SL/TP when LLM values are invalid.
"""

from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from ..core.config import config
from ..core.logger import get_logger

logger = get_logger(__name__)


class LLMDecisionValidator:
    """
    Validates LLM decisions for sanity and consistency.

    Based on research and bot reference logs:
    - Typical SL: 1-5% (bot uses 3.5%)
    - Typical TP: 3-10% (bot uses 7%)
    - Typical R/R: 1:2 to 1:3 (bot uses 2:1)
    """

    # Maximum acceptable distance for SL/TP from entry price
    MAX_SL_DISTANCE_PCT = 0.15  # 15% max for SL (very wide, but allows for volatile moves)
    MAX_TP_DISTANCE_PCT = 0.30  # 30% max for TP
    MIN_SL_DISTANCE_PCT = 0.005  # 0.5% min for SL (avoid too tight)
    MIN_TP_DISTANCE_PCT = 0.01  # 1% min for TP
    MIN_RR_RATIO = 1.3  # Minimum risk/reward ratio

    @classmethod
    def validate_and_fix_decision(
        cls, decision: dict, current_price: float, symbol: str = "UNKNOWN"
    ) -> Tuple[bool, str, dict]:
        """
        Validate a single coin decision from LLM and fix if needed.

        Option B: If validation fails, return corrected decision with defaults.

        Args:
            decision: LLM decision dict
            current_price: Current market price
            symbol: Trading symbol for logging

        Returns:
            Tuple of (is_valid, reason, fixed_decision)
            - is_valid: True if original was valid OR was successfully fixed
            - reason: Explanation of what happened
            - fixed_decision: The corrected/validated decision
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
            return cls._validate_and_fix_entry(decision, current_price, symbol)

        # Unknown signal - treat as HOLD
        logger.warning(f"⚠️ {symbol} Unknown signal type: {signal}, treating as HOLD")
        fixed = decision.copy()
        fixed["signal"] = "hold"
        fixed["confidence"] = 0.5
        fixed["_validation_note"] = f"Unknown signal '{signal}' converted to HOLD"
        return True, f"Unknown signal fixed to HOLD", fixed

    @classmethod
    def _validate_and_fix_entry(
        cls, decision: dict, current_price: float, symbol: str
    ) -> Tuple[bool, str, dict]:
        """
        Validate entry decision prices and fix if needed.

        Option B Implementation: Use defaults when LLM values are invalid.
        """
        fixed = decision.copy()
        validation_notes = []
        was_fixed = False

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
            was_fixed = True

        # Check confidence
        if confidence < 0.5:
            logger.warning(f"⚠️ {symbol} Confidence too low ({confidence:.0%}), skipping")
            fixed["signal"] = "hold"
            fixed["confidence"] = confidence
            fixed["_validation_note"] = f"Confidence {confidence:.0%} < 50%"
            return False, f"Confidence too low: {confidence:.0%}", fixed

        # Determine side from signal
        signal = decision.get("signal", "").lower()
        if "sell" in signal:
            side = "short"
        else:
            side = "long"

        # Check if SL/TP are missing or invalid
        prices_valid = cls._check_price_relationships(sl, entry, tp, side)

        if not prices_valid:
            # Calculate defaults based on config
            if side == "long":
                sl = entry * (1 - config.DEFAULT_STOP_LOSS_PCT)  # 3.5% below
                tp = entry * (1 + config.DEFAULT_TAKE_PROFIT_PCT)  # 7% above
            else:  # short
                sl = entry * (1 + config.DEFAULT_STOP_LOSS_PCT)  # 3.5% above
                tp = entry * (1 - config.DEFAULT_TAKE_PROFIT_PCT)  # 7% below

            fixed["stop_loss"] = sl
            fixed["take_profit"] = tp
            validation_notes.append(
                f"SL/TP recalculated with defaults (SL:{config.DEFAULT_STOP_LOSS_PCT:.1%}, TP:{config.DEFAULT_TAKE_PROFIT_PCT:.1%})"
            )
            was_fixed = True
            logger.info(f"🔧 {symbol} Fixed SL/TP: SL=${sl:.2f}, TP=${tp:.2f}")
        else:
            # Validate distances even if relationship is correct
            sl_distance, tp_distance = cls._calculate_distances(sl, entry, tp, side)

            # Check if distances are within acceptable range
            if sl_distance < cls.MIN_SL_DISTANCE_PCT or sl_distance > cls.MAX_SL_DISTANCE_PCT:
                # Recalculate with default
                if side == "long":
                    sl = entry * (1 - config.DEFAULT_STOP_LOSS_PCT)
                else:
                    sl = entry * (1 + config.DEFAULT_STOP_LOSS_PCT)
                fixed["stop_loss"] = sl
                validation_notes.append(f"SL distance out of range, reset to default")
                was_fixed = True

            if tp_distance < cls.MIN_TP_DISTANCE_PCT or tp_distance > cls.MAX_TP_DISTANCE_PCT:
                # Recalculate with default
                if side == "long":
                    tp = entry * (1 + config.DEFAULT_TAKE_PROFIT_PCT)
                else:
                    tp = entry * (1 - config.DEFAULT_TAKE_PROFIT_PCT)
                fixed["take_profit"] = tp
                validation_notes.append(f"TP distance out of range, reset to default")
                was_fixed = True

        # Final validation of R/R ratio
        sl_final = fixed.get("stop_loss", sl)
        tp_final = fixed.get("take_profit", tp)
        sl_dist, tp_dist = cls._calculate_distances(sl_final, entry, tp_final, side)

        if sl_dist > 0:
            rr_ratio = tp_dist / sl_dist
            if rr_ratio < cls.MIN_RR_RATIO:
                # Adjust TP to meet minimum R/R
                min_tp_dist = sl_dist * cls.MIN_RR_RATIO
                if side == "long":
                    tp_final = entry * (1 + min_tp_dist)
                else:
                    tp_final = entry * (1 - min_tp_dist)
                fixed["take_profit"] = tp_final
                validation_notes.append(f"TP adjusted for R/R >= {cls.MIN_RR_RATIO}")
                was_fixed = True

        # Add validation note
        if was_fixed:
            fixed["_validation_note"] = "; ".join(validation_notes)
            fixed["_original_sl"] = decision.get("stop_loss")
            fixed["_original_tp"] = decision.get("take_profit", decision.get("profit_target"))
            logger.info(f"✅ {symbol} Decision fixed: {'; '.join(validation_notes)}")
            return True, f"Fixed: {'; '.join(validation_notes)}", fixed
        else:
            logger.debug(f"✅ {symbol} Decision valid, no fixes needed")
            return True, "Validation passed", fixed

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
