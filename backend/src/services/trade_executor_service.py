"""Trade execution service for executing orders and managing positions."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import config
from ..core.exchange_client import ExchangeClient, get_exchange_client
from ..core.logger import get_logger
from ..models.bot import Bot
from ..models.position import Position, PositionSide, PositionStatus
from ..models.trade import Trade, TradeSide
from .position_service import PositionOpen, PositionService
from .risk_manager_service import RiskManagerService

logger = get_logger(__name__)


class TradeExecutorService:
    """Service for executing trades and managing positions."""

    def __init__(self, db: AsyncSession, exchange_client: Optional[ExchangeClient] = None):
        self.db = db
        self.exchange = exchange_client or get_exchange_client()
        self.position_service = PositionService(db)

    async def execute_entry(
        self, bot: Bot, decision: dict[str, Any], current_price: Decimal
    ) -> Tuple[Optional[Position], Optional[Trade]]:
        """Execute an entry order (open new position)."""
        try:
            symbol = decision.get("symbol", "")
            side = decision.get("side", "long")
            is_short = side.lower() == "short"

            leverage, default_size_pct = self._get_position_settings(is_short)
            size_pct = Decimal(str(decision.get("size_pct", default_size_pct)))

            stop_loss_price = Decimal(str(decision.get("stop_loss", 0)))
            take_profit_price = Decimal(str(decision.get("take_profit", 0)))
            entry_price = Decimal(str(decision.get("entry_price", current_price)))

            if stop_loss_price <= 0 or take_profit_price <= 0:
                logger.error(f"Invalid SL/TP: SL={stop_loss_price}, TP={take_profit_price}")
                return None, None

            confidence = decision.get("confidence", 0.5)
            quantity = RiskManagerService.calculate_position_size(
                capital=bot.capital,
                size_pct=size_pct,
                current_price=current_price,
                confidence=Decimal(str(confidence)),
                leverage=leverage,
            )

            if quantity <= 0:
                logger.warning(f"Skipping {symbol}: quantity={quantity}")
                return None, None

            order_side = "buy" if side.lower() == "long" else "sell"
            actual_price, fees = await self._execute_order(
                bot, symbol, order_side, quantity, current_price
            )

            position_data = PositionOpen(
                symbol=symbol,
                side=side,
                quantity=quantity,
                entry_price=actual_price,
                stop_loss=stop_loss_price,
                take_profit=take_profit_price,
                leverage=leverage,
                invalidation_condition=decision.get("invalidation_condition"),
            )

            logger.info(
                f"Position: Entry={actual_price:,.2f}, SL={stop_loss_price:,.2f}, TP={take_profit_price:,.2f}"
            )

            position = await self.position_service.open_position(bot.id, position_data)

            trade = Trade(
                bot_id=bot.id,
                position_id=position.id,
                symbol=symbol,
                side=TradeSide.BUY if order_side == "buy" else TradeSide.SELL,
                quantity=quantity,
                price=actual_price,
                fees=fees,
                realized_pnl=Decimal("0"),
                executed_at=datetime.utcnow(),
            )
            self.db.add(trade)

            bot = await self._reload_bot(bot.id)
            margin_cost = (actual_price * quantity) / position_data.leverage
            bot.capital -= margin_cost + fees

            await self.db.commit()
            await self.db.refresh(trade)
            await self.db.refresh(position)

            if not bot.paper_trading:
                await self._set_stop_orders(symbol, side, quantity, stop_loss_price, take_profit_price)

            logger.info(f"Entry: Position {position.id}, Capital: ${bot.capital:,.2f}")
            return position, trade

        except (ValueError, ConnectionError) as e:
            logger.error(f"Trade execution error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error executing entry: {e}")
            await self.db.rollback()
            return None, None

    async def execute_exit(
        self, position: Position, current_price: Decimal, reason: str = "manual_close"
    ) -> Optional[Trade]:
        """Execute an exit order (close position)."""
        try:
            order_side = "sell" if position.side == PositionSide.LONG else "buy"
            bot = await self._get_bot(position.bot_id)

            if bot is None:
                logger.error(f"Bot {position.bot_id} not found")
                return None

            actual_price, fees = await self._execute_order(
                bot, position.symbol, order_side, position.quantity, current_price, is_exit=True
            )

            realized_pnl = position.calculate_realized_pnl(actual_price, position.quantity) - fees
            await self.position_service.close_position(position.id, actual_price, reason)

            trade = Trade(
                bot_id=position.bot_id,
                position_id=position.id,
                symbol=position.symbol,
                side=TradeSide.SELL if order_side == "sell" else TradeSide.BUY,
                quantity=position.quantity,
                price=actual_price,
                fees=fees,
                realized_pnl=realized_pnl,
                executed_at=datetime.utcnow(),
            )
            self.db.add(trade)

            bot = await self._reload_bot(position.bot_id)
            leverage = position.leverage or Decimal(str(config.DEFAULT_LEVERAGE))
            margin_released = (position.entry_price * position.quantity) / leverage
            bot.capital += margin_released + realized_pnl

            await self.db.commit()
            await self.db.refresh(trade)
            await self.db.refresh(bot)

            logger.info(f"Exit: Position {position.id}, PnL: {realized_pnl:,.2f}, Capital: ${bot.capital:,.2f}")
            return trade

        except (ValueError, ConnectionError) as e:
            logger.error(f"Trade execution error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error executing exit: {e}")
            await self.db.rollback()
            return None

    def _get_position_settings(self, is_short: bool) -> Tuple[Decimal, float]:
        """Get leverage and default size based on position type."""
        if is_short:
            return Decimal(str(config.SHORT_MAX_LEVERAGE)), config.SHORT_POSITION_SIZE_PCT
        return Decimal(str(config.DEFAULT_LEVERAGE)), config.DEFAULT_POSITION_SIZE_PCT

    async def _execute_order(
        self,
        bot: Bot,
        symbol: str,
        side: str,
        quantity: Decimal,
        current_price: Decimal,
        is_exit: bool = False,
    ) -> Tuple[Decimal, Decimal]:
        """Execute market order or simulate for paper trading."""
        if bot and not bot.paper_trading:
            try:
                order = await self.exchange.create_order(
                    symbol=symbol, side=side, amount=float(quantity), order_type="market"
                )
                actual_price = Decimal(str(order.get("price", current_price)))
                fees = Decimal(str(order.get("fee", {}).get("cost", 0)))
                action = "Exit" if is_exit else "Entry"
                logger.info(f"{action} order: {side} {quantity} {symbol} @ {actual_price}")
                return actual_price, fees
            except Exception as e:
                logger.error(f"Order execution error: {e}")
                return Decimal(str(current_price)), Decimal("0")

        actual_price = Decimal(str(current_price))
        fees = actual_price * quantity * Decimal(str(config.PAPER_TRADING_FEE_PCT))
        action = "PAPER EXIT" if is_exit else "PAPER"
        logger.info(f"{action}: {side} {quantity} {symbol} @ {actual_price}")
        return actual_price, fees

    async def _reload_bot(self, bot_id: UUID) -> Bot:
        """Reload bot from database to get latest capital."""
        query = select(Bot).where(Bot.id == bot_id)
        result = await self.db.execute(query)
        return result.scalar_one()

    async def _set_stop_orders(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        stop_loss_price: Decimal,
        take_profit_price: Decimal,
    ) -> None:
        """Set stop loss and take profit orders on exchange."""
        try:
            stop_side = "sell" if side.lower() == "long" else "buy"
            await self.exchange.create_stop_loss_order(
                symbol=symbol, side=stop_side, amount=float(quantity), stop_price=float(stop_loss_price)
            )
            await self.exchange.create_take_profit_order(
                symbol=symbol, side=stop_side, amount=float(quantity), take_profit_price=float(take_profit_price)
            )
            logger.info(f"Stop orders: SL={stop_loss_price}, TP={take_profit_price}")
        except Exception as e:
            logger.error(f"Error setting stop orders: {e}")

    async def _get_bot(self, bot_id: UUID) -> Optional[Bot]:
        """Get bot by ID."""
        query = select(Bot).where(Bot.id == bot_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
