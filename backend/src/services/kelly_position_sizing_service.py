"""
Kelly Criterion-based position sizing for optimal growth.

The Kelly formula: f* = (p*W - (1-p)*L) / W
Where:
  f* = Fraction of capital to risk
  p = Win probability (0-1)
  W = Average win size (as multiple of stake)
  L = Average loss size (as multiple of stake)

For example, if win rate is 55%, avg win is +5%, avg loss is -2%:
  f* = (0.55 * 5 - 0.45 * 2) / 5 = (2.75 - 0.9) / 5 = 0.37 = 37%

But professional traders use 1/4 Kelly (quarter Kelly) for safety.
"""

from decimal import Decimal
from typing import Tuple, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ..models import Trade, Bot, PositionStatus
import logging

logger = logging.getLogger(__name__)


class KellyPositionSizingService:
    """Calculate position size using Kelly Criterion based on historical performance."""

    # Use 1/4 Kelly for safety (less aggressive than full Kelly)
    KELLY_FRACTION = Decimal("0.25")

    # Min/max bounds for position size
    MIN_SIZE_PCT = Decimal("0.02")    # 2% minimum
    MAX_SIZE_PCT = Decimal("0.25")    # 25% maximum

    # Min trades required for statistical validity
    MIN_TRADES_FOR_KELLY = 20

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def calculate_position_size(
        self,
        bot_id: str,
        base_size_pct: Decimal = Decimal("0.10"),
        risk_per_trade_pct: Decimal = Decimal("0.02"),
    ) -> Tuple[Decimal, str]:
        """
        Calculate optimal position size using Kelly Criterion.

        Args:
            bot_id: Bot identifier
            base_size_pct: Base position size as % of capital (fallback if not enough data)
            risk_per_trade_pct: Risk per trade as % of capital (e.g., 2%)

        Returns:
            Tuple of (position_size_pct, reasoning)
        """
        try:
            # Get recent trades for analysis
            trades = await self._get_recent_trades(bot_id, lookback_days=90)

            if len(trades) < self.MIN_TRADES_FOR_KELLY:
                reasoning = f"Not enough trades ({len(trades)}) for Kelly, using base size"
                return base_size_pct, reasoning

            # Calculate win rate and average win/loss
            win_rate, avg_win_pct, avg_loss_pct = self._analyze_trades(trades)

            if win_rate < Decimal("0.30"):  # Less than 30% win rate = bad strategy
                size = base_size_pct * Decimal("0.5")
                reasoning = f"Low win rate ({win_rate:.1%}), using 50% of base size"
                return max(size, self.MIN_SIZE_PCT), reasoning

            # Calculate Kelly fraction
            kelly_pct = self._calculate_kelly(win_rate, avg_win_pct, avg_loss_pct)

            # Apply 1/4 Kelly for safety
            kelly_safe = kelly_pct * self.KELLY_FRACTION

            # Bound between min/max
            size = max(self.MIN_SIZE_PCT, min(kelly_safe, self.MAX_SIZE_PCT))

            reasoning = (
                f"Kelly: {kelly_pct:.1%} (1/4 safety) = {kelly_safe:.1%} "
                f"→ {size:.1%} "
                f"(WR:{win_rate:.1%} W:{avg_win_pct:.1%} L:{avg_loss_pct:.1%})"
            )

            return size, reasoning

        except Exception as e:
            logger.error(f"Error calculating Kelly position size: {e}")
            return base_size_pct, f"Error in Kelly calc: {str(e)}"

    def _calculate_kelly(
        self,
        win_rate: Decimal,
        avg_win_pct: Decimal,
        avg_loss_pct: Decimal
    ) -> Decimal:
        """
        Kelly formula: f* = (p*W - (1-p)*L) / W

        Args:
            win_rate: Probability of winning (0.0 - 1.0)
            avg_win_pct: Average win as decimal (e.g., 0.05 for 5%)
            avg_loss_pct: Average loss as decimal (e.g., 0.02 for 2%)

        Returns:
            Optimal Kelly fraction
        """
        if avg_win_pct <= 0 or avg_loss_pct <= 0:
            return Decimal("0.10")  # Safety fallback

        # Kelly = (win% * avg_win - loss% * avg_loss) / avg_win
        # Where win% = win_rate, loss% = 1 - win_rate

        numerator = (win_rate * avg_win_pct) - ((Decimal("1.0") - win_rate) * avg_loss_pct)
        denominator = avg_win_pct

        kelly = numerator / denominator

        # Ensure positive and reasonable
        kelly = max(Decimal("0.01"), min(kelly, Decimal("1.0")))

        return kelly

    def _analyze_trades(self, trades: list) -> Tuple[Decimal, Decimal, Decimal]:
        """
        Analyze trade history to get win rate, avg win, avg loss.

        Returns:
            (win_rate, avg_win_pct, avg_loss_pct)
        """
        if not trades:
            return Decimal("0.50"), Decimal("0.05"), Decimal("0.02")

        wins = [t for t in trades if t.realized_pnl > 0]
        losses = [t for t in trades if t.realized_pnl < 0]

        win_rate = Decimal(len(wins)) / Decimal(len(trades))

        # Average win as % of entry value
        avg_win_pct = (
            Decimal(sum(t.realized_pnl for t in wins)) / Decimal(len(wins))
            / Decimal(sum(t.entry_price * t.quantity for t in wins) / len(wins))
            if wins else Decimal("0.05")
        )

        # Average loss as % of entry value (absolute)
        avg_loss_pct = (
            abs(Decimal(sum(t.realized_pnl for t in losses)) / Decimal(len(losses)))
            / Decimal(sum(t.entry_price * t.quantity for t in losses) / len(losses))
            if losses else Decimal("0.02")
        )

        return win_rate, avg_win_pct, avg_loss_pct

    async def _get_recent_trades(self, bot_id: str, lookback_days: int = 90) -> list:
        """Get recent closed trades for analysis."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

            stmt = select(Trade).where(
                and_(
                    Trade.bot_id == bot_id,
                    Trade.created_at >= cutoff_date,
                    Trade.realized_pnl != 0  # Only closed trades
                )
            ).order_by(Trade.created_at.desc())

            result = await self.db_session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching recent trades: {e}")
            return []
