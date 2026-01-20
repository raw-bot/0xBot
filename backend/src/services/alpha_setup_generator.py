"""
Alpha Setup Generator - Generate structured trading hypotheses.

Implements 0xBot-style "ALPHA SETUPS: MENU OF HYPOTHESES" with:
- Hypothesis A: Trend Following
- Hypothesis B: Mean Reversion / Fade
- Hypothesis C: Microstructure Edge
- Latent Risk identification
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TradingBias(Enum):
    """Directional bias for a trading hypothesis."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class AlphaHypothesis:
    """A single trading hypothesis with entry/exit logic."""

    hypothesis_type: str  # "trend_following", "mean_reversion", "microstructure"
    bias: TradingBias
    logic: str
    entry_condition: str
    target_zone: Optional[Tuple[float, float]]  # (low, high) price range
    invalidation: str


@dataclass
class AlphaSetup:
    """Complete alpha setup with 3 hypotheses and latent risk."""

    symbol: str
    trend_following: AlphaHypothesis
    mean_reversion: AlphaHypothesis
    microstructure: AlphaHypothesis
    latent_risk: str
    primary_bias: TradingBias  # Overall recommendation


class AlphaSetupGenerator:
    """
    Generate structured trading hypotheses per asset.

    For each asset, generate 3 hypotheses:
    1. Trend Following: Align with the current trend
    2. Mean Reversion: Fade extremes back to mean
    3. Microstructure: Edge from funding/OI/flow analysis

    Plus identify latent risks that could invalidate all setups.
    """

    def __init__(self) -> None:
        """Initialize the alpha setup generator."""
        pass

    def generate_setup(
        self,
        symbol: str,
        current_price: float,
        price_1h_ago: float,
        price_4h_ago: float,
        price_24h_ago: float,
        high_4h: float,
        low_4h: float,
        high_24h: float,
        low_24h: float,
        rsi_14: float,
        ema_20: float,
        ema_50: float,
        funding_rate: float,
        open_interest: float,
        avg_open_interest: float,
        volume_ratio: float = 1.0,
        narrative_classification: str = "NEUTRAL",
    ) -> AlphaSetup:
        """
        Generate complete alpha setup for a single asset.

        Args:
            symbol: Trading pair symbol
            current_price: Current asset price
            price_1h_ago: Price 1 hour ago
            price_4h_ago: Price 4 hours ago
            price_24h_ago: Price 24 hours ago
            high_4h: 4H high price
            low_4h: 4H low price
            high_24h: 24H high price
            low_24h: 24H low price
            rsi_14: 14-period RSI
            ema_20: 20 EMA value
            ema_50: 50 EMA value
            funding_rate: Current funding rate
            open_interest: Current OI
            avg_open_interest: Average OI for comparison
            volume_ratio: Volume vs average
            narrative_classification: From NarrativeAnalyzer

        Returns:
            AlphaSetup with all 3 hypotheses
        """
        coin_name = symbol.split("/")[0]

        # Calculate key metrics
        price_change_1h = (
            ((current_price - price_1h_ago) / price_1h_ago * 100) if price_1h_ago > 0 else 0
        )
        price_change_4h = (
            ((current_price - price_4h_ago) / price_4h_ago * 100) if price_4h_ago > 0 else 0
        )
        price_change_24h = (
            ((current_price - price_24h_ago) / price_24h_ago * 100) if price_24h_ago > 0 else 0
        )

        # Determine overall trend
        is_uptrend = current_price > ema_20 > ema_50
        is_downtrend = current_price < ema_20 < ema_50

        # Position in range
        range_4h = high_4h - low_4h if high_4h > low_4h else current_price * 0.02
        position_in_range = (current_price - low_4h) / range_4h if range_4h > 0 else 0.5

        # Generate each hypothesis
        trend_following = self._generate_trend_following(
            coin_name=coin_name,
            current_price=current_price,
            is_uptrend=is_uptrend,
            is_downtrend=is_downtrend,
            price_change_4h=price_change_4h,
            ema_20=ema_20,
            ema_50=ema_50,
            high_4h=high_4h,
            low_4h=low_4h,
        )

        mean_reversion = self._generate_mean_reversion(
            coin_name=coin_name,
            current_price=current_price,
            rsi_14=rsi_14,
            position_in_range=position_in_range,
            high_4h=high_4h,
            low_4h=low_4h,
            ema_20=ema_20,
        )

        microstructure = self._generate_microstructure(
            coin_name=coin_name,
            current_price=current_price,
            funding_rate=funding_rate,
            open_interest=open_interest,
            avg_open_interest=avg_open_interest,
            volume_ratio=volume_ratio,
            narrative_classification=narrative_classification,
        )

        latent_risk = self._identify_latent_risk(
            coin_name=coin_name,
            price_change_24h=price_change_24h,
            rsi_14=rsi_14,
            funding_rate=funding_rate,
            narrative_classification=narrative_classification,
        )

        # Determine primary bias
        primary_bias = self._determine_primary_bias(trend_following, mean_reversion, microstructure)

        return AlphaSetup(
            symbol=symbol,
            trend_following=trend_following,
            mean_reversion=mean_reversion,
            microstructure=microstructure,
            latent_risk=latent_risk,
            primary_bias=primary_bias,
        )

    def _generate_trend_following(
        self,
        coin_name: str,
        current_price: float,
        is_uptrend: bool,
        is_downtrend: bool,
        price_change_4h: float,
        ema_20: float,
        ema_50: float,
        high_4h: float,
        low_4h: float,
    ) -> AlphaHypothesis:
        """Generate trend following hypothesis."""

        if is_uptrend:
            return AlphaHypothesis(
                hypothesis_type="trend_following",
                bias=TradingBias.BULLISH,
                logic=f"4H uptrend with price above EMA20 ({ema_20:.2f}) > EMA50 ({ema_50:.2f}). Higher lows structure intact.",
                entry_condition=f"Buy dips toward ${ema_20:.2f} support or on breakout above ${high_4h:.2f}",
                target_zone=(high_4h, high_4h * 1.03),
                invalidation=f"Close below ${low_4h:.2f} or EMA50 breakdown",
            )
        elif is_downtrend:
            return AlphaHypothesis(
                hypothesis_type="trend_following",
                bias=TradingBias.BEARISH,
                logic=f"4H downtrend with price below EMA20 ({ema_20:.2f}) < EMA50 ({ema_50:.2f}). Lower highs structure intact.",
                entry_condition=f"Short rallies toward ${ema_20:.2f} resistance or on breakdown below ${low_4h:.2f}",
                target_zone=(low_4h * 0.97, low_4h),
                invalidation=f"Close above ${high_4h:.2f} or EMA50 reclaim",
            )
        else:
            return AlphaHypothesis(
                hypothesis_type="trend_following",
                bias=TradingBias.NEUTRAL,
                logic=f"No clear 4H trend. Price chopping between EMA20 ({ema_20:.2f}) and EMA50 ({ema_50:.2f}). Wait for breakout.",
                entry_condition=f"Wait for break above ${high_4h:.2f} or below ${low_4h:.2f} for trend confirmation",
                target_zone=None,
                invalidation="N/A - waiting for setup",
            )

    def _generate_mean_reversion(
        self,
        coin_name: str,
        current_price: float,
        rsi_14: float,
        position_in_range: float,
        high_4h: float,
        low_4h: float,
        ema_20: float,
    ) -> AlphaHypothesis:
        """Generate mean reversion / fade hypothesis."""

        # Overbought condition
        if rsi_14 > 70 or position_in_range > 0.85:
            return AlphaHypothesis(
                hypothesis_type="mean_reversion",
                bias=TradingBias.BEARISH,
                logic=f"RSI {rsi_14:.0f} overbought, price near 4H high ({position_in_range:.0%} of range). Mean reversion likely.",
                entry_condition=f"Short near ${high_4h:.2f} with tight stop above, target ${ema_20:.2f}",
                target_zone=(ema_20, current_price * 0.98),
                invalidation=f"Break above ${high_4h * 1.02:.2f} with volume",
            )

        # Oversold condition
        elif rsi_14 < 30 or position_in_range < 0.15:
            return AlphaHypothesis(
                hypothesis_type="mean_reversion",
                bias=TradingBias.BULLISH,
                logic=f"RSI {rsi_14:.0f} oversold, price near 4H low ({position_in_range:.0%} of range). Bounce likely.",
                entry_condition=f"Long near ${low_4h:.2f} with tight stop below, target ${ema_20:.2f}",
                target_zone=(current_price * 1.02, ema_20),
                invalidation=f"Break below ${low_4h * 0.98:.2f} with volume",
            )

        # Neutral - no extreme to fade
        else:
            return AlphaHypothesis(
                hypothesis_type="mean_reversion",
                bias=TradingBias.NEUTRAL,
                logic=f"RSI {rsi_14:.0f} neutral, price mid-range. No clear mean reversion setup.",
                entry_condition="Wait for extreme RSI (>70 or <30) or test of range edges",
                target_zone=None,
                invalidation="N/A - waiting for extreme",
            )

    def _generate_microstructure(
        self,
        coin_name: str,
        current_price: float,
        funding_rate: float,
        open_interest: float,
        avg_open_interest: float,
        volume_ratio: float,
        narrative_classification: str,
    ) -> AlphaHypothesis:
        """Generate microstructure-based hypothesis from funding/OI/flow."""

        oi_ratio = open_interest / avg_open_interest if avg_open_interest > 0 else 1.0

        # High negative funding = shorts crowded = potential squeeze
        if funding_rate < -0.01:
            return AlphaHypothesis(
                hypothesis_type="microstructure",
                bias=TradingBias.BULLISH,
                logic=f"Negative funding ({funding_rate:.4f}%) indicates crowded shorts. OI {oi_ratio:.1f}x average. Short squeeze potential.",
                entry_condition=f"Long on any support hold with stop below. Shorts are paying to stay short.",
                target_zone=(current_price * 1.02, current_price * 1.05),
                invalidation="Funding turns positive or breaks key support",
            )

        # High positive funding = longs crowded = potential dump
        elif funding_rate > 0.01:
            return AlphaHypothesis(
                hypothesis_type="microstructure",
                bias=TradingBias.BEARISH,
                logic=f"Positive funding ({funding_rate:.4f}%) indicates overleveraged longs. OI {oi_ratio:.1f}x average. Long squeeze risk.",
                entry_condition=f"Short any resistance rejection. Longs are paying premium to stay long.",
                target_zone=(current_price * 0.95, current_price * 0.98),
                invalidation="Funding turns negative or breaks key resistance",
            )

        # Check for narrative edge
        elif narrative_classification == "ABSORPTION":
            return AlphaHypothesis(
                hypothesis_type="microstructure",
                bias=TradingBias.BULLISH,
                logic=f"ABSORPTION pattern: bad news being absorbed → hidden demand. Funding neutral ({funding_rate:.4f}%).",
                entry_condition="Long dips as smart money accumulating into fear",
                target_zone=(current_price * 1.02, current_price * 1.05),
                invalidation="Price breaks to new lows on volume",
            )

        elif narrative_classification == "DISTRIBUTION":
            return AlphaHypothesis(
                hypothesis_type="microstructure",
                bias=TradingBias.BEARISH,
                logic=f"DISTRIBUTION pattern: good news being sold → hidden supply. Funding neutral ({funding_rate:.4f}%).",
                entry_condition="Short rallies as smart money distributing into strength",
                target_zone=(current_price * 0.95, current_price * 0.98),
                invalidation="Price breaks to new highs on volume",
            )

        # No microstructure edge
        else:
            return AlphaHypothesis(
                hypothesis_type="microstructure",
                bias=TradingBias.NEUTRAL,
                logic=f"Funding neutral ({funding_rate:.4f}%), OI {oi_ratio:.1f}x average. No clear flow edge.",
                entry_condition="Use trend/mean-reversion hypotheses instead",
                target_zone=None,
                invalidation="N/A - no microstructure edge",
            )

    def _identify_latent_risk(
        self,
        coin_name: str,
        price_change_24h: float,
        rsi_14: float,
        funding_rate: float,
        narrative_classification: str,
    ) -> str:
        """Identify risks that could invalidate all hypotheses."""

        risks = []

        # Macro risk
        if abs(price_change_24h) > 10:
            risks.append(
                f"High volatility ({price_change_24h:+.1f}% 24h) may continue; expect choppy action"
            )

        # Sentiment risk
        if narrative_classification in ["IMPULSE"]:
            risks.append("Fresh news impact still playing out; thesis may be premature")

        # Technical extreme risk
        if rsi_14 > 80 or rsi_14 < 20:
            risks.append(f"Extreme RSI ({rsi_14:.0f}) can stay extreme longer than expected")

        # Funding extreme risk
        if abs(funding_rate) > 0.05:
            risks.append(
                f"Extreme funding ({funding_rate:.3f}%) = high conviction positioning; squeeze could be violent"
            )

        if not risks:
            risks.append("Standard crypto volatility; watch broader market correlation (BTC, ETH)")

        return "; ".join(risks)

    def _determine_primary_bias(
        self, trend: AlphaHypothesis, mean_rev: AlphaHypothesis, micro: AlphaHypothesis
    ) -> TradingBias:
        """Determine overall primary bias from 3 hypotheses."""

        bias_scores: dict[TradingBias, float] = {TradingBias.BULLISH: 0.0, TradingBias.BEARISH: 0.0, TradingBias.NEUTRAL: 0.0}

        # Weight: Trend (2x) > Microstructure (1.5x) > Mean Reversion (1x)
        bias_scores[trend.bias] += 2.0
        bias_scores[micro.bias] += 1.5
        bias_scores[mean_rev.bias] += 1.0

        if bias_scores[TradingBias.BULLISH] > bias_scores[TradingBias.BEARISH]:
            return TradingBias.BULLISH
        elif bias_scores[TradingBias.BEARISH] > bias_scores[TradingBias.BULLISH]:
            return TradingBias.BEARISH
        else:
            return TradingBias.NEUTRAL

    def format_for_prompt(self, setups: Dict[str, AlphaSetup]) -> str:
        """
        Format alpha setups into 0xBot-style prompt section.

        Args:
            setups: Dict mapping symbols to AlphaSetup

        Returns:
            Formatted string for LLM prompt
        """
        lines = []
        lines.append("## 4. ALPHA SETUPS: MENU OF HYPOTHESES")
        lines.append("")

        for symbol, setup in setups.items():
            coin_name = symbol.split("/")[0]

            lines.append(f"### {coin_name}")
            lines.append("")

            # Trend Following
            tf = setup.trend_following
            lines.append(f"**Hypothesis A (Trend Following):**")
            lines.append(f"- Bias: {tf.bias.value.upper()}")
            lines.append(f"- Logic: {tf.logic}")
            lines.append(f"- Entry: {tf.entry_condition}")
            if tf.target_zone:
                lines.append(f"- Target: ${tf.target_zone[0]:,.2f} - ${tf.target_zone[1]:,.2f}")
            lines.append(f"- Invalidation: {tf.invalidation}")
            lines.append("")

            # Mean Reversion
            mr = setup.mean_reversion
            lines.append(f"**Hypothesis B (Mean Reversion/Fade):**")
            lines.append(f"- Bias: {mr.bias.value.upper()}")
            lines.append(f"- Logic: {mr.logic}")
            lines.append(f"- Entry: {mr.entry_condition}")
            if mr.target_zone:
                lines.append(f"- Target: ${mr.target_zone[0]:,.2f} - ${mr.target_zone[1]:,.2f}")
            lines.append(f"- Invalidation: {mr.invalidation}")
            lines.append("")

            # Microstructure
            ms = setup.microstructure
            lines.append(f"**Hypothesis C (Microstructure Edge):**")
            lines.append(f"- Bias: {ms.bias.value.upper()}")
            lines.append(f"- Logic: {ms.logic}")
            lines.append(f"- Entry: {ms.entry_condition}")
            if ms.target_zone:
                lines.append(f"- Target: ${ms.target_zone[0]:,.2f} - ${ms.target_zone[1]:,.2f}")
            lines.append(f"- Invalidation: {ms.invalidation}")
            lines.append("")

            # Latent Risk
            lines.append(f"**Latent Risk:** {setup.latent_risk}")
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)
