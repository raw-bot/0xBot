"""Trading Orchestrator - Coordinates all trading blocks."""

import asyncio
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, Union

from sqlalchemy import select, text

from ..core.activity_logger import ActivityLogger
from ..core.database import AsyncSessionLocal
from ..core.llm_client import LLMClient
from ..core.logger import get_logger
from ..models.bot import Bot, BotStatus
from ..models.signal import SignalType
from .block_execution import ExecutionBlock
from .block_indicator_decision import IndicatorDecisionBlock
from .block_llm_decision import LLMDecisionBlock
from .block_market_data import MarketDataBlock
from .block_portfolio import PortfolioBlock
from .block_risk import RiskBlock
from .block_trinity_decision import TrinityDecisionBlock

logger = get_logger(__name__)

RETRY_DELAY = 30


class TradingOrchestrator:
    """Orchestrates the complete trading cycle using modular blocks."""

    def __init__(
        self,
        bot_id: uuid.UUID,
        cycle_interval: int = 180,
        llm_client: Optional[LLMClient] = None,
        decision_mode: str = "trinity",  # "indicator", "llm", or "trinity"
        paper_trading: bool = True,  # Connect to OKX live or paper trading
    ):
        self.bot_id = bot_id
        self.cycle_interval = cycle_interval
        self.decision_mode = decision_mode.lower()
        self.paper_trading = paper_trading
        self._running = False
        self._task: Optional[asyncio.Task[Any]] = None

        self.market_data = MarketDataBlock(paper_trading=paper_trading)
        self.portfolio = PortfolioBlock(bot_id)

        # Initialize all decision blocks - use one based on decision_mode
        self.indicator_decision = IndicatorDecisionBlock()
        self.trinity_decision = TrinityDecisionBlock()
        self.llm_decision = LLMDecisionBlock(llm_client=llm_client, bot_id=bot_id) if llm_client else None

        # Set active decision block
        self.decision: Union[LLMDecisionBlock, TrinityDecisionBlock, IndicatorDecisionBlock]
        if self.decision_mode == "llm" and self.llm_decision:
            self.decision = self.llm_decision
            logger.info(f"🧠 Using LLM-based decision mode + Trade Filter + Memory")
        elif self.decision_mode == "trinity":
            self.decision = self.trinity_decision
            logger.info(f"📈 Using Trinity indicator framework (confluence scoring)")
        else:
            self.decision = self.indicator_decision
            logger.info(f"📊 Using legacy indicator-based decision mode")

        self.risk = RiskBlock()
        self.execution = ExecutionBlock(bot_id, paper_trading=paper_trading)

    async def start(self) -> None:
        """Start the trading loop."""
        self._running = True
        logger.info(f"Starting trading orchestrator (cycles every {self.cycle_interval}s)")

        while self._running:
            try:
                if not await self._is_bot_active():
                    logger.warning("Bot is not active, stopping orchestrator")
                    break

                cycle_start = datetime.utcnow()
                await self._run_cycle()
                cycle_time = (datetime.utcnow() - cycle_start).total_seconds()
                logger.info(f"Cycle completed in {cycle_time:.1f}s")

                sleep_time = max(0, self.cycle_interval - cycle_time)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                logger.info("Trading orchestrator cancelled")
                break
            except Exception as e:
                logger.error(f"Error in trading cycle: {e}")
                await asyncio.sleep(RETRY_DELAY)

    async def stop(self) -> None:
        """Stop the trading loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Trading orchestrator stopped")

    async def _is_bot_active(self) -> bool:
        """Check if bot is still active in database."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Bot).where(Bot.id == self.bot_id))
            bot = result.scalar_one_or_none()
            if bot is None:
                return False
            return bot.status == BotStatus.ACTIVE.value

    async def _run_cycle(self) -> None:
        """Execute one complete trading cycle."""
        market_data = await self.market_data.fetch_all()
        if not market_data:
            logger.warning("No market data available, skipping cycle")
            return

        portfolio_state = await self.portfolio.get_state()
        logger.info(
            f"Portfolio: Cash ${float(portfolio_state.cash):,.2f} | "
            f"Equity ${float(portfolio_state.equity):,.2f} | "
            f"Positions: {len(portfolio_state.open_positions)}"
        )

        await self._check_exits(portfolio_state.open_positions, market_data)

        portfolio_context = {
            "cash": float(portfolio_state.cash),
            "equity": float(portfolio_state.equity),
            "return_pct": portfolio_state.return_pct,
            "positions": portfolio_state.open_positions,
        }

        decisions = await self.decision.get_decisions(
            market_data=market_data,
            portfolio_context=portfolio_context,
        )

        if decisions:
            portfolio_state = await self.portfolio.get_state()
            for decision in decisions.values():
                await self._execute_decision(decision, market_data, portfolio_state)

        await self.portfolio.record_snapshot()

    async def _check_exits(self, positions: list[Any], market_data: dict[str, Any]) -> None:
        """Check if any positions should be closed and update current prices."""
        for position in positions:
            if position.symbol not in market_data:
                continue

            current_price = market_data[position.symbol].price
            await self._update_position_price(position, current_price)

            should_exit, reason = self.risk.check_exit_conditions(position, current_price)
            if should_exit:
                logger.info(f"Exit triggered for {position.symbol}: {reason}")
                await self.execution.close_position(position, current_price, reason)

    async def _update_position_price(self, position: Any, current_price: Decimal) -> None:
        """Update position with current market price."""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("UPDATE positions SET current_price = :price WHERE id = :id"),
                    {"price": float(current_price), "id": str(position.id)},
                )
                await db.commit()
        except Exception as e:
            logger.warning(f"Failed to update position: {e}")

    async def _execute_decision(self, decision: Any, market_data: dict[str, Any], portfolio_state: Any) -> None:
        """Validate and execute a single decision."""
        # Normalize decision format (handle both TradingSignal and legacy formats)
        signal_type = getattr(decision, 'signal_type', None)
        signal_str = str(signal_type) if signal_type else getattr(decision, 'signal', None)

        if signal_str == "close" or signal_str == SignalType.CLOSE.value:
            await self._handle_close_signal(decision, market_data, portfolio_state)
            return

        if signal_str not in ["buy_to_enter", SignalType.BUY_TO_ENTER.value, "sell_to_enter", SignalType.SELL_TO_ENTER.value]:
            return

        if self._has_position(decision.symbol, portfolio_state.open_positions):
            return

        if decision.symbol not in market_data:
            return

        current_price = market_data[decision.symbol].price

        # Normalize side (handle both enum and string)
        side = str(decision.side) if hasattr(decision.side, 'value') else decision.side

        # Keep as Decimal for validation, convert to float later for execution
        stop_loss = decision.stop_loss if decision.stop_loss else Decimal("0")
        take_profit = decision.take_profit if decision.take_profit else Decimal("0")

        # Ensure they are Decimal
        if not isinstance(stop_loss, Decimal):
            stop_loss = Decimal(str(stop_loss)) if stop_loss else Decimal("0")
        if not isinstance(take_profit, Decimal):
            take_profit = Decimal(str(take_profit)) if take_profit else Decimal("0")

        validation = self.risk.validate_entry(
            symbol=decision.symbol,
            side=side,
            size_pct=decision.size_pct,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            capital=portfolio_state.equity,
            current_positions=portfolio_state.open_positions,
        )

        if not validation.is_valid:
            logger.info(f"{decision.symbol}: {validation.reason}")
            return

        result = await self.execution.open_position(
            symbol=decision.symbol,
            side=side,
            size_pct=decision.size_pct,
            entry_price=current_price,
            stop_loss=stop_loss if stop_loss and stop_loss > 0 else Decimal("0"),
            take_profit=take_profit if take_profit and take_profit > 0 else Decimal("0"),
            leverage=getattr(decision, 'leverage', 1),
        )

        if result.success and result.position:
            logger.info(f"{side.upper()} {decision.symbol} @ ${current_price:,.2f}")
            sl_float = float(stop_loss) if stop_loss else 0
            tp_float = float(take_profit) if take_profit else 0
            ActivityLogger.log_trade_entry(
                bot_name="0xBot",
                symbol=decision.symbol,
                side=side,
                quantity=float(result.position.quantity),
                entry_price=float(current_price),
                stop_loss=sl_float,
                take_profit=tp_float,
                confidence=decision.confidence,
            )
        else:
            logger.error(f"{decision.symbol}: {result.error}")

    async def _handle_close_signal(self, decision: Any, market_data: dict[str, Any], portfolio_state: Any) -> None:
        """Handle LLM close signal for a position."""
        position = self._find_position(decision.symbol, portfolio_state.open_positions)
        if not position:
            return

        price_data = market_data.get(decision.symbol)
        if not price_data:
            return

        logger.info(f"LLM EXIT {decision.symbol}: {decision.reasoning[:50]}...")
        await self.execution.close_position(position, price_data.price, "llm_decision")

    def _has_position(self, symbol: str, positions: list[Any]) -> bool:
        """Check if there's an open position for the symbol."""
        return any(p.symbol == symbol for p in positions)

    def _find_position(self, symbol: str, positions: list[Any]) -> Any:
        """Find open position for symbol."""
        return next((p for p in positions if p.symbol == symbol), None)

    def switch_decision_mode(self, mode: str) -> bool:
        """Switch between decision modes (indicator, trinity, or llm).

        Args:
            mode: "indicator", "trinity", or "llm"

        Returns:
            True if switch successful, False otherwise
        """
        mode = mode.lower()

        if mode == "llm":
            if not self.llm_decision:
                logger.error("LLM decision block not available (no LLM client provided)")
                return False
            llm_dec = self.llm_decision
            self.decision = llm_dec
            self.decision_mode = "llm"
            logger.info("🧠 Switched to LLM-based decision mode")
            return True

        elif mode == "trinity":
            trinity_dec = self.trinity_decision
            self.decision = trinity_dec
            self.decision_mode = "trinity"
            logger.info("📈 Switched to Trinity indicator framework (confluence scoring)")
            return True

        elif mode == "indicator":
            indicator_dec = self.indicator_decision
            self.decision = indicator_dec
            self.decision_mode = "indicator"
            logger.info("📊 Switched to legacy indicator-based decision mode")
            return True

        else:
            logger.error(f"Unknown decision mode: {mode}. Use 'indicator', 'trinity', or 'llm'")
            return False

    def get_decision_mode(self) -> str:
        """Get current decision mode."""
        return self.decision_mode
