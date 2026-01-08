"""
FVG (Fair Value Gap) Detector Service

Implements ICT-style Fair Value Gap detection with:
1. Detection - 3-candle pattern identification
2. Freshness - Track mitigated vs unmitigated FVGs
3. Premium/Discount - Zone positioning via Fibonacci
4. Confirmation - Entry validation at 0.50 level
5. Confluence - Scoring with Breaker/Order Blocks
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Literal, Optional, Tuple

logger = logging.getLogger(__name__)


class FVGType(Enum):
    BULLISH = "bullish"  # Gap up - price should return to fill
    BEARISH = "bearish"  # Gap down - price should return to fill


class ZoneType(Enum):
    PREMIUM = "premium"  # Upper 50% of range - sell zone
    DISCOUNT = "discount"  # Lower 50% of range - buy zone
    EQUILIBRIUM = "equilibrium"  # At 50%


@dataclass
class FVG:
    """Fair Value Gap data structure."""

    type: FVGType
    top: float  # Upper boundary of gap
    bottom: float  # Lower boundary of gap
    middle: float  # 0.50 level (critical S/R)
    timestamp: datetime  # When the FVG formed
    timeframe: str  # Timeframe it was detected on
    size_pct: float  # Gap size as % of price
    impulse_strength: float  # How strong the impulse candle was
    is_mitigated: bool = False  # Has price touched this FVG?
    confluence_score: float = 0.0  # Bonus from alignments
    formation_candles: List[Dict] = field(default_factory=list)

    @property
    def size(self) -> float:
        """Absolute size of the gap."""
        return abs(self.top - self.bottom)

    def contains_price(self, price: float) -> bool:
        """Check if a price is within the FVG zone."""
        return self.bottom <= price <= self.top

    def is_above_middle(self, price: float) -> bool:
        """Check if price is above the 0.50 level."""
        return price > self.middle


class FVGDetectorService:
    """
    Service for detecting and analyzing Fair Value Gaps.

    Based on ICT (Inner Circle Trader) concepts:
    - FVG forms when impulse candle leaves gap between surrounding wicks
    - Market tends to return and fill these gaps
    - First touch (unmitigated) has highest probability
    """

    # Configuration
    MIN_FVG_SIZE_PCT = 0.001  # 0.1% minimum gap size
    ATR_PERIOD = 14
    IMPULSE_MULTIPLIER = 1.5  # Candle body must be > 1.5x ATR
    MAX_FVG_AGE_CANDLES = 50  # Don't track old FVGs

    def __init__(self):
        self.active_fvgs: Dict[str, List[FVG]] = {}  # symbol -> list of FVGs

    def detect_fvgs(self, symbol: str, candles: List[Dict], timeframe: str = "1h") -> List[FVG]:
        """
        Detect Fair Value Gaps in candle data.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            candles: List of OHLCV candles (oldest first)
                     Each candle: {open, high, low, close, volume, timestamp}
            timeframe: Timeframe of candles

        Returns:
            List of detected FVGs
        """
        if len(candles) < 3:
            return []

        detected = []
        atr = self._calculate_atr(candles)

        # Scan for 3-candle patterns
        for i in range(1, len(candles) - 1):
            candle_prev = candles[i - 1]  # n-1
            candle_impulse = candles[i]  # n (impulse)
            candle_next = candles[i + 1]  # n+1

            # Check for bullish FVG (gap up)
            bullish_fvg = self._check_bullish_fvg(
                candle_prev, candle_impulse, candle_next, atr, timeframe
            )
            if bullish_fvg:
                detected.append(bullish_fvg)

            # Check for bearish FVG (gap down)
            bearish_fvg = self._check_bearish_fvg(
                candle_prev, candle_impulse, candle_next, atr, timeframe
            )
            if bearish_fvg:
                detected.append(bearish_fvg)

        # Update stored FVGs for symbol
        self.active_fvgs[symbol] = detected

        logger.info(f"FVG | {symbol} | Detected {len(detected)} FVGs on {timeframe}")

        return detected

    def _check_bullish_fvg(
        self, prev: Dict, impulse: Dict, next_c: Dict, atr: float, timeframe: str
    ) -> Optional[FVG]:
        """
        Check for bullish FVG (gap up).

        Bullish FVG: Gap between prev candle HIGH and next candle LOW
        """
        prev_high = prev.get("high", 0)
        next_low = next_c.get("low", 0)

        # Gap exists if next candle's low > prev candle's high
        if next_low <= prev_high:
            return None

        gap_size = next_low - prev_high
        current_price = impulse.get("close", 0)

        if current_price <= 0:
            return None

        gap_pct = gap_size / current_price

        # Filter: Gap must be significant
        if gap_pct < self.MIN_FVG_SIZE_PCT:
            return None

        # Filter: Impulse candle must be strong
        impulse_body = abs(impulse.get("close", 0) - impulse.get("open", 0))
        if atr > 0 and impulse_body < atr * self.IMPULSE_MULTIPLIER:
            return None

        # Valid FVG found
        return FVG(
            type=FVGType.BULLISH,
            top=next_low,
            bottom=prev_high,
            middle=(next_low + prev_high) / 2,
            timestamp=(
                datetime.fromisoformat(impulse.get("timestamp", datetime.utcnow().isoformat()))
                if isinstance(impulse.get("timestamp"), str)
                else datetime.utcnow()
            ),
            timeframe=timeframe,
            size_pct=gap_pct,
            impulse_strength=impulse_body / atr if atr > 0 else 1.0,
            formation_candles=[prev, impulse, next_c],
        )

    def _check_bearish_fvg(
        self, prev: Dict, impulse: Dict, next_c: Dict, atr: float, timeframe: str
    ) -> Optional[FVG]:
        """
        Check for bearish FVG (gap down).

        Bearish FVG: Gap between prev candle LOW and next candle HIGH
        """
        prev_low = prev.get("low", 0)
        next_high = next_c.get("high", 0)

        # Gap exists if next candle's high < prev candle's low
        if next_high >= prev_low:
            return None

        gap_size = prev_low - next_high
        current_price = impulse.get("close", 0)

        if current_price <= 0:
            return None

        gap_pct = gap_size / current_price

        # Filter: Gap must be significant
        if gap_pct < self.MIN_FVG_SIZE_PCT:
            return None

        # Filter: Impulse candle must be strong
        impulse_body = abs(impulse.get("close", 0) - impulse.get("open", 0))
        if atr > 0 and impulse_body < atr * self.IMPULSE_MULTIPLIER:
            return None

        # Valid FVG found
        return FVG(
            type=FVGType.BEARISH,
            top=prev_low,
            bottom=next_high,
            middle=(prev_low + next_high) / 2,
            timestamp=(
                datetime.fromisoformat(impulse.get("timestamp", datetime.utcnow().isoformat()))
                if isinstance(impulse.get("timestamp"), str)
                else datetime.utcnow()
            ),
            timeframe=timeframe,
            size_pct=gap_pct,
            impulse_strength=impulse_body / atr if atr > 0 else 1.0,
            formation_candles=[prev, impulse, next_c],
        )

    def _calculate_atr(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate Average True Range."""
        if len(candles) < period:
            return 0.0

        true_ranges = []
        for i in range(1, len(candles)):
            high = candles[i].get("high", 0)
            low = candles[i].get("low", 0)
            prev_close = candles[i - 1].get("close", 0)

            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            true_ranges.append(tr)

        if len(true_ranges) < period:
            return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0

        return sum(true_ranges[-period:]) / period

    def update_mitigation(self, symbol: str, current_price: float) -> None:
        """
        Update FVG mitigation status based on current price.

        An FVG becomes "mitigated" when price touches it for the first time.
        """
        if symbol not in self.active_fvgs:
            return

        for fvg in self.active_fvgs[symbol]:
            if not fvg.is_mitigated and fvg.contains_price(current_price):
                fvg.is_mitigated = True
                logger.info(
                    f"FVG | {symbol} | {fvg.type.value} FVG MITIGATED at "
                    f"${current_price:,.2f} (zone: ${fvg.bottom:,.2f}-${fvg.top:,.2f})"
                )

    def get_unmitigated_fvgs(self, symbol: str) -> List[FVG]:
        """Get only fresh, unmitigated FVGs for a symbol."""
        if symbol not in self.active_fvgs:
            return []
        return [f for f in self.active_fvgs[symbol] if not f.is_mitigated]

    def get_premium_discount_zone(
        self, price: float, range_high: float, range_low: float
    ) -> Tuple[ZoneType, float]:
        """
        Determine if price is in Premium or Discount zone.

        Uses Fibonacci-style division:
        - Above 50% of range = Premium (sell zone)
        - Below 50% of range = Discount (buy zone)

        Returns:
            Tuple of (zone_type, percentage in range)
        """
        if range_high <= range_low:
            return ZoneType.EQUILIBRIUM, 0.5

        range_size = range_high - range_low
        position = (price - range_low) / range_size

        if position > 0.5:
            return ZoneType.PREMIUM, position
        elif position < 0.5:
            return ZoneType.DISCOUNT, position
        else:
            return ZoneType.EQUILIBRIUM, 0.5

    def validate_entry(
        self, fvg: FVG, current_candle: Dict, intended_side: Literal["long", "short"]
    ) -> Tuple[bool, str]:
        """
        Validate entry based on candle reaction at FVG.

        Rules:
        - Ideal: Price wicks into FVG but body closes outside (rejection)
        - Acceptable: Body closes inside but above 0.50 for longs / below for shorts
        - No-Go: Body closes on wrong side of 0.50

        Returns:
            Tuple of (is_valid, reason)
        """
        candle_close = current_candle.get("close", 0)
        candle_low = current_candle.get("low", 0)
        candle_high = current_candle.get("high", 0)

        # Check if candle touched the FVG
        touched = candle_low <= fvg.top and candle_high >= fvg.bottom

        if not touched:
            return False, "Candle did not touch FVG zone"

        # For LONG entries (bullish FVG in discount)
        if intended_side == "long":
            if fvg.type != FVGType.BULLISH:
                return False, "Wrong FVG type for long entry"

            # Ideal: Close above FVG (rejection)
            if candle_close > fvg.top:
                return True, "Strong rejection - close above FVG ✓"

            # Acceptable: Close inside but above middle
            if fvg.is_above_middle(candle_close):
                return True, "Acceptable - close above 0.50 level ✓"

            # No-go: Close below middle
            return False, "Close below 0.50 level - weak reaction"

        # For SHORT entries (bearish FVG in premium)
        else:
            if fvg.type != FVGType.BEARISH:
                return False, "Wrong FVG type for short entry"

            # Ideal: Close below FVG (rejection)
            if candle_close < fvg.bottom:
                return True, "Strong rejection - close below FVG ✓"

            # Acceptable: Close inside but below middle
            if not fvg.is_above_middle(candle_close):
                return True, "Acceptable - close below 0.50 level ✓"

            # No-go: Close above middle
            return False, "Close above 0.50 level - weak reaction"

    def calculate_confluence_score(
        self,
        fvg: FVG,
        has_breaker_block: bool = False,
        has_order_block: bool = False,
        has_bos: bool = False,
    ) -> float:
        """
        Calculate confluence score for FVG setup quality.

        Base score = 1.0
        +0.3 for Breaker Block alignment
        +0.3 for Order Block alignment
        +0.2 for BOS (Break of Structure)
        +0.1 per 0.5x impulse strength above threshold

        Returns:
            Confluence score (1.0 to 2.0+)
        """
        score = 1.0

        if has_breaker_block:
            score += 0.3

        if has_order_block:
            score += 0.3

        if has_bos:
            score += 0.2

        # Bonus for strong impulse
        if fvg.impulse_strength > 1.5:
            bonus = min((fvg.impulse_strength - 1.5) * 0.2, 0.3)
            score += bonus

        fvg.confluence_score = score
        return score

    def format_for_prompt(self, symbol: str, range_high: float, range_low: float) -> str:
        """
        Format FVG analysis for inclusion in LLM prompt.
        """
        fvgs = self.get_unmitigated_fvgs(symbol)

        if not fvgs:
            return f"### FVG Analysis ({symbol})\nNo unmitigated FVGs detected.\n"

        lines = [f"### FVG Analysis ({symbol})", ""]

        for fvg in fvgs[:3]:  # Limit to 3 most relevant
            zone, pos = self.get_premium_discount_zone(fvg.middle, range_high, range_low)

            emoji = "🟢" if fvg.type == FVGType.BULLISH else "🔴"
            zone_emoji = "📈" if zone == ZoneType.DISCOUNT else "📉"

            lines.append(f"**{emoji} {fvg.type.value.upper()} FVG** ({fvg.timeframe})")
            lines.append(f"  - Zone: ${fvg.bottom:,.2f} - ${fvg.top:,.2f}")
            lines.append(f"  - Middle (0.50): ${fvg.middle:,.2f}")
            lines.append(f"  - Position: {zone_emoji} {zone.value.upper()} ({pos:.1%})")
            lines.append(
                f"  - Freshness: {'🆕 UNMITIGATED' if not fvg.is_mitigated else '⚠️ Mitigated'}"
            )
            lines.append(f"  - Impulse: {fvg.impulse_strength:.1f}x ATR")
            lines.append("")

        # Add trading guidance
        lines.append("**FVG Trading Rules:**")
        lines.append("- LONG: Only in DISCOUNT zone, bullish FVG, close above 0.50")
        lines.append("- SHORT: Only in PREMIUM zone, bearish FVG, close below 0.50")
        lines.append("- AVOID: Mitigated FVGs (already touched)")
        lines.append("")

        return "\n".join(lines)


# Singleton instance
_fvg_detector: Optional[FVGDetectorService] = None


def get_fvg_detector() -> FVGDetectorService:
    """Get singleton FVG detector instance."""
    global _fvg_detector
    if _fvg_detector is None:
        _fvg_detector = FVGDetectorService()
    return _fvg_detector
