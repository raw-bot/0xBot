"""
LLM Decision Validator - Validates trading decisions with safety limits only.
Trusts the LLM's intelligence, intervening only for extreme values.
"""

from typing import Dict, Tuple

from ..core.logger import get_logger

logger = get_logger(__name__)


class LLMDecisionValidator:
    """Validates LLM decisions with safety limits only (not overriding intelligent decisions)."""

    # Safety limits (absolute protection)
    SAFETY_MAX_SL_PCT = 0.25   # 25% max loss
    SAFETY_MAX_TP_PCT = 1.00   # 100% max target
    SAFETY_MIN_SL_PCT = 0.003  # 0.3% min to avoid spread triggers
    SAFETY_MIN_TP_PCT = 0.005  # 0.5% min to cover fees

    # Fallbacks only when LLM provides nothing
    FALLBACK_SL_PCT = 0.05  # 5%
    FALLBACK_TP_PCT = 0.10  # 10%

    @classmethod
    def validate_and_fix_decision(
        cls, decision: dict, current_price: float, symbol: str = "UNKNOWN"
    ) -> Tuple[bool, str, dict]:
        """Validate and fix an LLM decision, applying safety limits only."""
        signal = decision.get("signal", "hold").lower()

        if signal in ["hold", "wait", "no_trade"]:
            return True, "HOLD signal", decision

        if signal in ["close", "exit"]:
            return True, "EXIT signal", decision

        if signal in ["buy_to_enter", "sell_to_enter", "buy", "sell", "entry"]:
            return cls._validate_entry_with_safety_limits(decision, current_price, symbol)

        logger.warning(f"{symbol} Unknown signal: {signal}, treating as HOLD")
        return True, "Unknown signal fixed to HOLD", {**decision, "signal": "hold", "confidence": 0.5}

    @classmethod
    def _apply_price_offset(cls, entry: float, pct: float, side: str, is_sl: bool) -> float:
        """Calculate SL or TP price from entry using percentage offset."""
        if side == "long":
            return entry * (1 - pct) if is_sl else entry * (1 + pct)
        return entry * (1 + pct) if is_sl else entry * (1 - pct)

    @classmethod
    def _calculate_distance(cls, entry: float, price: float, side: str, is_sl: bool) -> float:
        """Calculate percentage distance from entry to SL or TP."""
        if entry <= 0 or price <= 0:
            return 0
        if side == "long":
            return abs((entry - price) / entry) if is_sl else abs((price - entry) / entry)
        return abs((price - entry) / entry) if is_sl else abs((entry - price) / entry)

    @classmethod
    def _validate_entry_with_safety_limits(
        cls, decision: dict, current_price: float, symbol: str
    ) -> Tuple[bool, str, dict]:
        """Validate entry decision with safety limits only."""
        fixed = decision.copy()
        notes = []

        sl = decision.get("stop_loss", 0)
        tp = decision.get("take_profit", decision.get("profit_target", 0))
        entry = decision.get("entry_price", current_price) or current_price
        confidence = decision.get("confidence", 0)

        if not entry or entry <= 0:
            entry = current_price
            fixed["entry_price"] = entry
            notes.append("entry set to market")

        if confidence < 0.5:
            logger.warning(f"{symbol} Confidence too low ({confidence:.0%})")
            return False, f"Confidence too low: {confidence:.0%}", {**fixed, "signal": "hold"}

        side = "short" if "sell" in decision.get("signal", "").lower() else "long"

        # Apply fallbacks if missing
        if not sl or sl <= 0:
            sl = cls._apply_price_offset(entry, cls.FALLBACK_SL_PCT, side, is_sl=True)
            notes.append(f"SL fallback ({cls.FALLBACK_SL_PCT:.0%})")
        if not tp or tp <= 0:
            tp = cls._apply_price_offset(entry, cls.FALLBACK_TP_PCT, side, is_sl=False)
            notes.append(f"TP fallback ({cls.FALLBACK_TP_PCT:.0%})")

        fixed["stop_loss"], fixed["take_profit"] = sl, tp

        # Clamp SL to safety limits
        sl_dist = cls._calculate_distance(entry, sl, side, is_sl=True)
        if sl_dist < cls.SAFETY_MIN_SL_PCT:
            sl = cls._apply_price_offset(entry, cls.SAFETY_MIN_SL_PCT, side, is_sl=True)
            notes.append(f"SL min clamp ({cls.SAFETY_MIN_SL_PCT:.1%})")
        elif sl_dist > cls.SAFETY_MAX_SL_PCT:
            sl = cls._apply_price_offset(entry, cls.SAFETY_MAX_SL_PCT, side, is_sl=True)
            notes.append(f"SL max clamp ({cls.SAFETY_MAX_SL_PCT:.0%})")

        # Clamp TP to safety limits
        tp_dist = cls._calculate_distance(entry, tp, side, is_sl=False)
        if tp_dist < cls.SAFETY_MIN_TP_PCT:
            tp = cls._apply_price_offset(entry, cls.SAFETY_MIN_TP_PCT, side, is_sl=False)
            notes.append(f"TP min clamp ({cls.SAFETY_MIN_TP_PCT:.1%})")
        elif tp_dist > cls.SAFETY_MAX_TP_PCT:
            tp = cls._apply_price_offset(entry, cls.SAFETY_MAX_TP_PCT, side, is_sl=False)
            notes.append(f"TP max clamp ({cls.SAFETY_MAX_TP_PCT:.0%})")

        fixed["stop_loss"], fixed["take_profit"] = sl, tp

        # Check and fix price relationships
        valid_order = (sl < entry < tp) if side == "long" else (tp < entry < sl)
        if not valid_order and sl > 0 and tp > 0:
            fixed["stop_loss"], fixed["take_profit"] = tp, sl
            notes.append("SL/TP swapped")

        if notes:
            logger.info(f"{symbol} Safety applied: {'; '.join(notes)}")
            return True, f"Safety applied: {'; '.join(notes)}", fixed
        logger.debug(f"{symbol} LLM decision trusted as-is")
        return True, "LLM decision trusted", fixed


def validate_llm_decision(
    decision: dict, current_price: float, symbol: str = "UNKNOWN"
) -> Tuple[bool, str, dict]:
    """Convenience function to validate and fix an LLM decision."""
    return LLMDecisionValidator.validate_and_fix_decision(decision, current_price, symbol)
