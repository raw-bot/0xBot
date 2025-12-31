"""Bot management API endpoints."""

import uuid
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.logger import get_logger
from ..core.scheduler import get_scheduler
from ..middleware.auth import get_current_user
from ..models.bot import Bot, BotStatus
from ..models.user import User
from ..services.bot_service import BotCreate, BotService, BotUpdate
from ..services.position_service import PositionService

logger = get_logger(__name__)

router = APIRouter(prefix="/bots", tags=["bots"])


# ============================================================================
# Pydantic Schemas
# ============================================================================


class RiskParamsSchema(BaseModel):
    """Risk parameters schema."""

    max_position_pct: float = Field(
        0.10, ge=0.01, le=1.0, description="Max position size as % of capital"
    )
    max_drawdown_pct: float = Field(
        0.20, ge=0.05, le=1.0, description="Max drawdown as % of capital"
    )
    max_trades_per_day: int = Field(10, ge=1, le=100, description="Max trades per day")


class BotCreateRequest(BaseModel):
    """Request body for creating a bot."""

    name: str = Field(..., min_length=1, max_length=255, description="Bot name")
    model_name: str = Field(
        ..., description="LLM model name (claude-4.5-sonnet, gpt-4, deepseek-v3, gemini-2.5-pro)"
    )
    capital: float = Field(..., ge=100, description="Initial capital in USD (min $100)")
    trading_symbols: Optional[List[str]] = Field(
        None, description="List of trading pairs (e.g., ['BTC/USDT', 'ETH/USDT'])"
    )
    risk_params: Optional[RiskParamsSchema] = Field(None, description="Risk management parameters")
    paper_trading: bool = Field(True, description="Enable paper trading mode")


class BotUpdateRequest(BaseModel):
    """Request body for updating a bot."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    capital: Optional[float] = Field(None, ge=100)
    trading_symbols: Optional[List[str]] = Field(
        None, description="List of trading pairs to update"
    )
    risk_params: Optional[RiskParamsSchema] = None
    status: Optional[str] = None


class BotResponse(BaseModel):
    """Bot response schema."""

    id: str
    user_id: str
    name: str
    model_name: str
    capital: float
    trading_symbols: List[str]
    risk_params: dict
    status: str
    paper_trading: bool
    created_at: str
    updated_at: str

    # Portfolio metrics
    total_pnl: float
    portfolio_value: float
    return_pct: float

    class Config:
        from_attributes = True


class PositionResponse(BaseModel):
    """Position response schema."""

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
    """Trade response schema."""

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
    """Bot list response."""

    bots: List[BotResponse]
    total: int


class PositionListResponse(BaseModel):
    """Position list response."""

    positions: List[PositionResponse]
    total: int


class TradeListResponse(BaseModel):
    """Trade list response."""

    trades: List[TradeResponse]
    total: int


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    details: Optional[dict] = None


class EquitySnapshotResponse(BaseModel):
    """Single equity snapshot."""

    timestamp: str
    equity: float
    cash: float
    unrealized_pnl: float


class EquityHistoryResponse(BaseModel):
    """Equity history response."""

    snapshots: List[EquitySnapshotResponse]
    current_equity: float
    initial_capital: float
    total_return_pct: float


# ============================================================================
# T039: Bot CRUD Endpoints
# ============================================================================


@router.post("", response_model=BotResponse, status_code=status.HTTP_201_CREATED)
async def create_bot(
    request: BotCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new trading bot.

    - **name**: Bot name
    - **model_name**: AI model (claude-4.5-sonnet, gpt-4, deepseek-v3, gemini-2.5-pro)
    - **capital**: Initial capital in USD (minimum $100)
    - **risk_params**: Risk management parameters (optional)
    - **paper_trading**: Enable paper trading mode (default: true)
    """
    try:
        bot_service = BotService(db)

        # Convert risk params if provided
        risk_params_dict = None
        if request.risk_params:
            risk_params_dict = request.risk_params.model_dump()

        bot_data = BotCreate(
            name=request.name,
            model_name=request.model_name,
            capital=Decimal(str(request.capital)),
            trading_symbols=request.trading_symbols,
            risk_params=risk_params_dict,
            paper_trading=request.paper_trading,
        )

        bot = await bot_service.create_bot(current_user.id, bot_data)

        # Refresh bot to load relationships needed for calculated properties
        await db.refresh(bot)

        return _bot_to_response(bot)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating bot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create bot"
        )


@router.get("", response_model=BotListResponse)
async def list_bots(
    include_stopped: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all bots for the current user.

    - **include_stopped**: Include stopped bots (default: false)
    """
    try:
        bot_service = BotService(db)
        logger.info(f"Listing bots for user: {current_user.id} ({current_user.email})")

        # DEBUG: Check if ANY bots exist
        all_bots_result = await db.execute(select(Bot))
        all_bots = list(all_bots_result.scalars().all())
        logger.info(f"DEBUG: Total bots in system: {len(all_bots)}")
        for b in all_bots:
            logger.info(f"  - Bot: {b.id}, User: {b.user_id}, Status: {b.status}")

        bots = await bot_service.get_user_bots(current_user.id, include_stopped)
        logger.info(f"Found {len(bots)} bots for user {current_user.id}")

        return BotListResponse(bots=[_bot_to_response(bot) for bot in bots], total=len(bots))

    except Exception as e:
        logger.error(f"Error listing bots: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list bots"
        )


@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(
    bot_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Get a specific bot by ID."""
    try:
        bot_service = BotService(db)
        bot = await bot_service.get_bot(uuid.UUID(bot_id), load_relations=True)

        if not bot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

        # Verify ownership
        if bot.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this bot"
            )

        return _bot_to_response(bot)

    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bot ID")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get bot"
        )


@router.put("/{bot_id}", response_model=BotResponse)
async def update_bot(
    bot_id: str,
    request: BotUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a bot's configuration.

    - **name**: New bot name (optional)
    - **capital**: New capital amount (optional)
    - **risk_params**: New risk parameters (optional)
    """
    try:
        bot_service = BotService(db)

        # Verify bot exists and user owns it
        bot = await bot_service.get_bot(uuid.UUID(bot_id))
        if not bot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
        if bot.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        # Prepare update data
        risk_params_dict = request.risk_params.model_dump() if request.risk_params else None
        capital_decimal = Decimal(str(request.capital)) if request.capital else None

        update_data = BotUpdate(
            name=request.name,
            capital=capital_decimal,
            trading_symbols=request.trading_symbols,
            risk_params=risk_params_dict,
            status=request.status,
        )

        updated_bot = await bot_service.update_bot(uuid.UUID(bot_id), update_data)

        if not updated_bot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

        return _bot_to_response(updated_bot)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating bot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update bot"
        )


@router.delete("/{bot_id}", response_model=MessageResponse)
async def delete_bot(
    bot_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Delete (soft delete) a bot.

    Sets the bot status to 'stopped' instead of hard deleting.
    """
    try:
        bot_service = BotService(db)

        # Verify bot exists and user owns it
        bot = await bot_service.get_bot(uuid.UUID(bot_id))
        if not bot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
        if bot.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        success = await bot_service.delete_bot(uuid.UUID(bot_id))

        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

        return MessageResponse(message="Bot deleted successfully")

    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bot ID")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting bot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete bot"
        )


# ============================================================================
# T040: Bot Control Endpoints
# ============================================================================


@router.post("/{bot_id}/start", response_model=MessageResponse)
async def start_bot(
    bot_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Start the trading bot.

    Sets bot status to 'active' and starts the trading engine.
    """
    try:
        bot_service = BotService(db)

        # Verify bot exists and user owns it
        bot = await bot_service.get_bot(uuid.UUID(bot_id))
        if not bot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
        if bot.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        # Check if already active
        if bot.status == BotStatus.ACTIVE:
            return MessageResponse(message="Bot is already active")

        # Update bot status to active
        update_data = BotUpdate(status=BotStatus.ACTIVE.value)
        await bot_service.update_bot(uuid.UUID(bot_id), update_data)

        # Start trading engine immediately via scheduler
        scheduler = get_scheduler()
        success = await scheduler.start_bot(uuid.UUID(bot_id), db)

        if not success:
            logger.error(f"Failed to start trading engine for bot {bot_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Bot status updated but trading engine failed to start",
            )

        logger.info(f"Bot {bot_id} started and trading engine launched")

        return MessageResponse(
            message="Bot started successfully - trading engine is now running",
            details={"bot_id": bot_id, "status": "active", "engine_running": True},
        )

    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bot ID")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to start bot"
        )


@router.post("/{bot_id}/pause", response_model=MessageResponse)
async def pause_bot(
    bot_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Pause the trading bot.

    Sets bot status to 'paused'. Keeps positions open but stops new trades.
    """
    try:
        bot_service = BotService(db)

        # Verify bot exists and user owns it
        bot = await bot_service.get_bot(uuid.UUID(bot_id))
        if not bot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
        if bot.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        # Update bot status to paused
        update_data = BotUpdate(status=BotStatus.PAUSED.value)
        await bot_service.update_bot(uuid.UUID(bot_id), update_data)

        logger.info(f"Bot {bot_id} paused")

        return MessageResponse(
            message="Bot paused successfully", details={"bot_id": bot_id, "status": "paused"}
        )

    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bot ID")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing bot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to pause bot"
        )


@router.post("/{bot_id}/stop", response_model=MessageResponse)
async def stop_bot(
    bot_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Stop the trading bot (emergency stop).

    Sets bot status to 'stopped' and closes all open positions.
    """
    try:
        bot_service = BotService(db)
        position_service = PositionService(db)

        # Verify bot exists and user owns it
        bot = await bot_service.get_bot(uuid.UUID(bot_id))
        if not bot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
        if bot.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        # Get open positions count
        positions = await position_service.get_open_positions(uuid.UUID(bot_id))
        positions_count = len(positions)

        # Update bot status to stopped
        update_data = BotUpdate(status=BotStatus.STOPPED.value)
        await bot_service.update_bot(uuid.UUID(bot_id), update_data)

        # Stop trading engine immediately via scheduler
        scheduler = get_scheduler()
        engine_stopped = await scheduler.stop_bot(uuid.UUID(bot_id))

        logger.info(f"Bot {bot_id} stopped (engine_stopped={engine_stopped})")

        return MessageResponse(
            message="Bot stopped successfully - all positions closed",
            details={
                "bot_id": bot_id,
                "status": "stopped",
                "open_positions": positions_count,
                "engine_stopped": engine_stopped,
            },
        )

    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bot ID")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to stop bot"
        )


# ============================================================================
# T041: Get Bot Positions
# ============================================================================


@router.get("/{bot_id}/positions", response_model=PositionListResponse)
async def get_bot_positions(
    bot_id: str,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all positions for a bot.

    - **status_filter**: Filter by status ('open' or 'closed')
    """
    try:
        bot_service = BotService(db)
        position_service = PositionService(db)

        # Verify bot exists and user owns it
        bot = await bot_service.get_bot(uuid.UUID(bot_id))
        if not bot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
        if bot.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        # Get positions
        if status_filter == "open":
            positions = await position_service.get_open_positions(uuid.UUID(bot_id))
            total = len(positions)
        else:
            positions, total = await position_service.get_all_positions(
                uuid.UUID(bot_id), limit=100, offset=0
            )

        return PositionListResponse(
            positions=[_position_to_response(pos) for pos in positions], total=total
        )

    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bot ID")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get positions"
        )


# ============================================================================
# T042: Get Bot Trades
# ============================================================================


@router.get("/{bot_id}/trades", response_model=TradeListResponse)
async def get_bot_trades(
    bot_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get trade history for a bot.

    - **limit**: Maximum number of trades to return (default: 50)
    - **offset**: Number of trades to skip (default: 0)
    """
    try:
        from sqlalchemy import desc, select

        from ..models.trade import Trade

        bot_service = BotService(db)

        # Verify bot exists and user owns it
        bot = await bot_service.get_bot(uuid.UUID(bot_id))
        if not bot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
        if bot.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        # Get total count
        count_query = select(Trade).where(Trade.bot_id == uuid.UUID(bot_id))
        count_result = await db.execute(count_query)
        total = len(list(count_result.scalars().all()))

        # Get paginated trades
        query = (
            select(Trade)
            .where(Trade.bot_id == uuid.UUID(bot_id))
            .order_by(desc(Trade.executed_at))
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(query)
        trades = list(result.scalars().all())

        return TradeListResponse(
            trades=[_trade_to_response(trade) for trade in trades], total=total
        )

    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bot ID")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get trades"
        )


# ============================================================================
# Equity History Endpoint
# ============================================================================


@router.get("/{bot_id}/equity", response_model=EquityHistoryResponse)
async def get_bot_equity(
    bot_id: str,
    period: str = "24h",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get equity history for dashboard chart.

    - **period**: Time period (1h, 24h, 7d, 30d, all)
    """
    try:
        from datetime import timedelta

        from sqlalchemy import desc, select

        from ..models.equity_snapshot import EquitySnapshot

        bot_service = BotService(db)

        # Verify bot exists and user owns it
        bot = await bot_service.get_bot(uuid.UUID(bot_id))
        if not bot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")
        if bot.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

        # Calculate time range
        from datetime import datetime

        now = datetime.utcnow()
        period_map = {
            "1h": timedelta(hours=1),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
        }
        time_delta = period_map.get(period)
        start_time = now - time_delta if time_delta else None

        # Build query
        query = select(EquitySnapshot).where(EquitySnapshot.bot_id == uuid.UUID(bot_id))
        if start_time:
            query = query.where(EquitySnapshot.timestamp >= start_time)
        query = query.order_by(EquitySnapshot.timestamp)

        result = await db.execute(query)
        snapshots = list(result.scalars().all())

        # Calculate current equity
        current_equity = float(bot.capital)
        initial_capital = float(bot.initial_capital)
        total_return_pct = 0.0
        if initial_capital > 0:
            total_return_pct = ((current_equity - initial_capital) / initial_capital) * 100

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

    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bot ID")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting equity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get equity history"
        )


# ============================================================================
# Helper Functions
# ============================================================================


def _bot_to_response(bot: Bot) -> BotResponse:
    """Convert Bot model to BotResponse."""
    # Calculate PnL safely without accessing lazy-loaded relations
    total_pnl = Decimal("0")
    portfolio_value = bot.capital
    return_pct = Decimal("0")

    # Only calculate if relations are loaded
    if hasattr(bot, "_sa_instance_state") and bot._sa_instance_state.has_identity:
        try:
            total_pnl = bot.total_pnl
            portfolio_value = bot.portfolio_value
            return_pct = bot.return_pct
        except:
            # Fallback if relations not loaded
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


def _position_to_response(position) -> PositionResponse:
    """Convert Position model to PositionResponse."""
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


def _trade_to_response(trade) -> TradeResponse:
    """Convert Trade model to TradeResponse."""
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
