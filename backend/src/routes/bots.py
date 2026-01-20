import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.scheduler import get_scheduler
from ..middleware.auth import get_current_user
from ..models.bot import Bot, BotStatus
from ..models.equity_snapshot import EquitySnapshot
from ..models.trade import Trade
from ..models.user import User
from ..services.bot_service import BotCreate, BotService, BotUpdate
from ..services.position_service import PositionService


router = APIRouter(prefix="/bots", tags=["bots"])


class RiskParamsSchema(BaseModel):
    max_position_pct: float = Field(0.10, ge=0.01, le=1.0)
    max_drawdown_pct: float = Field(0.20, ge=0.05, le=1.0)
    max_trades_per_day: int = Field(10, ge=1, le=100)


class BotCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    model_name: str
    capital: float = Field(..., ge=100)
    trading_symbols: Optional[list[str]] = None
    risk_params: Optional[RiskParamsSchema] = None
    paper_trading: bool = True


class BotUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    capital: Optional[float] = Field(None, ge=100)
    trading_symbols: Optional[list[str]] = None
    risk_params: Optional[RiskParamsSchema] = None
    status: Optional[str] = None


class BotResponse(BaseModel):
    id: str
    user_id: str
    name: str
    model_name: str
    capital: float
    trading_symbols: list[str]
    risk_params: dict[str, Any]
    status: str
    paper_trading: bool
    created_at: str
    updated_at: str
    total_pnl: float
    portfolio_value: float
    return_pct: float

    class Config:
        from_attributes = True


class PositionResponse(BaseModel):
    id: str
    bot_id: str
    symbol: str
    side: str
    quantity: float
    entry_price: float
    current_price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    status: str
    unrealized_pnl: float
    unrealized_pnl_pct: float
    position_value: float
    opened_at: str
    closed_at: Optional[str]

    class Config:
        from_attributes = True


class TradeResponse(BaseModel):
    id: str
    bot_id: str
    position_id: Optional[str]
    symbol: str
    side: str
    quantity: float
    price: float
    fees: float
    realized_pnl: float
    executed_at: str

    class Config:
        from_attributes = True


class BotListResponse(BaseModel):
    bots: list[BotResponse]
    total: int


class PositionListResponse(BaseModel):
    positions: list[PositionResponse]
    total: int


class TradeListResponse(BaseModel):
    trades: list[TradeResponse]
    total: int


class MessageResponse(BaseModel):
    message: str
    details: Optional[dict[str, Any]] = None


class EquitySnapshotResponse(BaseModel):
    timestamp: str
    equity: float
    cash: float
    unrealized_pnl: float


class EquityHistoryResponse(BaseModel):
    snapshots: list[EquitySnapshotResponse]
    current_equity: float
    initial_capital: float
    total_return_pct: float


async def get_bot_with_ownership(
    bot_id: str,
    user: User,
    db: AsyncSession,
    load_relations: bool = False,
) -> Bot:
    """Fetch bot and verify ownership. Raises HTTPException if not found or unauthorized."""
    try:
        bot_uuid = uuid.UUID(bot_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bot ID")

    bot_service = BotService(db)
    bot = await bot_service.get_bot(bot_uuid, load_relations=load_relations)

    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
    if bot.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    return bot


def bot_to_response(bot: Bot) -> BotResponse:
    total_pnl = Decimal("0")
    portfolio_value = bot.capital
    return_pct = Decimal("0")

    if hasattr(bot, "_sa_instance_state") and bot._sa_instance_state.has_identity:
        try:
            total_pnl = bot.total_pnl
            portfolio_value = bot.portfolio_value
            return_pct = bot.return_pct
        except Exception:
            pass

    return BotResponse(
        id=str(bot.id),
        user_id=str(bot.user_id),
        name=bot.name,
        model_name=bot.model_name,
        capital=float(bot.capital),
        trading_symbols=bot.trading_symbols,
        risk_params=bot.risk_params,
        status=bot.status,
        paper_trading=bot.paper_trading,
        created_at=bot.created_at.isoformat(),
        updated_at=bot.updated_at.isoformat(),
        total_pnl=float(total_pnl),
        portfolio_value=float(portfolio_value),
        return_pct=float(return_pct),
    )


def position_to_response(position: Any) -> PositionResponse:
    return PositionResponse(
        id=str(position.id),
        bot_id=str(position.bot_id),
        symbol=position.symbol,
        side=position.side,
        quantity=float(position.quantity),
        entry_price=float(position.entry_price),
        current_price=float(position.current_price),
        stop_loss=float(position.stop_loss) if position.stop_loss else None,
        take_profit=float(position.take_profit) if position.take_profit else None,
        status=position.status,
        unrealized_pnl=float(position.unrealized_pnl),
        unrealized_pnl_pct=float(position.unrealized_pnl_pct),
        position_value=float(position.position_value),
        opened_at=position.opened_at.isoformat(),
        closed_at=position.closed_at.isoformat() if position.closed_at else None,
    )


def trade_to_response(trade: Any) -> TradeResponse:
    return TradeResponse(
        id=str(trade.id),
        bot_id=str(trade.bot_id),
        position_id=str(trade.position_id) if trade.position_id else None,
        symbol=trade.symbol,
        side=trade.side,
        quantity=float(trade.quantity),
        price=float(trade.price),
        fees=float(trade.fees),
        realized_pnl=float(trade.realized_pnl),
        executed_at=trade.executed_at.isoformat(),
    )


@router.post("", response_model=BotResponse, status_code=status.HTTP_201_CREATED)
async def create_bot(
    request: BotCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BotResponse:
    bot_service = BotService(db)

    bot_data = BotCreate(
        name=request.name,
        model_name=request.model_name,
        capital=Decimal(str(request.capital)),
        trading_symbols=request.trading_symbols,
        risk_params=request.risk_params.model_dump() if request.risk_params else None,
        paper_trading=request.paper_trading,
    )

    bot = await bot_service.create_bot(current_user.id, bot_data)
    await db.refresh(bot)

    return bot_to_response(bot)


@router.get("", response_model=BotListResponse)
async def list_bots(
    page: int = 1,
    limit: int = 100,
    include_stopped: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BotListResponse:
    # Validate pagination parameters
    limit = max(10, min(limit, 1000))  # Enforce min 10, max 1000
    if page < 1:
        page = 1
    offset = (page - 1) * limit

    bot_service = BotService(db)
    bots, total = await bot_service.get_user_bots_paginated(
        current_user.id, include_stopped, limit, offset
    )
    return BotListResponse(bots=[bot_to_response(bot) for bot in bots], total=total)


@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(
    bot_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BotResponse:
    bot = await get_bot_with_ownership(bot_id, current_user, db, load_relations=True)
    return bot_to_response(bot)


@router.put("/{bot_id}", response_model=BotResponse)
async def update_bot(
    bot_id: str,
    request: BotUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BotResponse:
    bot = await get_bot_with_ownership(bot_id, current_user, db)
    bot_service = BotService(db)

    update_data = BotUpdate(
        name=request.name,
        capital=Decimal(str(request.capital)) if request.capital else None,
        trading_symbols=request.trading_symbols,
        risk_params=request.risk_params.model_dump() if request.risk_params else None,
        status=request.status,
    )

    updated_bot = await bot_service.update_bot(bot.id, update_data)
    if updated_bot is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update bot")
    return bot_to_response(updated_bot)


@router.delete("/{bot_id}", response_model=MessageResponse)
async def delete_bot(
    bot_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    bot = await get_bot_with_ownership(bot_id, current_user, db)
    bot_service = BotService(db)
    await bot_service.delete_bot(bot.id)
    return MessageResponse(message="Bot deleted successfully")


@router.post("/{bot_id}/start", response_model=MessageResponse)
async def start_bot(
    bot_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    bot = await get_bot_with_ownership(bot_id, current_user, db)

    if bot.status == BotStatus.ACTIVE:
        return MessageResponse(message="Bot is already active")

    bot_service = BotService(db)
    await bot_service.update_bot(bot.id, BotUpdate(status=BotStatus.ACTIVE.value))

    scheduler = get_scheduler()
    success = await scheduler.start_bot(bot.id, db)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bot status updated but trading engine failed to start",
        )

    return MessageResponse(
        message="Bot started successfully - trading engine is now running",
        details={"bot_id": bot_id, "status": "active", "engine_running": True},
    )


@router.post("/{bot_id}/pause", response_model=MessageResponse)
async def pause_bot(
    bot_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    bot = await get_bot_with_ownership(bot_id, current_user, db)
    bot_service = BotService(db)
    await bot_service.update_bot(bot.id, BotUpdate(status=BotStatus.PAUSED.value))

    return MessageResponse(
        message="Bot paused successfully",
        details={"bot_id": bot_id, "status": "paused"},
    )


@router.post("/{bot_id}/stop", response_model=MessageResponse)
async def stop_bot(
    bot_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    bot = await get_bot_with_ownership(bot_id, current_user, db)
    position_service = PositionService(db)
    positions = await position_service.get_open_positions(bot.id)

    bot_service = BotService(db)
    await bot_service.update_bot(bot.id, BotUpdate(status=BotStatus.STOPPED.value))

    scheduler = get_scheduler()
    engine_stopped = await scheduler.stop_bot(bot.id)

    return MessageResponse(
        message="Bot stopped successfully - all positions closed",
        details={
            "bot_id": bot_id,
            "status": "stopped",
            "open_positions": len(positions),
            "engine_stopped": engine_stopped,
        },
    )


@router.get("/{bot_id}/positions", response_model=PositionListResponse)
async def get_bot_positions(
    bot_id: str,
    page: int = 1,
    limit: int = 100,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PositionListResponse:
    bot = await get_bot_with_ownership(bot_id, current_user, db)

    # Validate pagination parameters
    limit = max(10, min(limit, 1000))  # Enforce min 10, max 1000
    if page < 1:
        page = 1
    offset = (page - 1) * limit

    position_service = PositionService(db)

    if status_filter == "open":
        positions, total = await position_service.get_open_positions_paginated(
            bot.id, limit=limit, offset=offset
        )
    else:
        positions, total = await position_service.get_all_positions(bot.id, limit=limit, offset=offset)

    return PositionListResponse(
        positions=[position_to_response(pos) for pos in positions],
        total=total,
    )


@router.get("/{bot_id}/trades", response_model=TradeListResponse)
async def get_bot_trades(
    bot_id: str,
    page: int = 1,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TradeListResponse:
    bot = await get_bot_with_ownership(bot_id, current_user, db)

    # Validate pagination parameters
    limit = max(10, min(limit, 1000))  # Enforce min 10, max 1000
    if page < 1:
        page = 1
    offset = (page - 1) * limit

    count_result = await db.execute(
        select(func.count()).select_from(Trade).where(Trade.bot_id == bot.id)
    )
    total = count_result.scalar()

    result = await db.execute(
        select(Trade)
        .where(Trade.bot_id == bot.id)
        .order_by(desc(Trade.executed_at))
        .limit(limit)
        .offset(offset)
    )
    trades = list(result.scalars().all())

    return TradeListResponse(
        trades=[trade_to_response(trade) for trade in trades],
        total=total if total is not None else 0,
    )


@router.get("/{bot_id}/equity", response_model=EquityHistoryResponse)
async def get_bot_equity(
    bot_id: str,
    period: str = "24h",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EquityHistoryResponse:
    bot = await get_bot_with_ownership(bot_id, current_user, db)

    period_map = {
        "1h": timedelta(hours=1),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    time_delta = period_map.get(period)
    start_time = datetime.utcnow() - time_delta if time_delta else None

    query = select(EquitySnapshot).where(EquitySnapshot.bot_id == bot.id)
    if start_time:
        query = query.where(EquitySnapshot.timestamp >= start_time)
    query = query.order_by(EquitySnapshot.timestamp)

    result = await db.execute(query)
    snapshots = list(result.scalars().all())

    current_equity = float(bot.capital)
    initial_capital = float(bot.initial_capital)
    total_return_pct = (
        ((current_equity - initial_capital) / initial_capital) * 100
        if initial_capital > 0
        else 0.0
    )

    return EquityHistoryResponse(
        snapshots=[
            EquitySnapshotResponse(
                timestamp=s.timestamp.isoformat(),
                equity=float(s.equity),
                cash=float(s.cash),
                unrealized_pnl=float(s.unrealized_pnl),
            )
            for s in snapshots
        ],
        current_equity=current_equity,
        initial_capital=initial_capital,
        total_return_pct=total_return_pct,
    )
