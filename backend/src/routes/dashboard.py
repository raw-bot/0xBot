from datetime import datetime, timedelta
from typing import Any, List, Optional
import time

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.database import get_db
from ..core.logger import get_logger
from ..models.bot import Bot, BotStatus
from ..models.equity_snapshot import EquitySnapshot
from ..models.position import Position
from ..models.trade import Trade
from ..services.market_sentiment_service import get_sentiment_service

logger = get_logger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


PERIOD_MAP = {
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "12h": timedelta(hours=12),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "7j": timedelta(days=7),
    "30d": timedelta(days=30),
    "30j": timedelta(days=30),
}


class DashboardBotResponse(BaseModel):
    id: str
    name: str
    status: str
    capital: float
    initial_capital: float
    total_trades: int
    winning_trades: int = 0


class DashboardPositionResponse(BaseModel):
    symbol: str
    side: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    leverage: float


class DashboardEquitySnapshot(BaseModel):
    timestamp: str
    equity: float


class TradeHistoryItem(BaseModel):
    timestamp: str
    symbol: str
    side: str
    pnl: float
    cumulative_pnl: float
    entry_price: float = 0.0
    exit_price: float = 0.0
    quantity: float = 0.0
    size: float = 0.0
    margin: float = 0.0
    leverage: float = 1.0
    fees: float = 0.0


class DashboardResponse(BaseModel):
    bot: Optional[DashboardBotResponse]
    positions: list[DashboardPositionResponse]
    equity_snapshots: list[DashboardEquitySnapshot]
    trade_history: list[TradeHistoryItem]
    current_equity: float
    total_return_pct: float
    total_unrealized_pnl: float
    btc_start_price: float = 0.0
    btc_current_price: float = 0.0
    hodl_return_pct: float = 0.0
    alpha_pct: float = 0.0


def get_period_start(period: str) -> Optional[datetime]:
    time_delta = PERIOD_MAP.get(period)
    return datetime.utcnow() - time_delta if time_delta else None


def calculate_margin_in_positions(positions: list[Any]) -> float:
    return sum(
        float(p.entry_price * p.quantity / p.leverage) if p.leverage else float(p.entry_price * p.quantity)
        for p in positions
    )


def build_trade_history_item(trade: Any, position: Any, cumulative_pnl: float) -> TradeHistoryItem:
    pnl = float(trade.realized_pnl) if trade.realized_pnl else 0.0
    qty = float(trade.quantity) if trade.quantity else 0.0
    trade_price = float(trade.price) if trade.price else 0.0
    is_exit = pnl != 0

    if is_exit and position:
        entry_p = float(position.entry_price)
        exit_p = trade_price
        display_side = position.side
    else:
        entry_p = trade_price
        exit_p = 0.0
        display_side = "long" if trade.side.lower() == "buy" else "short"

    lev = float(position.leverage) if position and position.leverage else 1.0
    notional = qty * entry_p
    margin = notional / lev if lev > 0 else notional

    return TradeHistoryItem(
        timestamp=trade.executed_at.isoformat(),
        symbol=trade.symbol,
        side=display_side,
        pnl=pnl,
        cumulative_pnl=cumulative_pnl,
        entry_price=entry_p,
        exit_price=exit_p,
        quantity=qty,
        size=notional,
        margin=margin,
        leverage=lev,
        fees=float(trade.fees) if trade.fees else 0.0,
    )


async def get_hodl_comparison(db: AsyncSession, bot_id: Any, total_return_pct: float) -> dict[str, Any]:
    try:
        first_trade_query = (
            select(Trade)
            .where(Trade.bot_id == bot_id, Trade.symbol == "BTC/USDT")
            .order_by(Trade.executed_at)
            .limit(1)
        )
        first_trade_result = await db.execute(first_trade_query)
        first_btc_trade = first_trade_result.scalar_one_or_none()

        if not first_btc_trade:
            return {"btc_start_price": 0.0, "btc_current_price": 0.0, "hodl_return_pct": 0.0, "alpha_pct": 0.0}

        btc_start_price = float(first_btc_trade.price)

        from ..core.exchange_client import get_exchange_client
        exchange = get_exchange_client()
        btc_ticker = await exchange.fetch_ticker("BTC/USDT")
        btc_current_price = btc_ticker.get("last", 0) or 0

        if btc_start_price > 0 and btc_current_price > 0:
            hodl_return_pct = ((btc_current_price - btc_start_price) / btc_start_price) * 100
            alpha_pct = total_return_pct - hodl_return_pct
        else:
            hodl_return_pct = 0.0
            alpha_pct = 0.0

        return {
            "btc_start_price": btc_start_price,
            "btc_current_price": btc_current_price,
            "hodl_return_pct": hodl_return_pct,
            "alpha_pct": alpha_pct,
        }
    except Exception as e:
        logger.warning(f"Could not calculate HODL comparison: {e}")
        return {"btc_start_price": 0.0, "btc_current_price": 0.0, "hodl_return_pct": 0.0, "alpha_pct": 0.0}


async def get_first_bot(db: AsyncSession) -> Optional[Bot]:
    result = await db.execute(
        select(Bot).where(Bot.status == BotStatus.ACTIVE.value).limit(1)
    )
    bot = result.scalar_one_or_none()

    if not bot:
        result = await db.execute(select(Bot).limit(1))
        bot = result.scalar_one_or_none()

    return bot


@router.get("", response_model=DashboardResponse)
async def get_dashboard_data(
    period: str = "24h",
    include_hodl: bool = Query(False, description="Include HODL comparison (slower)"),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    """Get dashboard data with optimized queries.

    Performance targets:
    - Positions query: 1 query
    - Equity snapshots query: 1 query
    - Trade history query: 1 query with outerjoin
    - Total metrics query: 1 query
    - Total: 4 queries max (with optional HODL = 5)
    """
    start_time = time.time()

    # Get first bot
    bot = await get_first_bot(db)

    if not bot:
        return DashboardResponse(
            bot=None,
            positions=[],
            equity_snapshots=[],
            trade_history=[],
            current_equity=10000.0,
            total_return_pct=0.0,
            total_unrealized_pnl=0.0,
        )

    start_time_period = get_period_start(period)

    # Query 1: Get open positions (indexed on bot_id, status)
    positions_result = await db.execute(
        select(Position).where(Position.bot_id == bot.id, Position.status == "open")
    )
    positions = list(positions_result.scalars().all())

    total_unrealized_pnl = sum(float(p.unrealized_pnl) for p in positions)
    margin_in_positions = calculate_margin_in_positions(positions)

    # Query 2: Get equity snapshots (indexed on bot_id, timestamp)
    equity_query = select(EquitySnapshot).where(EquitySnapshot.bot_id == bot.id)
    if start_time_period:
        equity_query = equity_query.where(EquitySnapshot.timestamp >= start_time_period)
    equity_query = equity_query.order_by(EquitySnapshot.timestamp)
    equity_result = await db.execute(equity_query)
    snapshots = list(equity_result.scalars().all())

    # Calculate metrics
    current_equity = float(bot.capital) + margin_in_positions + total_unrealized_pnl
    initial_capital = float(bot.initial_capital)
    total_return_pct = ((current_equity - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0.0

    # Query 3: Get trades with positions (using outerjoin to prevent N+1 queries)
    trades_query = (
        select(Trade, Position)
        .outerjoin(Position, Trade.position_id == Position.id)
        .where(Trade.bot_id == bot.id)
    )
    if start_time_period:
        trades_query = trades_query.where(Trade.executed_at >= start_time_period)
    trades_query = trades_query.order_by(Trade.executed_at.desc())
    trades_result = await db.execute(trades_query)
    all_trade_rows = list(trades_result.all())

    # Query 4: Get total trades count (use COUNT(*) query instead of fetching all rows)
    total_trades_result = await db.execute(
        select(func.count(Trade.id)).where(Trade.bot_id == bot.id)
    )
    total_trades = total_trades_result.scalar() or 0

    # Build trade history
    cumulative_by_symbol: dict[str, float] = {}
    trade_history: list[TradeHistoryItem] = []
    for trade, position in all_trade_rows:
        pnl = float(trade.realized_pnl) if trade.realized_pnl else 0.0
        cumulative_by_symbol[trade.symbol] = cumulative_by_symbol.get(trade.symbol, 0.0) + pnl
        trade_history.append(build_trade_history_item(trade, position, cumulative_by_symbol[trade.symbol]))

    winning_trades = sum(1 for t, _ in all_trade_rows if t.realized_pnl and float(t.realized_pnl) > 0)

    # Optional: Get HODL comparison (can be slow due to exchange API call)
    hodl_data = {}
    if include_hodl:
        hodl_data = await get_hodl_comparison(db, bot.id, total_return_pct)
    else:
        hodl_data = {"btc_start_price": 0.0, "btc_current_price": 0.0, "hodl_return_pct": 0.0, "alpha_pct": 0.0}

    query_time_ms = (time.time() - start_time) * 1000
    logger.info(f"Dashboard query completed in {query_time_ms:.2f}ms")

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
                leverage=float(p.leverage) if p.leverage else 1.0,
            )
            for p in positions
        ],
        equity_snapshots=[
            DashboardEquitySnapshot(timestamp=s.timestamp.isoformat(), equity=float(s.equity))
            for s in snapshots
        ],
        trade_history=trade_history,
        current_equity=current_equity,
        total_return_pct=total_return_pct,
        total_unrealized_pnl=total_unrealized_pnl,
        **hodl_data,
    )


@router.get("/bots")
async def list_bots_public(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(100, ge=10, le=1000, description="Results per page (10-1000)"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List all bots with pagination to prevent loading all bots.

    Performance targets:
    - Single COUNT query
    - Single SELECT with OFFSET/LIMIT
    - Total: 2 queries max
    """
    # Query 1: Get total count (indexed)
    count_result = await db.execute(select(func.count(Bot.id)))
    total = count_result.scalar() or 0

    # Query 2: Get paginated results
    offset = (page - 1) * limit
    result = await db.execute(
        select(Bot).offset(offset).limit(limit)
    )
    bots = list(result.scalars().all())

    total_pages = (total + limit - 1) // limit

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
        "total": total,
        "page": page,
        "limit": limit,
        "pages": total_pages,
    }


@router.get("/sentiment")
async def get_market_sentiment() -> dict[str, Any]:
    try:
        sentiment_service = get_sentiment_service()
        sentiment = await sentiment_service.get_market_sentiment()

        if not sentiment:
            return {"available": False, "error": "Sentiment data unavailable"}

        return {
            "available": True,
            "fear_greed": {
                "value": sentiment.fear_greed.value,
                "label": sentiment.fear_greed.label,
                "yesterday": sentiment.fear_greed.yesterday_value,
                "last_week": sentiment.fear_greed.last_week_value,
                "trend": sentiment.fear_greed.trend,
            },
            "global_market": {
                "total_market_cap": sentiment.global_market.total_market_cap_usd,
                "market_cap_change_24h": sentiment.global_market.market_cap_change_24h,
                "btc_dominance": sentiment.global_market.btc_dominance,
                "eth_dominance": sentiment.global_market.eth_dominance,
                "trending_coins": sentiment.global_market.trending_coins,
            },
            "market_phase": sentiment.market_phase.value,
            "llm_guidance": sentiment.llm_guidance,
            "timestamp": sentiment.fetched_at.isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching sentiment: {e}")
        return {"available": False, "error": str(e)}
