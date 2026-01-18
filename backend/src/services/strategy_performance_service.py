"""Strategy performance tracking and metrics calculation service."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Tuple, Dict, List
import statistics

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import AsyncSessionLocal
from ..core.logger import get_logger
from ..models.position import Position, PositionStatus
from ..models.trade import Trade
from ..models.bot import Bot

logger = get_logger(__name__)


class StrategyMetrics:
    """Container for calculated strategy metrics."""

    def __init__(self):
        self.total_trades: int = 0
        self.winning_trades: int = 0
        self.losing_trades: int = 0
        self.win_rate: Decimal = Decimal("0")
        self.profit_factor: Decimal = Decimal("0")
        self.avg_win: Decimal = Decimal("0")
        self.avg_loss: Decimal = Decimal("0")
        self.largest_win: Decimal = Decimal("0")
        self.largest_loss: Decimal = Decimal("0")
        self.total_pnl: Decimal = Decimal("0")
        self.total_return_pct: Decimal = Decimal("0")
        self.sharpe_ratio: Decimal = Decimal("0")
        self.max_drawdown: Decimal = Decimal("0")
        self.max_drawdown_pct: Decimal = Decimal("0")
        self.consecutive_wins: int = 0
        self.consecutive_losses: int = 0
        self.trades_by_symbol: Dict[str, int] = {}
        self.symbol_win_rates: Dict[str, Decimal] = {}
        self.lookback_days: int = 30

    def to_dict(self) -> Dict:
        """Convert metrics to dictionary for API response."""
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate_pct": float(self.win_rate),
            "profit_factor": float(self.profit_factor),
            "avg_win": float(self.avg_win),
            "avg_loss": float(self.avg_loss),
            "largest_win": float(self.largest_win),
            "largest_loss": float(self.largest_loss),
            "total_pnl": float(self.total_pnl),
            "total_return_pct": float(self.total_return_pct),
            "sharpe_ratio": float(self.sharpe_ratio),
            "max_drawdown": float(self.max_drawdown),
            "max_drawdown_pct": float(self.max_drawdown_pct),
            "consecutive_wins": self.consecutive_wins,
            "consecutive_losses": self.consecutive_losses,
            "trades_by_symbol": self.trades_by_symbol,
            "symbol_win_rates": {k: float(v) for k, v in self.symbol_win_rates.items()},
            "lookback_days": self.lookback_days,
        }


class StrategyPerformanceService:
    """Service for calculating strategy performance metrics."""

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    async def _get_db(self) -> AsyncSession:
        """Get database session if not provided."""
        if self.db:
            return self.db
        return AsyncSessionLocal()

    async def calculate_metrics(
        self, bot_id: str, lookback_days: int = 30
    ) -> StrategyMetrics:
        """Calculate performance metrics for a bot's strategy.

        Args:
            bot_id: Bot UUID
            lookback_days: Number of days to analyze (default 30)

        Returns:
            StrategyMetrics object with all calculated metrics
        """
        db = await self._get_db()
        metrics = StrategyMetrics()
        metrics.lookback_days = lookback_days

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

            # Get all closed positions for the bot in lookback period
            positions = await db.execute(
                select(Position).where(
                    and_(
                        Position.bot_id == bot_id,
                        Position.status == PositionStatus.CLOSED,
                        Position.closed_at >= cutoff_date,
                    )
                )
            )
            closed_positions = positions.scalars().all()

            if not closed_positions:
                logger.info(f"No closed positions found for bot {bot_id} in last {lookback_days} days")
                return metrics

            # Get all trades for these positions
            position_ids = [p.id for p in closed_positions]
            trades_result = await db.execute(
                select(Trade).where(Trade.position_id.in_(position_ids))
            )
            trades = trades_result.scalars().all()

            # Calculate metrics
            self._calculate_trade_metrics(metrics, closed_positions, trades)
            self._calculate_risk_metrics(metrics, closed_positions)
            self._calculate_sharpe_ratio(metrics, closed_positions)

            logger.info(
                f"Calculated metrics for bot {bot_id}: "
                f"{metrics.winning_trades}W-{metrics.losing_trades}L "
                f"({metrics.win_rate:.1f}% win rate)"
            )

            return metrics

        finally:
            if not self.db:
                await db.close()

    def _calculate_trade_metrics(
        self, metrics: StrategyMetrics, positions: List[Position], trades: List[Trade]
    ) -> None:
        """Calculate basic trade metrics (win rate, profit factor, etc)."""
        if not positions:
            return

        metrics.total_trades = len(positions)
        pnl_values = []
        symbol_pnls = {}
        symbol_trades = {}

        for position in positions:
            # Calculate realized PnL from position trades
            position_pnl = Decimal("0")
            position_trades = [t for t in trades if t.position_id == position.id]

            for trade in position_trades:
                if trade.realized_pnl:
                    position_pnl += trade.realized_pnl

            pnl_values.append(position_pnl)
            metrics.total_pnl += position_pnl

            # Track by symbol
            if position.symbol not in symbol_pnls:
                symbol_pnls[position.symbol] = Decimal("0")
                symbol_trades[position.symbol] = 0

            symbol_pnls[position.symbol] += position_pnl
            symbol_trades[position.symbol] += 1
            metrics.trades_by_symbol[position.symbol] = symbol_trades[position.symbol]

            # Count wins and losses
            if position_pnl > 0:
                metrics.winning_trades += 1
                metrics.avg_win += position_pnl
                if position_pnl > metrics.largest_win:
                    metrics.largest_win = position_pnl
            elif position_pnl < 0:
                metrics.losing_trades += 1
                metrics.avg_loss += abs(position_pnl)
                if position_pnl < metrics.largest_loss:
                    metrics.largest_loss = position_pnl

        # Calculate averages
        if metrics.winning_trades > 0:
            metrics.avg_win = metrics.avg_win / Decimal(metrics.winning_trades)

        if metrics.losing_trades > 0:
            metrics.avg_loss = metrics.avg_loss / Decimal(metrics.losing_trades)

        # Calculate win rate
        if metrics.total_trades > 0:
            metrics.win_rate = (
                Decimal(metrics.winning_trades) / Decimal(metrics.total_trades) * Decimal("100")
            )

        # Calculate profit factor
        if metrics.avg_loss > 0:
            total_wins = metrics.avg_win * Decimal(metrics.winning_trades)
            total_losses = metrics.avg_loss * Decimal(metrics.losing_trades)
            if total_losses > 0:
                metrics.profit_factor = total_wins / total_losses

        # Calculate symbol win rates
        for symbol, pnl in symbol_pnls.items():
            symbol_count = symbol_trades[symbol]
            symbol_wins = sum(1 for p in positions if p.symbol == symbol and p.id in [
                t.position_id for t in trades if (t.realized_pnl or Decimal("0")) > 0
            ])
            if symbol_count > 0:
                metrics.symbol_win_rates[symbol] = (
                    Decimal(symbol_wins) / Decimal(symbol_count) * Decimal("100")
                )

    def _calculate_risk_metrics(
        self, metrics: StrategyMetrics, positions: List[Position]
    ) -> None:
        """Calculate risk metrics (max drawdown, etc)."""
        if not positions:
            return

        # Sort positions by close date
        sorted_positions = sorted(positions, key=lambda p: p.closed_at or datetime.utcnow())

        # Calculate cumulative equity curve for max drawdown
        cumulative_pnl = Decimal("0")
        peak_pnl = Decimal("0")
        max_drawdown = Decimal("0")

        position_pnls = []
        for position in sorted_positions:
            # Get position PnL from trades
            position_pnl = position.calculate_realized_pnl(
                position.current_price, position.quantity
            )
            position_pnls.append(position_pnl)
            cumulative_pnl += position_pnl

            if cumulative_pnl > peak_pnl:
                peak_pnl = cumulative_pnl

            drawdown = peak_pnl - cumulative_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        metrics.max_drawdown = max_drawdown
        if peak_pnl > 0:
            metrics.max_drawdown_pct = (max_drawdown / peak_pnl) * Decimal("100")

        # Calculate consecutive wins/losses
        if position_pnls:
            max_consecutive_wins = 0
            max_consecutive_losses = 0
            current_wins = 0
            current_losses = 0

            for pnl in position_pnls:
                if pnl > 0:
                    current_wins += 1
                    current_losses = 0
                    max_consecutive_wins = max(max_consecutive_wins, current_wins)
                elif pnl < 0:
                    current_losses += 1
                    current_wins = 0
                    max_consecutive_losses = max(max_consecutive_losses, current_losses)

            metrics.consecutive_wins = max_consecutive_wins
            metrics.consecutive_losses = max_consecutive_losses

    def _calculate_sharpe_ratio(
        self, metrics: StrategyMetrics, positions: List[Position]
    ) -> None:
        """Calculate Sharpe ratio from returns."""
        if metrics.total_trades < 2:
            return

        # Get position returns
        returns = []
        for position in positions:
            if position.entry_price > 0:
                if position.side == "long":
                    ret = (position.current_price - position.entry_price) / position.entry_price
                else:
                    ret = (position.entry_price - position.current_price) / position.entry_price
                returns.append(float(ret) * 100)  # Convert to percentage

        if len(returns) < 2:
            return

        try:
            mean_return = statistics.mean(returns)
            std_dev = statistics.stdev(returns)

            # Risk-free rate (annual 2%, daily ~0.0055%)
            risk_free_rate = 0.00005477  # Daily

            if std_dev > 0:
                # Sharpe ratio = (mean_return - risk_free_rate) / std_dev
                sharpe = (mean_return - risk_free_rate) / std_dev
                metrics.sharpe_ratio = Decimal(str(sharpe))
        except Exception as e:
            logger.warning(f"Failed to calculate Sharpe ratio: {e}")

    async def get_strategy_summary(self, bot_id: str) -> Dict:
        """Get a summary of strategy performance for dashboard display."""
        metrics = await self.calculate_metrics(bot_id)
        return {
            "summary": {
                "total_trades": metrics.total_trades,
                "win_rate": f"{float(metrics.win_rate):.1f}%",
                "profit_factor": f"{float(metrics.profit_factor):.2f}x",
                "total_return": f"${float(metrics.total_pnl):.2f}",
            },
            "risk_metrics": {
                "max_drawdown": f"{float(metrics.max_drawdown_pct):.1f}%",
                "sharpe_ratio": f"{float(metrics.sharpe_ratio):.2f}",
            },
            "detailed_metrics": metrics.to_dict(),
        }

    async def get_recent_trades_performance(
        self, bot_id: str, limit: int = 10
    ) -> List[Dict]:
        """Get performance data for the most recent trades."""
        db = await self._get_db()

        try:
            # Get recent closed positions
            positions = await db.execute(
                select(Position)
                .where(
                    and_(
                        Position.bot_id == bot_id,
                        Position.status == PositionStatus.CLOSED,
                    )
                )
                .order_by(Position.closed_at.desc())
                .limit(limit)
            )
            closed_positions = positions.scalars().all()

            trades_data = []
            for position in closed_positions:
                # Get trades for this position
                trades = await db.execute(
                    select(Trade).where(Trade.position_id == position.id)
                )
                position_trades = trades.scalars().all()

                total_pnl = sum(t.realized_pnl for t in position_trades)
                pnl_pct = (
                    (total_pnl / position.entry_value * Decimal("100"))
                    if position.entry_value > 0
                    else Decimal("0")
                )

                trades_data.append({
                    "symbol": position.symbol,
                    "side": position.side,
                    "entry_price": float(position.entry_price),
                    "exit_price": float(position.current_price),
                    "quantity": float(position.quantity),
                    "pnl": float(total_pnl),
                    "pnl_pct": float(pnl_pct),
                    "duration_hours": (
                        (position.closed_at - position.opened_at).total_seconds() / 3600
                        if position.closed_at
                        else 0
                    ),
                    "closed_at": position.closed_at.isoformat() if position.closed_at else None,
                })

            return trades_data

        finally:
            if not self.db:
                await db.close()
