"""Position service for managing trading positions."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import config
from ..models.position import Position, PositionSide, PositionStatus


class PositionOpen:
    """Data for opening a new position."""

    def __init__(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        entry_price: Decimal,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
        leverage: Decimal = Decimal(str(config.DEFAULT_LEVERAGE)),
        invalidation_condition: Optional[str] = None,
    ):
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.leverage = leverage
        self.invalidation_condition = invalidation_condition


class PositionService:
    """Service for managing trading positions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def open_position(self, bot_id: UUID, data: PositionOpen) -> Position:
        """Open a new trading position."""
        self._validate_position_data(data)

        position = Position(
            bot_id=bot_id,
            symbol=data.symbol,
            side=data.side,
            quantity=data.quantity,
            entry_price=data.entry_price,
            current_price=data.entry_price,
            stop_loss=data.stop_loss,
            take_profit=data.take_profit,
            leverage=data.leverage,
            status=PositionStatus.OPEN,
            opened_at=datetime.utcnow(),
        )

        self.db.add(position)
        await self.db.commit()
        await self.db.refresh(position)
        return position

    def _validate_position_data(self, data: PositionOpen) -> None:
        """Validate position data before opening."""
        valid_sides = [s.value for s in PositionSide]
        if data.side not in valid_sides:
            raise ValueError(f"Invalid side. Must be one of: {valid_sides}")
        if data.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if data.entry_price <= 0:
            raise ValueError("Entry price must be positive")
        if data.stop_loss is not None and data.stop_loss <= 0:
            raise ValueError("Stop loss must be positive")
        if data.take_profit is not None and data.take_profit <= 0:
            raise ValueError("Take profit must be positive")

    async def close_position(
        self, position_id: UUID, exit_price: Decimal, reason: str = "manual_close"
    ) -> Optional[Position]:
        """Close a trading position."""
        position = await self.get_position(position_id)
        if not position:
            return None
        if position.status == PositionStatus.CLOSED:
            raise ValueError("Position is already closed")
        if exit_price <= 0:
            raise ValueError("Exit price must be positive")

        position.current_price = exit_price
        position.status = PositionStatus.CLOSED
        position.closed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(position)
        return position

    async def update_current_price(self, position_id: UUID, price: Decimal) -> Optional[Position]:
        """Update the current price of an open position."""
        position = await self.get_position(position_id)
        if not position:
            return None
        if position.status == PositionStatus.CLOSED:
            raise ValueError("Cannot update price of closed position")
        if price <= 0:
            raise ValueError("Price must be positive")

        position.current_price = price
        await self.db.commit()
        await self.db.refresh(position)
        return position

    async def get_position(self, position_id: UUID) -> Optional[Position]:
        """Get a position by ID."""
        query = select(Position).where(Position.id == position_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_open_positions(
        self, bot_id: UUID, symbol: Optional[str] = None
    ) -> list[Position]:
        """Get all open positions for a bot."""
        query = select(Position).where(
            Position.bot_id == bot_id, Position.status == PositionStatus.OPEN
        )
        if symbol:
            query = query.where(Position.symbol == symbol)
        query = query.order_by(Position.opened_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_all_positions(
        self, bot_id: UUID, limit: int = 100, offset: int = 0
    ) -> tuple[list[Position], int]:
        """Get all positions for a bot with pagination."""
        count_query = select(Position).where(Position.bot_id == bot_id)
        count_result = await self.db.execute(count_query)
        total = len(list(count_result.scalars().all()))

        query = (
            select(Position)
            .where(Position.bot_id == bot_id)
            .order_by(Position.opened_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def check_stop_loss_take_profit(
        self, position: Position, current_price: Decimal
    ) -> Optional[str]:
        """Check if stop loss or take profit is hit."""
        if position.status == PositionStatus.CLOSED:
            return None

        is_long = position.side == PositionSide.LONG

        if position.stop_loss:
            sl_hit = (is_long and current_price <= position.stop_loss) or \
                     (not is_long and current_price >= position.stop_loss)
            if sl_hit:
                return "stop_loss"

        if position.take_profit:
            tp_hit = (is_long and current_price >= position.take_profit) or \
                     (not is_long and current_price <= position.take_profit)
            if tp_hit:
                return "take_profit"

        return None

    async def get_total_exposure(self, bot_id: UUID) -> Decimal:
        """Calculate total market exposure (sum of position values)."""
        positions = await self.get_open_positions(bot_id)
        return sum((pos.position_value for pos in positions), Decimal("0"))
