"""Trade execution service for executing orders and managing positions."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exchange_client import ExchangeClient, get_exchange_client
from ..core.logger import get_logger
from ..models.bot import Bot
from ..models.position import Position, PositionSide, PositionStatus
from ..models.trade import Trade, TradeSide
from .position_service import PositionService, PositionOpen
from .risk_manager_service import RiskManagerService

logger = get_logger(__name__)


class TradeExecutorService:
    """Service for executing trades and managing positions."""
    
    def __init__(
        self,
        db: AsyncSession,
        exchange_client: Optional[ExchangeClient] = None
    ):
        """
        Initialize trade executor service.
        
        Args:
            db: Database session
            exchange_client: Optional exchange client
        """
        self.db = db
        self.exchange = exchange_client or get_exchange_client()
        self.position_service = PositionService(db)
    
    async def execute_entry(
        self,
        bot: Bot,
        decision: dict,
        current_price: Decimal
    ) -> Tuple[Optional[Position], Optional[Trade]]:
        """
        Execute an entry order (open new position).
        
        Args:
            bot: Bot instance
            decision: LLM decision with trade details
            current_price: Current market price
            
        Returns:
            Tuple of (Position, Trade) or (None, None) if execution fails
        """
        try:
            # Extract decision details
            symbol = decision.get('symbol', '')
            side = decision.get('side', 'long')
            size_pct = Decimal(str(decision.get('size_pct', 0)))
            stop_loss_pct = Decimal(str(decision.get('stop_loss_pct', 0)))
            take_profit_pct = Decimal(str(decision.get('take_profit_pct', 0)))
            
            # Calculate position size
            quantity = RiskManagerService.calculate_position_size(
                capital=bot.capital,
                size_pct=size_pct,
                current_price=current_price,
                leverage=1.0  # No leverage for v1
            )
            
            # Calculate stop loss and take profit prices
            stop_loss_price = RiskManagerService.calculate_stop_loss_price(
                entry_price=current_price,
                stop_loss_pct=stop_loss_pct,
                side=side
            )
            
            take_profit_price = RiskManagerService.calculate_take_profit_price(
                entry_price=current_price,
                take_profit_pct=take_profit_pct,
                side=side
            )
            
            # Determine order side (buy for long, sell for short)
            order_side = 'buy' if side.lower() == 'long' else 'sell'
            
            # Execute market order (if not paper trading)
            if not bot.paper_trading:
                try:
                    order = await self.exchange.create_order(
                        symbol=symbol,
                        side=order_side,
                        amount=float(quantity),
                        order_type='market'
                    )
                    
                    # Get actual execution price and fees from order
                    actual_price = Decimal(str(order.get('price', current_price)))
                    fees = Decimal(str(order.get('fee', {}).get('cost', 0)))
                    
                    logger.info(f"Market order executed: {order_side} {quantity} {symbol} @ {actual_price}")
                    
                except Exception as e:
                    logger.error(f"Error executing market order: {e}")
                    # In case of exchange error, still create position with current price
                    actual_price = current_price
                    fees = Decimal("0")
            else:
                # Paper trading mode
                actual_price = current_price
                fees = actual_price * quantity * Decimal("0.001")  # Estimate 0.1% fee
                logger.info(f"PAPER: {order_side} {quantity} {symbol} @ {actual_price}")
            
            # Create position record
            position_data = PositionOpen(
                symbol=symbol,
                side=side,
                quantity=quantity,
                entry_price=actual_price,
                stop_loss=stop_loss_price,
                take_profit=take_profit_price
            )
            
            position = await self.position_service.open_position(bot.id, position_data)
            
            # Create trade record
            trade = Trade(
                bot_id=bot.id,
                position_id=position.id,
                symbol=symbol,
                side=TradeSide.BUY if order_side == 'buy' else TradeSide.SELL,
                quantity=quantity,
                price=actual_price,
                fees=fees,
                realized_pnl=Decimal("0"),  # Entry trade has no PnL
                executed_at=datetime.utcnow()
            )
            
            self.db.add(trade)
            
            # Merge bot into current session to update capital
            bot = await self.db.merge(bot)
            
            # Update bot capital: deduct the cost of the position
            cost = actual_price * quantity + fees
            bot.capital -= cost
            
            await self.db.commit()
            await self.db.refresh(trade)
            await self.db.refresh(bot)
            
            # Set stop loss and take profit orders (if not paper trading)
            if not bot.paper_trading:
                await self._set_stop_orders(symbol, side, quantity, stop_loss_price, take_profit_price)
            
            logger.info(f"Entry executed: Position {position.id}, Trade {trade.id}, Capital: ${bot.capital:,.2f}")
            return position, trade
            
        except Exception as e:
            logger.error(f"Error executing entry: {e}")
            await self.db.rollback()
            return None, None
    
    async def execute_exit(
        self,
        position: Position,
        current_price: Decimal,
        reason: str = "manual_close"
    ) -> Optional[Trade]:
        """
        Execute an exit order (close position).
        
        Args:
            position: Position to close
            current_price: Current market price
            reason: Reason for closing
            
        Returns:
            Trade record or None if execution fails
        """
        try:
            # Determine order side (opposite of position side)
            order_side = 'sell' if position.side == PositionSide.LONG else 'buy'
            
            # Execute market order (if not paper trading)
            bot = await self._get_bot(position.bot_id)
            if bot and not bot.paper_trading:
                try:
                    order = await self.exchange.create_order(
                        symbol=position.symbol,
                        side=order_side,
                        amount=float(position.quantity),
                        order_type='market'
                    )
                    
                    actual_price = Decimal(str(order.get('price', current_price)))
                    fees = Decimal(str(order.get('fee', {}).get('cost', 0)))
                    
                    logger.info(f"Exit order executed: {order_side} {position.quantity} {position.symbol} @ {actual_price}")
                    
                except Exception as e:
                    logger.error(f"Error executing exit order: {e}")
                    actual_price = current_price
                    fees = Decimal("0")
            else:
                # Paper trading mode
                actual_price = current_price
                fees = actual_price * position.quantity * Decimal("0.001")
                logger.info(f"PAPER EXIT: {order_side} {position.quantity} {position.symbol} @ {actual_price}")
            
            # Calculate realized PnL
            realized_pnl = position.calculate_realized_pnl(actual_price, position.quantity)
            realized_pnl -= fees  # Subtract fees from PnL
            
            # Close position
            await self.position_service.close_position(position.id, actual_price, reason)
            
            # Create trade record
            trade = Trade(
                bot_id=position.bot_id,
                position_id=position.id,
                symbol=position.symbol,
                side=TradeSide.SELL if order_side == 'sell' else TradeSide.BUY,
                quantity=position.quantity,
                price=actual_price,
                fees=fees,
                realized_pnl=realized_pnl,
                executed_at=datetime.utcnow()
            )
            
            self.db.add(trade)
            
            # Merge bot into current session to update capital
            bot = await self.db.merge(bot)
            
            # Update bot capital: add back the proceeds from selling
            proceeds = actual_price * position.quantity - fees
            bot.capital += proceeds
            
            await self.db.commit()
            await self.db.refresh(trade)
            await self.db.refresh(bot)
            
            logger.info(f"Exit executed: Position {position.id}, PnL: {realized_pnl:,.2f}, Capital: ${bot.capital:,.2f}")
            return trade
            
        except Exception as e:
            logger.error(f"Error executing exit: {e}")
            await self.db.rollback()
            return None
    
    async def _set_stop_orders(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        stop_loss_price: Decimal,
        take_profit_price: Decimal
    ) -> None:
        """
        Set stop loss and take profit orders on exchange.
        
        Args:
            symbol: Trading pair
            side: Position side
            quantity: Position quantity
            stop_loss_price: Stop loss trigger price
            take_profit_price: Take profit trigger price
        """
        try:
            # Determine order side for stop orders (opposite of position)
            stop_side = 'sell' if side.lower() == 'long' else 'buy'
            
            # Create stop loss order
            await self.exchange.create_stop_loss_order(
                symbol=symbol,
                side=stop_side,
                amount=float(quantity),
                stop_price=float(stop_loss_price)
            )
            
            # Create take profit order
            await self.exchange.create_take_profit_order(
                symbol=symbol,
                side=stop_side,
                amount=float(quantity),
                take_profit_price=float(take_profit_price)
            )
            
            logger.info(f"Stop orders set: SL @ {stop_loss_price}, TP @ {take_profit_price}")
            
        except Exception as e:
            logger.error(f"Error setting stop orders: {e}")
            # Don't fail the whole trade if stop orders fail
    
    async def _get_bot(self, bot_id: uuid.UUID) -> Optional[Bot]:
        """Get bot by ID."""
        from sqlalchemy import select
        query = select(Bot).where(Bot.id == bot_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()