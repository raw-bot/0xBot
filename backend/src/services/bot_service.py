"""Bot service for managing AI trading agents."""

import os
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.bot import Bot, BotStatus, ModelName

FORCED_MODEL_DEEPSEEK = "deepseek-chat"


class BotCreate:
    """Data for creating a new bot."""

    def __init__(
        self,
        name: str,
        model_name: str,
        capital: Decimal,
        trading_symbols: Optional[list[str]] = None,
        risk_params: Optional[dict] = None,
        paper_trading: bool = True,
    ):
        self.name = name
        self.model_name = model_name
        self.capital = capital
        self.trading_symbols = trading_symbols or ["BTC/USDT"]  # Default to BTC only
        self.risk_params = risk_params or {
            "max_position_pct": 0.08,  # Harmonized with prompt LLM (8% max position)
            "max_drawdown_pct": 0.15,  # Reduced from 0.20 to 0.15 (tighter risk control)
            "max_trades_per_day": 20,  # Reduced from 50 to 20 (more selective)
        }
        self.paper_trading = paper_trading


class BotUpdate:
    """Data for updating a bot."""

    def __init__(
        self,
        name: Optional[str] = None,
        capital: Optional[Decimal] = None,
        trading_symbols: Optional[list[str]] = None,
        risk_params: Optional[dict] = None,
        status: Optional[str] = None,
    ):
        self.name = name
        self.capital = capital
        self.trading_symbols = trading_symbols
        self.risk_params = risk_params
        self.status = status


class BotService:
    """Service for managing bot lifecycle and operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_bot(self, user_id: UUID, data: BotCreate) -> Bot:
        """
        Create a new trading bot.

        Args:
            user_id: ID of the user creating the bot
            data: Bot creation data

        Returns:
            Created bot instance

        Raises:
            ValueError: If validation fails
        """
        # Validate capital
        if data.capital < Decimal("100"):
            raise ValueError("Capital must be at least $100")

        # Validate model name
        valid_models = [m.value for m in ModelName]
        if data.model_name not in valid_models:
            raise ValueError(f"Invalid model_name. Must be one of: {valid_models}")

        # Validate risk parameters
        self._validate_risk_params(data.risk_params)

        # Validate trading symbols
        self._validate_trading_symbols(data.trading_symbols)

        # Create bot
        bot = Bot(
            user_id=user_id,
            name=data.name,
            model_name=data.model_name,  # String directement - validation déjà faite ligne 78-80
            initial_capital=data.capital,  # Set initial capital
            capital=data.capital,  # Current capital starts equal to initial
            trading_symbols=data.trading_symbols,
            risk_params=data.risk_params,
            paper_trading=data.paper_trading,
            status=BotStatus.INACTIVE,
        )

        self.db.add(bot)
        await self.db.commit()
        await self.db.refresh(bot)

        return bot

    async def get_bot(self, bot_id: UUID, load_relations: bool = False) -> Optional[Bot]:
        """
        Get a bot by ID.

        Args:
            bot_id: Bot ID
            load_relations: If True, eagerly load positions, trades, decisions

        Returns:
            Bot instance or None if not found
        """
        query = select(Bot).where(Bot.id == bot_id)

        if load_relations:
            query = query.options(
                selectinload(Bot.positions), selectinload(Bot.trades), selectinload(Bot.decisions)
            )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_bot(self, bot_id: UUID, data: BotUpdate) -> Optional[Bot]:
        """
        Update bot configuration.

        Args:
            bot_id: Bot ID
            data: Update data

        Returns:
            Updated bot or None if not found

        Raises:
            ValueError: If validation fails
        """
        bot = await self.get_bot(bot_id)
        if not bot:
            return None

        # Update fields if provided
        if data.name is not None:
            bot.name = data.name

        if data.capital is not None:
            if data.capital < Decimal("100"):
                raise ValueError("Capital must be at least $100")
            # When manually updating capital, also update initial_capital
            # This allows users to add/remove funds
            bot.initial_capital = data.capital
            bot.capital = data.capital

        if data.trading_symbols is not None:
            self._validate_trading_symbols(data.trading_symbols)
            bot.trading_symbols = data.trading_symbols

        if data.risk_params is not None:
            self._validate_risk_params(data.risk_params)
            bot.risk_params = data.risk_params

        if data.status is not None:
            # Validate status
            valid_statuses = [s.value for s in BotStatus]
            if data.status not in valid_statuses:
                raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
            bot.status = data.status

        bot.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(bot)

        return bot

    async def delete_bot(self, bot_id: UUID) -> bool:
        """
        Delete a bot (soft delete by setting status to stopped).

        Args:
            bot_id: Bot ID

        Returns:
            True if deleted, False if not found
        """
        bot = await self.get_bot(bot_id)
        if not bot:
            return False

        # Set status to stopped instead of hard delete
        bot.status = BotStatus.STOPPED
        bot.updated_at = datetime.utcnow()

        await self.db.commit()

        return True

    async def get_user_bots(self, user_id: UUID, include_stopped: bool = False) -> list[Bot]:
        """
        Get all bots for a user.

        Args:
            user_id: User ID
            include_stopped: If True, include stopped bots

        Returns:
            List of bots
        """
        query = select(Bot).where(Bot.user_id == user_id)

        if not include_stopped:
            query = query.where(Bot.status != BotStatus.STOPPED)

        query = query.order_by(Bot.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_user_bots_paginated(
        self, user_id: UUID, include_stopped: bool = False, limit: int = 100, offset: int = 0
    ) -> tuple[list[Bot], int]:
        """
        Get paginated bots for a user.

        Args:
            user_id: User ID
            include_stopped: If True, include stopped bots
            limit: Number of results per page
            offset: Offset for pagination

        Returns:
            Tuple of (list of bots, total count)
        """
        # Build count query
        count_query = select(Bot).where(Bot.user_id == user_id)
        if not include_stopped:
            count_query = count_query.where(Bot.status != BotStatus.STOPPED)

        count_result = await self.db.execute(count_query)
        total = len(list(count_result.scalars().all()))

        # Build paginated query
        query = select(Bot).where(Bot.user_id == user_id)
        if not include_stopped:
            query = query.where(Bot.status != BotStatus.STOPPED)

        query = query.order_by(Bot.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        bots = list(result.scalars().all())

        return bots, total

    async def get_active_bots(self) -> list[Bot]:
        """
        Get all active bots across all users.

        Returns:
            List of active bots
        """
        query = select(Bot).where(Bot.status == BotStatus.ACTIVE)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    def _validate_risk_params(self, risk_params: dict) -> None:
        """
        Validate risk parameters.

        Args:
            risk_params: Risk parameters dict

        Raises:
            ValueError: If validation fails
        """
        required_keys = {"max_position_pct", "max_drawdown_pct", "max_trades_per_day"}
        if not all(key in risk_params for key in required_keys):
            raise ValueError(f"Risk params must include: {required_keys}")

        # Validate ranges
        max_pos = risk_params["max_position_pct"]
        if not (0 < max_pos <= 1):
            raise ValueError("max_position_pct must be between 0 and 1")

        max_dd = risk_params["max_drawdown_pct"]
        if not (0 < max_dd <= 1):
            raise ValueError("max_drawdown_pct must be between 0 and 1")

        max_trades = risk_params["max_trades_per_day"]
        if not isinstance(max_trades, int) or max_trades < 1:
            raise ValueError("max_trades_per_day must be a positive integer")

    def _validate_trading_symbols(self, trading_symbols: list[str]) -> None:
        """
        Validate trading symbols list.

        Args:
            trading_symbols: List of trading pairs (e.g., ["BTC/USDT", "ETH/USDT"])

        Raises:
            ValueError: If validation fails
        """
        if not trading_symbols or len(trading_symbols) == 0:
            raise ValueError("At least one trading symbol is required")

        # Validate format: should be like "BTC/USDT"
        for symbol in trading_symbols:
            if not isinstance(symbol, str):
                raise ValueError(f"Symbol must be string: {symbol}")
            if "/" not in symbol:
                raise ValueError(f"Invalid symbol format (should be BASE/QUOTE): {symbol}")
            parts = symbol.split("/")
            if len(parts) != 2:
                raise ValueError(f"Invalid symbol format: {symbol}")
            if not parts[0] or not parts[1]:
                raise ValueError(f"Invalid symbol format: {symbol}")
