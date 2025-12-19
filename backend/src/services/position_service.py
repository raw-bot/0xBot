"""Position service for managing trading positions."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.position import Position, PositionSide, PositionStatus
from ..models.trade import Trade, TradeSide


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
        leverage: Decimal = Decimal("10.0"),
    ):
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.leverage = leverage

    async def get_open_positions_with_relations(self, bot_id):
        """Récupère les positions avec toutes les relations chargées."""
        query = (
            select(Position)
            .options(selectinload(Position.bot))
            .where(Position.bot_id == bot_id, Position.status == PositionStatus.OPEN)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_positions_batch(self, bot_ids: list) -> Dict[str, list]:
        """Récupère les positions pour plusieurs bots en une seule requête."""
        if not bot_ids:
            return {}

        query = select(Position).where(Position.bot_id.in_(bot_ids))
        result = await self.db.execute(query)
        positions = result.scalars().all()

        # Grouper par bot_id
        positions_by_bot = {}
        for position in positions:
            bot_id = str(position.bot_id)
            if bot_id not in positions_by_bot:
                positions_by_bot[bot_id] = []
            positions_by_bot[bot_id].append(position)

        return positions_by_bot

    async def get_recent_trades(self, bot_id: str, hours: int = 24) -> list:
        """Récupère les trades récents avec une limite de temps."""
        from datetime import datetime, timedelta

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        query = (
            select(Trade)
            .where(Trade.bot_id == bot_id, Trade.executed_at >= cutoff_time)
            .order_by(Trade.executed_at.desc())
            .limit(100)
        )

        result = await self.db.execute(query)
        return result.scalars().all()


class PositionService:
    """Service for managing trading positions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def open_position(self, bot_id: uuid.UUID, data: PositionOpen) -> Position:
        """
        Open a new trading position.

        Args:
            bot_id: ID of the bot opening the position
            data: Position data

        Returns:
            Created position instance

        Raises:
            ValueError: If validation fails
        """
        # Validate side
        valid_sides = [s.value for s in PositionSide]
        if data.side not in valid_sides:
            raise ValueError(f"Invalid side. Must be one of: {valid_sides}")

        # Validate quantities and prices
        if data.quantity <= 0:
            raise ValueError("Quantity must be positive")

        if data.entry_price <= 0:
            raise ValueError("Entry price must be positive")

        if data.stop_loss is not None and data.stop_loss <= 0:
            raise ValueError("Stop loss must be positive")

        if data.take_profit is not None and data.take_profit <= 0:
            raise ValueError("Take profit must be positive")

        # Create position
        position = Position(
            bot_id=bot_id,
            symbol=data.symbol,
            side=data.side,
            quantity=data.quantity,
            entry_price=data.entry_price,
            current_price=data.entry_price,  # Initially same as entry
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

    async def close_position(
        self, position_id: uuid.UUID, exit_price: Decimal, reason: str = "manual_close"
    ) -> Optional[Position]:
        """
        Close a trading position.

        Args:
            position_id: Position ID
            exit_price: Price at which position is closed
            reason: Reason for closing (manual_close, stop_loss, take_profit)

        Returns:
            Closed position or None if not found

        Raises:
            ValueError: If position already closed or invalid price
        """
        position = await self.get_position(position_id)
        if not position:
            return None

        if position.status == PositionStatus.CLOSED:
            raise ValueError("Position is already closed")

        if exit_price <= 0:
            raise ValueError("Exit price must be positive")

        # Update position
        position.current_price = exit_price
        position.status = PositionStatus.CLOSED
        position.closed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(position)

        return position

    async def update_current_price(
        self, position_id: uuid.UUID, price: Decimal
    ) -> Optional[Position]:
        """
        Update the current price of an open position.

        Args:
            position_id: Position ID
            price: New current price

        Returns:
            Updated position or None if not found

        Raises:
            ValueError: If position is closed or invalid price
        """
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

    async def get_position(self, position_id: uuid.UUID) -> Optional[Position]:
        """
        Get a position by ID.

        Args:
            position_id: Position ID

        Returns:
            Position instance or None if not found
        """
        query = select(Position).where(Position.id == position_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_open_positions(
        self, bot_id: uuid.UUID, symbol: Optional[str] = None
    ) -> list[Position]:
        """
        Get all open positions for a bot.

        Args:
            bot_id: Bot ID
            symbol: Optional symbol filter

        Returns:
            List of open positions
        """
        query = select(Position).where(
            Position.bot_id == bot_id, Position.status == PositionStatus.OPEN
        )

        if symbol:
            query = query.where(Position.symbol == symbol)

        query = query.order_by(Position.opened_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_all_positions(
        self, bot_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> tuple[list[Position], int]:
        """
        Get all positions for a bot with pagination.

        Args:
            bot_id: Bot ID
            limit: Maximum number of positions to return
            offset: Number of positions to skip

        Returns:
            Tuple of (positions list, total count)
        """
        # Get total count
        count_query = select(Position).where(Position.bot_id == bot_id)
        count_result = await self.db.execute(count_query)
        total = len(list(count_result.scalars().all()))

        # Get paginated positions
        query = (
            select(Position)
            .where(Position.bot_id == bot_id)
            .order_by(Position.opened_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        positions = list(result.scalars().all())

        return positions, total

    async def check_stop_loss_take_profit(
        self, position: Position, current_price: Decimal
    ) -> Optional[str]:
        """
        Check if stop loss or take profit is hit.

        Args:
            position: Position to check
            current_price: Current market price

        Returns:
            "stop_loss" or "take_profit" if hit, None otherwise
        """
        if position.status == PositionStatus.CLOSED:
            return None

        # Check stop loss
        if position.stop_loss:
            if position.side == PositionSide.LONG and current_price <= position.stop_loss:
                return "stop_loss"
            elif position.side == PositionSide.SHORT and current_price >= position.stop_loss:
                return "stop_loss"

        # Check take profit
        if position.take_profit:
            if position.side == PositionSide.LONG and current_price >= position.take_profit:
                return "take_profit"
            elif position.side == PositionSide.SHORT and current_price <= position.take_profit:
                return "take_profit"

        return None

    async def get_total_exposure(self, bot_id: uuid.UUID) -> Decimal:
        """
        Calculate total market exposure (sum of position values).

        Args:
            bot_id: Bot ID

        Returns:
            Total exposure value
        """
        positions = await self.get_open_positions(bot_id)

        total = Decimal("0")
        for pos in positions:
            total += pos.position_value

        return total
