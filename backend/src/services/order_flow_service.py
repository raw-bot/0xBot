"""Order Flow Imbalance (OFI) service using delta-based microstructure analysis."""

from typing import Optional

import numpy as np

from ..core.logger import get_logger

logger = get_logger(__name__)


class OrderFlowService:
    """Service for calculating order flow imbalance and delta-based signals."""

    @staticmethod
    def calculate_delta(
        closes: list[float],
        opens: list[float],
        highs: list[float],
        lows: list[float],
        volumes: list[float],
    ) -> dict[str, list[Optional[float]]]:
        """Calculate delta (estimated order flow) from OHLCV data.

        Delta estimation formula:
        delta = volume * (close - open) / (high - low + 0.001)

        Positive delta = more buyers in control (bullish microstructure)
        Negative delta = more sellers in control (bearish microstructure)

        Args:
            closes: List of close prices
            opens: List of open prices
            highs: List of high prices
            lows: List of low prices
            volumes: List of volumes

        Returns:
            Dict with:
            - 'delta': Per-bar delta values
            - 'cum_delta': Cumulative delta over all bars
        """
        if not closes or len(closes) != len(opens) or len(closes) != len(volumes):
            logger.debug("[ORDER_FLOW] Insufficient data for delta calculation")
            return {"delta": [], "cum_delta": []}

        delta: list[Optional[float]] = []
        cum_delta = 0.0
        cumulative: list[Optional[float]] = []

        for i in range(len(closes)):
            close = closes[i]
            open_price = opens[i]
            high = highs[i]
            low = lows[i]
            volume = volumes[i]

            if (
                close is None
                or open_price is None
                or high is None
                or low is None
                or volume is None
            ):
                delta.append(None)
                cumulative.append(None)
                continue

            # Avoid division by zero
            hl_range = high - low
            if hl_range == 0:
                hl_range = 0.001

            # Delta = volume * (close - open) / (high - low)
            bar_delta = volume * (close - open_price) / (hl_range + 0.001)
            delta.append(bar_delta)

            # Cumulative delta
            cum_delta += bar_delta
            cumulative.append(cum_delta)

            if i == len(closes) - 1:
                logger.debug(
                    f"[ORDER_FLOW] Delta: {bar_delta:.0f}, Cumulative: {cum_delta:.0f}"
                )

        return {"delta": delta, "cum_delta": cumulative}

    @staticmethod
    def detect_ofi_signals(
        closes: list[float],
        opens: list[float],
        highs: list[float],
        lows: list[float],
        volumes: list[float],
    ) -> dict[str, bool | float]:
        """Detect order flow imbalance signals.

        Signals:
        - delta_positive: Current cumulative delta > 0 (buyers in control)
        - delta_surge: abs(delta) > 2*std_dev of recent deltas (extreme imbalance)
        - delta_bullish_cross: Cumulative delta crosses above 0 (bullish reversal)
        - delta_divergence: Delta increases while price consolidates (strength)

        Args:
            closes: List of close prices
            opens: List of open prices
            highs: List of high prices
            lows: List of low prices
            volumes: List of volumes

        Returns:
            Dict with signal names and boolean values
        """
        if not closes or len(closes) < 5:
            return {
                "delta_positive": False,
                "delta_surge": False,
                "delta_bullish_cross": False,
                "delta_bearish_cross": False,
                "delta_divergence": False,
                "delta_strength": 0.0,
            }

        # Calculate delta
        delta_result = OrderFlowService.calculate_delta(closes, opens, highs, lows, volumes)
        deltas = delta_result["delta"]
        cum_deltas = delta_result["cum_delta"]

        if not deltas or not cum_deltas:
            return {
                "delta_positive": False,
                "delta_surge": False,
                "delta_bullish_cross": False,
                "delta_bearish_cross": False,
                "delta_divergence": False,
                "delta_strength": 0.0,
            }

        # Get current values
        current_delta = deltas[-1] if deltas[-1] is not None else 0.0
        current_cum_delta = cum_deltas[-1] if cum_deltas[-1] is not None else 0.0
        prev_cum_delta = cum_deltas[-2] if len(cum_deltas) >= 2 and cum_deltas[-2] is not None else 0.0

        # Calculate statistics on recent delta (last 20 bars)
        recent_deltas = [d for d in deltas[-20:] if d is not None]
        delta_std = 0.0
        if len(recent_deltas) > 2:
            delta_std = float(np.std(recent_deltas))

        # Signal 1: Delta positive (buyers in control)
        delta_positive = current_cum_delta > 0

        # Signal 2: Delta surge (extreme imbalance)
        delta_surge = False
        if delta_std > 0:
            delta_surge = abs(current_delta) > 2 * delta_std

        # Signal 3: Bullish cross (cum_delta crosses above 0)
        delta_bullish_cross = prev_cum_delta <= 0 and current_cum_delta > 0

        # Signal 4: Bearish cross (cum_delta crosses below 0)
        delta_bearish_cross = prev_cum_delta >= 0 and current_cum_delta < 0

        # Signal 5: Delta divergence
        # Detect if delta is increasing while price is consolidating
        delta_divergence = False
        if len(deltas) >= 5:
            # Recent price change (should be small in consolidation)
            price_change = abs(closes[-1] - closes[-5])
            price_range = max(closes[-5:]) - min(closes[-5:]) if closes[-5:] else 1

            # Recent delta trend (should be increasing)
            recent_cum_delta_change = current_cum_delta - (cum_deltas[-5] if len(cum_deltas) >= 5 and cum_deltas[-5] is not None else 0)

            # Consolidation = small price change, strong delta = divergence
            if price_range < (closes[-1] * 0.01) and recent_cum_delta_change > (2 * delta_std if delta_std > 0 else 100):
                delta_divergence = True

        # Delta strength (normalized 0-1)
        delta_strength = 0.0
        if delta_std > 0:
            delta_strength = min(1.0, abs(current_delta) / (3 * delta_std))
        elif abs(current_delta) > 0:
            delta_strength = 0.5

        logger.debug(
            f"[ORDER_FLOW] Cum Delta: {current_cum_delta:.0f}, "
            f"Surge: {delta_surge}, Cross: {delta_bullish_cross}, "
            f"Strength: {delta_strength:.0%}"
        )

        return {
            "delta_positive": delta_positive,
            "delta_surge": delta_surge,
            "delta_bullish_cross": delta_bullish_cross,
            "delta_bearish_cross": delta_bearish_cross,
            "delta_divergence": delta_divergence,
            "delta_strength": delta_strength,
        }

    @staticmethod
    def get_ofi_values(
        closes: list[float],
        opens: list[float],
        highs: list[float],
        lows: list[float],
        volumes: list[float],
    ) -> dict[str, list[Optional[float]] | float]:
        """Get OFI indicator values for charting/analysis.

        Returns delta and cumulative delta for visualization.

        Args:
            closes: List of close prices
            opens: List of open prices
            highs: List of high prices
            lows: List of low prices
            volumes: List of volumes

        Returns:
            Dict with 'delta' and 'cum_delta' arrays, plus current values
        """
        delta_result = OrderFlowService.calculate_delta(closes, opens, highs, lows, volumes)

        current_delta = 0.0
        current_cum_delta = 0.0

        if delta_result["delta"] and delta_result["delta"][-1] is not None:
            current_delta = delta_result["delta"][-1]

        if delta_result["cum_delta"] and delta_result["cum_delta"][-1] is not None:
            current_cum_delta = delta_result["cum_delta"][-1]

        return {
            "delta": delta_result["delta"],
            "cum_delta": delta_result["cum_delta"],
            "current_delta": current_delta,
            "current_cum_delta": current_cum_delta,
        }
