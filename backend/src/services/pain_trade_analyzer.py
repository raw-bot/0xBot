"""
Pain Trade Analyzer Service - Detect liquidation hunting opportunities.

Implements 0xBot-style "Pain Trade" analysis:
- Squeeze Watch (High OI + Counter-Trend Funding)
- Liquidity Traps / Crowded Trades detection
- Trigger Levels for liquidations
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SqueezeType(Enum):
    """Type of squeeze setup detected."""

    LONG_SQUEEZE = "LONG_SQUEEZE"  # Positive funding + price falling = longs squeezed
    SHORT_SQUEEZE = "SHORT_SQUEEZE"  # Negative funding + price rising = shorts squeezed
    NO_SQUEEZE = "NO_SQUEEZE"  # No clear squeeze setup
    POTENTIAL_LONG = "POTENTIAL_LONG"  # Conditions forming for long squeeze
    POTENTIAL_SHORT = "POTENTIAL_SHORT"  # Conditions forming for short squeeze


@dataclass
class SqueezeAnalysis:
    """Analysis of squeeze potential for an asset."""

    symbol: str
    squeeze_type: SqueezeType
    funding_rate: float
    open_interest: float
    oi_trend: str  # "rising", "falling", "stable"
    price_trend: str  # "up", "down", "range"
    squeeze_probability: float  # 0.0 to 1.0
    trigger_level_up: Optional[float]
    trigger_level_down: Optional[float]
    interpretation: str


@dataclass
class CrowdedTradeAnalysis:
    """Analysis of crowded/obvious trades that may trap traders."""

    trade_description: str
    is_crowded: bool
    trap_risk: str  # "high", "medium", "low"
    explanation: str


class PainTradeAnalyzer:
    """
    Detect squeeze setups and liquidity traps.

    The "pain trade" is the move that hurts the most traders.
    This service identifies:
    1. High OI + Counter-Trend Funding = Squeeze Setup
    2. Crowded "obvious" trades that may be traps
    3. Key trigger levels for liquidations
    """

    # Thresholds for analysis
    HIGH_FUNDING_THRESHOLD = 0.01  # 0.01% per 8h = elevated
    EXTREME_FUNDING_THRESHOLD = 0.05  # 0.05% per 8h = extreme
    HIGH_OI_PERCENTILE = 0.80  # Top 20% is "high OI"

    def __init__(self) -> None:
        """Initialize the pain trade analyzer."""
        pass

    def analyze_squeeze_potential(
        self,
        symbol: str,
        funding_rate: float,
        open_interest: float,
        avg_open_interest: float,
        current_price: float,
        price_1h_ago: float,
        price_4h_ago: float,
        high_4h: float,
        low_4h: float,
    ) -> SqueezeAnalysis:
        """
        Analyze squeeze potential for a single asset.

        Args:
            symbol: Trading pair symbol
            funding_rate: Current funding rate (as percentage, e.g., 0.01 for 0.01%)
            open_interest: Current open interest in contracts/USD
            avg_open_interest: Average OI for comparison
            current_price: Current asset price
            price_1h_ago: Price 1 hour ago
            price_4h_ago: Price 4 hours ago
            high_4h: 4H high price
            low_4h: 4H low price

        Returns:
            SqueezeAnalysis dataclass with full analysis
        """
        # Determine OI trend
        oi_ratio = open_interest / avg_open_interest if avg_open_interest > 0 else 1.0
        if oi_ratio > 1.1:
            oi_trend = "rising"
        elif oi_ratio < 0.9:
            oi_trend = "falling"
        else:
            oi_trend = "stable"

        # Determine price trend
        price_change_1h = (
            ((current_price - price_1h_ago) / price_1h_ago * 100) if price_1h_ago > 0 else 0
        )
        price_change_4h = (
            ((current_price - price_4h_ago) / price_4h_ago * 100) if price_4h_ago > 0 else 0
        )

        if price_change_1h > 0.5:
            price_trend = "up"
        elif price_change_1h < -0.5:
            price_trend = "down"
        else:
            price_trend = "range"

        # Calculate trigger levels (support/resistance that could trigger liquidations)
        price_range = high_4h - low_4h if high_4h > low_4h else current_price * 0.02
        trigger_level_up = high_4h + (price_range * 0.1)  # Break above triggers shorts
        trigger_level_down = low_4h - (price_range * 0.1)  # Break below triggers longs

        # Analyze squeeze type based on funding vs price direction
        squeeze_type, squeeze_prob, interpretation = self._classify_squeeze(
            funding_rate=funding_rate,
            price_trend=price_trend,
            oi_ratio=oi_ratio,
            price_change_1h=price_change_1h,
        )

        return SqueezeAnalysis(
            symbol=symbol,
            squeeze_type=squeeze_type,
            funding_rate=funding_rate,
            open_interest=open_interest,
            oi_trend=oi_trend,
            price_trend=price_trend,
            squeeze_probability=squeeze_prob,
            trigger_level_up=trigger_level_up,
            trigger_level_down=trigger_level_down,
            interpretation=interpretation,
        )

    def _classify_squeeze(
        self, funding_rate: float, price_trend: str, oi_ratio: float, price_change_1h: float
    ) -> Tuple[SqueezeType, float, str]:
        """
        Classify the type of squeeze setup.

        High OI + Counter-Trend Funding = Squeeze Setup
        - Positive funding + price down = Long squeeze risk
        - Negative funding + price up = Short squeeze potential

        Returns:
            Tuple of (SqueezeType, probability, interpretation)
        """
        # Check for extreme funding (clear signal)
        if abs(funding_rate) > self.EXTREME_FUNDING_THRESHOLD:
            if funding_rate > 0 and price_trend in ["down", "range"]:
                # Longs paying + price dropping = Long squeeze underway
                return (
                    SqueezeType.LONG_SQUEEZE,
                    min(0.85, 0.5 + oi_ratio * 0.2),
                    f"Longs paying {funding_rate:.3f}% into weak price → Long squeeze risk HIGH",
                )
            elif funding_rate < 0 and price_trend in ["up", "range"]:
                # Shorts paying + price rising = Short squeeze underway
                return (
                    SqueezeType.SHORT_SQUEEZE,
                    min(0.85, 0.5 + oi_ratio * 0.2),
                    f"Shorts paying {abs(funding_rate):.3f}% into strength → Short squeeze risk HIGH",
                )

        # Check for elevated funding (potential setup)
        if abs(funding_rate) > self.HIGH_FUNDING_THRESHOLD:
            if funding_rate > 0 and price_trend == "down":
                return (
                    SqueezeType.POTENTIAL_LONG,
                    min(0.65, 0.3 + oi_ratio * 0.2),
                    f"Longs still paying while price weakens → Potential long squeeze forming",
                )
            elif funding_rate > 0 and price_trend == "up":
                return (
                    SqueezeType.NO_SQUEEZE,
                    0.2,
                    f"Longs paying, price up → Trend aligned, no immediate squeeze",
                )
            elif funding_rate < 0 and price_trend == "up":
                return (
                    SqueezeType.POTENTIAL_SHORT,
                    min(0.65, 0.3 + oi_ratio * 0.2),
                    f"Shorts paying while price rises → Potential short squeeze forming",
                )
            elif funding_rate < 0 and price_trend == "down":
                return (
                    SqueezeType.NO_SQUEEZE,
                    0.2,
                    f"Shorts paying, price down → Trend aligned, no immediate squeeze",
                )

        # No significant funding imbalance
        return (
            SqueezeType.NO_SQUEEZE,
            0.1,
            f"Funding neutral ({funding_rate:.4f}%), no squeeze signal",
        )

    def detect_crowded_trades(
        self,
        symbol: str,
        funding_rate: float,
        price_change_24h: float,
        narrative_sentiment: str,
        volume_ratio: float,
    ) -> List[CrowdedTradeAnalysis]:
        """
        Detect "obvious" trades that may be crowded/traps.

        Args:
            symbol: Trading symbol
            funding_rate: Current funding rate
            price_change_24h: 24h price change percentage
            narrative_sentiment: News sentiment ('positive', 'negative', 'neutral')
            volume_ratio: Current volume vs average

        Returns:
            List of CrowdedTradeAnalysis for detected crowded trades
        """
        crowded_trades = []
        coin_name = symbol.split("/")[0]

        # Check for "Chase the rally" trap
        if price_change_24h > 5 and funding_rate > 0.01:
            crowded_trades.append(
                CrowdedTradeAnalysis(
                    trade_description=f"Long {coin_name} after +{price_change_24h:.1f}% move",
                    is_crowded=True,
                    trap_risk="high",
                    explanation=f"Late longs chasing after large move; elevated funding ({funding_rate:.3f}%) = crowded",
                )
            )

        # Check for "Catch the falling knife" trap
        if price_change_24h < -5 and funding_rate < -0.01:
            crowded_trades.append(
                CrowdedTradeAnalysis(
                    trade_description=f"Short {coin_name} after {price_change_24h:.1f}% drop",
                    is_crowded=True,
                    trap_risk="high",
                    explanation=f"Late shorts piling in after large drop; negative funding = squeeze risk",
                )
            )

        # Check for "Fade the news" trap
        if narrative_sentiment == "positive" and price_change_24h < -2:
            crowded_trades.append(
                CrowdedTradeAnalysis(
                    trade_description=f"Short {coin_name} because price down despite good news",
                    is_crowded=funding_rate < 0,
                    trap_risk="medium" if funding_rate < 0 else "low",
                    explanation="Fading positive news can work, but check if distribution is real vs shakeout",
                )
            )
        elif narrative_sentiment == "negative" and price_change_24h > 2:
            crowded_trades.append(
                CrowdedTradeAnalysis(
                    trade_description=f"Short {coin_name} because 'it must go down eventually'",
                    is_crowded=funding_rate < 0,
                    trap_risk="high" if funding_rate < -0.01 else "medium",
                    explanation="Fighting absorption of bad news; shorts may be fuel for further upside",
                )
            )

        return crowded_trades

    def format_for_prompt(
        self,
        squeeze_analyses: Dict[str, SqueezeAnalysis],
        crowded_trades: Dict[str, List[CrowdedTradeAnalysis]],
    ) -> str:
        """
        Format pain trade analysis into 0xBot-style prompt section.

        Args:
            squeeze_analyses: Dict mapping symbols to SqueezeAnalysis
            crowded_trades: Dict mapping symbols to list of CrowdedTradeAnalysis

        Returns:
            Formatted string for LLM prompt
        """
        lines = []
        lines.append('## 3. THE "PAIN TRADE" (LIQUIDATION HUNTING)')
        lines.append("")

        # Squeeze Watch section
        lines.append("### Squeeze Watch (High OI + Counter-Trend Funding)")
        lines.append("")

        has_squeeze = False
        for symbol, analysis in squeeze_analyses.items():
            coin_name = symbol.split("/")[0]

            if analysis.squeeze_type != SqueezeType.NO_SQUEEZE:
                has_squeeze = True
                lines.append(f"**{coin_name}:**")
                lines.append(
                    f"- Funding: {analysis.funding_rate:+.4f}% | OI: {analysis.open_interest:,.0f} ({analysis.oi_trend})"
                )
                lines.append(f"- Price Trend: {analysis.price_trend}")
                lines.append(
                    f"- Signal: **{analysis.squeeze_type.value}** (Prob: {analysis.squeeze_probability:.0%})"
                )
                lines.append(f"- {analysis.interpretation}")
                lines.append("")

        if not has_squeeze:
            lines.append("No clear squeeze setups detected. Funding near neutral across assets.")
            lines.append("")

        # Trigger Levels section
        lines.append("### Key Trigger Levels")
        lines.append("")

        for symbol, analysis in squeeze_analyses.items():
            coin_name = symbol.split("/")[0]
            lines.append(
                f"- **{coin_name}**: Below ${analysis.trigger_level_down:,.2f} = long liquidation zone | Above ${analysis.trigger_level_up:,.2f} = short squeeze zone"
            )
        lines.append("")

        # Crowded Trades section
        lines.append("### Crowded Obvious Trades (Trap Risk)")
        lines.append("")

        has_crowded = False
        for symbol, trades in crowded_trades.items():
            for trade in trades:
                if trade.is_crowded:
                    has_crowded = True
                    lines.append(
                        f'- "{trade.trade_description}" → **{trade.trap_risk.upper()} TRAP RISK**'
                    )
                    lines.append(f"  {trade.explanation}")
                    lines.append("")

        if not has_crowded:
            lines.append("No obviously crowded trades detected.")
            lines.append("")

        return "\n".join(lines)
