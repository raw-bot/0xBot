"""Trade filtering service to limit trades and ensure profitability."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Tuple
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import AsyncSessionLocal
from ..core.logger import get_logger
from ..core.memory.memory_manager import MemoryManager
from ..models.position import Position, PositionStatus
from ..models.trade import Trade

logger = get_logger(__name__)


class TradeFilterService:
    """Service to filter and validate trades for profitability and limits."""

    # Trade quality filters (not hard limits)
    TARGET_TRADES_PER_DAY = 6  # Target average, not a hard cap
    MIN_PROFIT_PER_TRADE_USD = 10  # Don't take trades under $10 profit expectancy
    MIN_PROFIT_PER_TRADE_PCT = 1.0  # Don't take trades under 1% expected return
    MIN_WIN_PROBABILITY = 0.55  # Only take trades with 55%+ win probability
    MIN_CONFIDENCE = 0.65  # Only trades with 65%+ confidence
    MAX_DAILY_LOSS_USD = -100  # Circuit breaker: stop if down $100+ in a day
    RR_RATIO_MIN = 1.5  # Minimum risk/reward ratio

    def __init__(self, db: Optional[AsyncSession] = None, bot_id: UUID = None):
        self.db = db
        self.bot_id = bot_id

    async def _get_db(self) -> AsyncSession:
        """Get database session if not provided."""
        if self.db:
            return self.db
        return AsyncSessionLocal()

    async def should_trade_today(self, bot_id: UUID) -> Tuple[bool, str]:
        """Check if bot should continue trading today.

        Returns:
            (bool, str): (should_trade, reason)

        Note: Only stops trading on circuit breaker (daily loss).
        Trade count is a TARGET, not a hard limit.
        """
        db = await self._get_db()

        try:
            today = datetime.utcnow().date()
            cutoff = datetime.combine(today, datetime.min.time())

            # Get today's trades
            trades_result = await db.execute(
                select(Trade).where(
                    and_(
                        Trade.bot_id == bot_id,
                        Trade.executed_at >= cutoff,
                    )
                )
            )
            today_trades = trades_result.scalars().all()

            # Check daily P&L (circuit breaker)
            daily_pnl = sum(t.realized_pnl for t in today_trades)
            if daily_pnl <= self.MAX_DAILY_LOSS_USD:
                return False, f"⚠️ Daily loss limit hit: ${float(daily_pnl):.2f} - STOP TRADING"

            # Trade count is just informational
            trades_count = len(today_trades)
            status = "✓ OK" if trades_count <= self.TARGET_TRADES_PER_DAY else "⚠️ ABOVE TARGET"
            return True, f"{status} - {trades_count}/{self.TARGET_TRADES_PER_DAY} trades (avg)"

        finally:
            if not self.db:
                await db.close()

    async def calculate_win_probability(
        self, bot_id: UUID, symbol: str, lookback_days: int = 30
    ) -> Tuple[Decimal, int]:
        """Calculate historical win probability for a symbol.

        Returns:
            (win_probability, sample_size)

        Note: Uses batch query to avoid N+1 pattern (was 1 + N queries, now 2 queries)
        """
        db = await self._get_db()

        try:
            cutoff = datetime.utcnow() - timedelta(days=lookback_days)

            # Get closed positions for this symbol
            positions_result = await db.execute(
                select(Position).where(
                    and_(
                        Position.bot_id == bot_id,
                        Position.symbol == symbol,
                        Position.status == PositionStatus.CLOSED,
                        Position.closed_at >= cutoff,
                    )
                )
            )
            positions = positions_result.scalars().all()

            if not positions:
                # No history - return neutral probability
                return Decimal("0.50"), 0

            # Batch query: get ALL trades for these positions in one query (not 1 + N)
            position_ids = [p.id for p in positions]
            trades_result = await db.execute(
                select(Trade).where(Trade.position_id.in_(position_ids))
            )
            all_trades = trades_result.scalars().all()

            # Group trades by position_id for efficient lookup
            trades_by_position = {}
            for trade in all_trades:
                if trade.position_id not in trades_by_position:
                    trades_by_position[trade.position_id] = []
                trades_by_position[trade.position_id].append(trade)

            # Calculate wins
            wins = 0
            for position in positions:
                trades = trades_by_position.get(position.id, [])
                if any(t.realized_pnl > 0 for t in trades):
                    wins += 1

            win_prob = Decimal(wins) / Decimal(len(positions))
            return win_prob, len(positions)

        finally:
            if not self.db:
                await db.close()

    async def validate_trade_setup(
        self,
        symbol: str,
        entry_price: Decimal,
        stop_loss: Decimal,
        take_profit: Decimal,
        position_size_usd: Decimal,
        win_probability: Decimal,
        confidence: Decimal,
    ) -> Tuple[bool, str]:
        """Validate if a trade setup meets profitability requirements.

        Uses memory to adjust thresholds dynamically based on symbol history.

        Returns:
            (is_valid, reason)
        """
        # Get dynamic thresholds based on memory
        min_profit_threshold = await self._get_dynamic_min_profit(symbol, bot_id=self.bot_id)

        # Calculate risk/reward
        risk_usd = (entry_price - stop_loss).abs()
        reward_usd = (take_profit - entry_price).abs()

        if risk_usd <= 0:
            return False, f"Invalid SL: ${float(risk_usd):.2f}"

        rr_ratio = reward_usd / risk_usd if risk_usd > 0 else Decimal("0")

        # Check minimum R/R
        if rr_ratio < Decimal(str(self.RR_RATIO_MIN)):
            return False, f"Poor R/R: {float(rr_ratio):.2f}x (need >{self.RR_RATIO_MIN}x)"

        # Calculate expected profit
        expected_profit = (
            (win_probability * reward_usd) - ((Decimal("1") - win_probability) * risk_usd)
        )

        # Check minimum expected profit in USD (dynamic threshold)
        if expected_profit < Decimal(str(min_profit_threshold)):
            return False, f"Low expected profit: ${float(expected_profit):.2f} (need >${min_profit_threshold})"

        # Calculate expected return %
        expected_return_pct = (expected_profit / position_size_usd * Decimal("100"))
        if expected_return_pct < Decimal(str(self.MIN_PROFIT_PER_TRADE_PCT)):
            return False, f"Low expected return: {float(expected_return_pct):.2f}% (need >{self.MIN_PROFIT_PER_TRADE_PCT}%)"

        # Check minimum win probability
        if win_probability < Decimal(str(self.MIN_WIN_PROBABILITY)):
            return False, f"Low win prob: {float(win_probability*100):.1f}% (need >{self.MIN_WIN_PROBABILITY*100:.0f}%)"

        # Check confidence threshold
        if confidence < Decimal(str(self.MIN_CONFIDENCE)):
            return False, f"Low confidence: {float(confidence*100):.0f}% (need >{self.MIN_CONFIDENCE*100:.0f}%)"

        return True, f"✓ Valid setup: ${float(expected_profit):.2f} expected profit, {float(rr_ratio):.2f}x R/R"

    async def _get_dynamic_min_profit(self, symbol: str, bot_id: UUID = None) -> int:
        """Get dynamic minimum profit threshold based on symbol history.

        Adjusts the minimum profit requirement based on win rate:
        - High win rate (>65%) → Lower minimum profit ($5)
        - Low win rate (<50%) → Higher minimum profit ($20)
        - Normal (50-65%) → Default ($10)

        Args:
            symbol: Trading symbol
            bot_id: Bot UUID for memory lookup (if available)
        """
        if not MemoryManager.is_enabled():
            return self.MIN_PROFIT_PER_TRADE_USD

        try:
            from ..services.trading_memory_service import TradingMemoryService

            # Create memory service with bot_id if provided
            memory = TradingMemoryService(bot_id=bot_id)
            stats = await memory.recall_symbol_stats(symbol)

            if not stats:
                return self.MIN_PROFIT_PER_TRADE_USD

            win_rate = stats.get("win_rate", 0.55)

            # Dynamic threshold based on win rate
            if win_rate > 0.65:
                threshold = 5  # Profitable symbol - relax threshold
                logger.info(f"[MEMORY] {symbol} win rate {win_rate*100:.0f}% → min profit threshold: ${threshold}")
            elif win_rate < 0.50:
                threshold = 20  # Struggling symbol - stricter threshold
                logger.info(f"[MEMORY] {symbol} win rate {win_rate*100:.0f}% → min profit threshold: ${threshold}")
            else:
                threshold = 10  # Default

            return threshold

        except Exception as e:
            logger.warning(f"[MEMORY] Error getting dynamic threshold for {symbol}: {e}")
            return self.MIN_PROFIT_PER_TRADE_USD

    async def get_daily_stats(self, bot_id: UUID) -> Dict:
        """Get today's trading statistics."""
        db = await self._get_db()

        try:
            today = datetime.utcnow().date()
            cutoff = datetime.combine(today, datetime.min.time())

            # Get today's trades
            trades_result = await db.execute(
                select(Trade).where(
                    and_(
                        Trade.bot_id == bot_id,
                        Trade.executed_at >= cutoff,
                    )
                )
            )
            today_trades = trades_result.scalars().all()

            if not today_trades:
                return {
                    "trades_today": 0,
                    "wins": 0,
                    "losses": 0,
                    "pnl": 0,
                    "win_rate": 0,
                }

            # Calculate stats
            pnl = sum(t.realized_pnl for t in today_trades)
            wins = len([t for t in today_trades if t.realized_pnl > 0])
            losses = len([t for t in today_trades if t.realized_pnl < 0])
            win_rate = (wins / len(today_trades) * 100) if today_trades else 0

            return {
                "trades_today": len(today_trades),
                "wins": wins,
                "losses": losses,
                "pnl": float(pnl),
                "win_rate": float(win_rate),
                "target_trades": self.TARGET_TRADES_PER_DAY,
                "vs_target": "above" if len(today_trades) > self.TARGET_TRADES_PER_DAY else "below/at",
            }

        finally:
            if not self.db:
                await db.close()
