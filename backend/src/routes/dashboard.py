"""Public dashboard API endpoints (no authentication required)."""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.logger import get_logger
from ..models.bot import Bot, BotStatus
from ..models.position import Position

logger = get_logger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ============================================================================
# Pydantic Schemas
# ============================================================================


class DashboardBotResponse(BaseModel):
    """Simple bot info for dashboard."""

    id: str
    name: str
    status: str
    capital: float
    initial_capital: float
    total_trades: int
    winning_trades: int = 0


class DashboardPositionResponse(BaseModel):
    """Position info for dashboard."""

    symbol: str
    side: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


class DashboardEquitySnapshot(BaseModel):
    """Equity snapshot for chart."""

    timestamp: str
    equity: float


class TradeHistoryItem(BaseModel):
    """Single trade for PnL chart."""

    timestamp: str
    symbol: str
    side: str
    pnl: float
    cumulative_pnl: float  # Running total for this symbol
    entry_price: float = 0.0
    exit_price: float = 0.0


class DashboardResponse(BaseModel):
    """Full dashboard data response."""

    bot: Optional[DashboardBotResponse]
    positions: List[DashboardPositionResponse]
    equity_snapshots: List[DashboardEquitySnapshot]
    trade_history: List[TradeHistoryItem]  # NEW: for multi-curve chart
    current_equity: float
    total_return_pct: float
    total_unrealized_pnl: float


# ============================================================================
# Public Dashboard Endpoints
# ============================================================================


@router.get("", response_model=DashboardResponse)
async def get_dashboard_data(
    period: str = "24h",
    db: AsyncSession = Depends(get_db),
):
    """
    Get all dashboard data in a single call (no authentication required).

    - **period**: Time period for equity chart (1h, 24h, 7d, 30d, all)
    """
    try:
        # Get the first active bot
        query = select(Bot).where(Bot.status == BotStatus.ACTIVE.value).limit(1)
        result = await db.execute(query)
        bot = result.scalar_one_or_none()

        if not bot:
            # Try to get any bot
            query = select(Bot).limit(1)
            result = await db.execute(query)
            bot = result.scalar_one_or_none()

        if not bot:
            # No bots exist, return empty dashboard
            return DashboardResponse(
                bot=None,
                positions=[],
                equity_snapshots=[],
                current_equity=10000.0,
                total_return_pct=0.0,
                total_unrealized_pnl=0.0,
            )

        # Get open positions
        positions_query = select(Position).where(
            Position.bot_id == bot.id, Position.status == "open"
        )
        positions_result = await db.execute(positions_query)
        positions = list(positions_result.scalars().all())

        # Calculate total unrealized PnL and margin locked in positions
        total_unrealized_pnl = sum(float(p.unrealized_pnl) for p in positions)

        # Calculate margin locked in open positions (entry_price * quantity / leverage)
        # With leverage 1x, margin = notional value
        margin_in_positions = sum(
            (
                float(p.entry_price * p.quantity / p.leverage)
                if p.leverage
                else float(p.entry_price * p.quantity)
            )
            for p in positions
        )

        # Get equity snapshots
        from ..models.equity_snapshot import EquitySnapshot

        now = datetime.utcnow()
        period_map = {
            "1h": timedelta(hours=1),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
        }
        time_delta = period_map.get(period)
        start_time = now - time_delta if time_delta else None

        equity_query = select(EquitySnapshot).where(EquitySnapshot.bot_id == bot.id)
        if start_time:
            equity_query = equity_query.where(EquitySnapshot.timestamp >= start_time)
        equity_query = equity_query.order_by(EquitySnapshot.timestamp)

        equity_result = await db.execute(equity_query)
        snapshots = list(equity_result.scalars().all())

        # Calculate current equity and return
        # Equity = cash + margin locked in positions + unrealized PnL
        current_equity = float(bot.capital) + margin_in_positions + total_unrealized_pnl
        initial_capital = float(bot.initial_capital)
        total_return_pct = 0.0
        if initial_capital > 0:
            total_return_pct = ((current_equity - initial_capital) / initial_capital) * 100

        # Count trades and build trade history for chart
        from ..models.trade import Trade

        trades_query = select(Trade).where(Trade.bot_id == bot.id)
        if start_time:
            trades_query = trades_query.where(Trade.executed_at >= start_time)
        trades_query = trades_query.order_by(Trade.executed_at)
        trades_result = await db.execute(trades_query)
        all_trades = list(trades_result.scalars().all())

        # Get total trades (unfiltered) for stats
        total_trades_query = select(Trade).where(Trade.bot_id == bot.id)
        total_trades_result = await db.execute(total_trades_query)
        total_trades = len(list(total_trades_result.scalars().all()))

        # Calculate cumulative PnL per symbol
        cumulative_by_symbol = {}
        trade_history = []
        for trade in all_trades:
            symbol = trade.symbol
            pnl = float(trade.realized_pnl) if trade.realized_pnl else 0.0
            if symbol not in cumulative_by_symbol:
                cumulative_by_symbol[symbol] = 0.0
            cumulative_by_symbol[symbol] += pnl
            trade_history.append(
                TradeHistoryItem(
                    timestamp=trade.executed_at.isoformat(),
                    symbol=symbol,
                    side=trade.side,
                    pnl=pnl,
                    cumulative_pnl=cumulative_by_symbol[symbol],
                    entry_price=float(trade.price) if trade.price else 0.0,
                    exit_price=float(trade.price) if trade.price else 0.0,
                )
            )

        # Count winning trades
        winning_trades = sum(1 for t in all_trades if t.realized_pnl and float(t.realized_pnl) > 0)

        return DashboardResponse(
            bot=DashboardBotResponse(
                id=str(bot.id),
                name=bot.name,
                status=bot.status,
                capital=float(bot.capital),
                initial_capital=initial_capital,
                total_trades=total_trades,
                winning_trades=winning_trades,
            ),
            positions=[
                DashboardPositionResponse(
                    symbol=p.symbol,
                    side=p.side,
                    quantity=float(p.quantity),
                    entry_price=float(p.entry_price),
                    current_price=float(p.current_price),
                    unrealized_pnl=float(p.unrealized_pnl),
                    unrealized_pnl_pct=float(p.unrealized_pnl_pct),
                )
                for p in positions
            ],
            equity_snapshots=[
                DashboardEquitySnapshot(
                    timestamp=s.timestamp.isoformat(),
                    equity=float(s.equity),
                )
                for s in snapshots
            ],
            trade_history=trade_history,
            current_equity=current_equity,
            total_return_pct=total_return_pct,
            total_unrealized_pnl=total_unrealized_pnl,
        )

    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard data: {str(e)}",
        )


@router.get("/bots")
async def list_bots_public(
    db: AsyncSession = Depends(get_db),
):
    """
    List all bots (public endpoint for dashboard).
    """
    try:
        query = select(Bot)
        result = await db.execute(query)
        bots = list(result.scalars().all())

        return {
            "bots": [
                {
                    "id": str(bot.id),
                    "name": bot.name,
                    "status": bot.status,
                    "capital": float(bot.capital),
                    "initial_capital": float(bot.initial_capital),
                }
                for bot in bots
            ],
            "total": len(bots),
        }

    except Exception as e:
        logger.error(f"Error listing bots: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list bots"
        )
