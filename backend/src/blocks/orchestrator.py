"""Trading Orchestrator - Coordinates all trading blocks.

This is the main entry point that:
1. Fetches market data
2. Gets portfolio state
3. Calls LLM for decisions
4. Validates against risk
5. Executes valid trades
6. Records equity snapshot
"""

import asyncio
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.activity_logger import ActivityLogger
from ..core.config import config
from ..core.database import AsyncSessionLocal
from ..core.llm_client import LLMClient
from ..core.logger import get_logger
from ..models.bot import Bot, BotStatus
from .block_execution import ExecutionBlock
from .block_llm_decision import LLMDecisionBlock
from .block_market_data import MarketDataBlock
from .block_portfolio import PortfolioBlock
from .block_risk import RiskBlock

logger = get_logger(__name__)


class TradingOrchestrator:
    """Orchestrates the complete trading cycle using modular blocks."""

    def __init__(
        self,
        bot_id: uuid.UUID,
        cycle_interval: int = 180,  # 3 minutes
        llm_client: Optional[LLMClient] = None,
    ):
        self.bot_id = bot_id
        self.cycle_interval = cycle_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Initialize blocks
        self.market_data = MarketDataBlock()
        self.portfolio = PortfolioBlock(bot_id)
        self.llm = LLMDecisionBlock(llm_client)
        self.risk = RiskBlock()
        self.execution = ExecutionBlock(bot_id)

    async def start(self) -> None:
        """Start the trading loop."""
        self._running = True
        logger.info(f"Starting trading orchestrator (cycles every {self.cycle_interval}s)")

        while self._running:
            try:
                # Check if bot is still active
                if not await self._is_bot_active():
                    logger.warning("Bot is not active, stopping orchestrator")
                    break

                # Run one trading cycle
                cycle_start = datetime.utcnow()
                await self._run_cycle()
                cycle_time = (datetime.utcnow() - cycle_start).total_seconds()

                logger.info(f"✅ Cycle completed in {cycle_time:.1f}s")

                # Wait for next cycle
                sleep_time = max(0, self.cycle_interval - cycle_time)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                logger.info("Trading orchestrator cancelled")
                break
            except Exception as e:
                logger.error(f"Error in trading cycle: {e}")
                await asyncio.sleep(30)  # Wait before retry

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
            query = select(Bot).where(Bot.id == self.bot_id)
            result = await db.execute(query)
            bot = result.scalar_one_or_none()
            return bot and bot.status == BotStatus.ACTIVE.value

    async def _run_cycle(self) -> None:
        """Execute one complete trading cycle."""

        # Step 1: Fetch market data
        logger.info("📊 Step 1: Fetching market data...")
        market_data = await self.market_data.fetch_all()
        if not market_data:
            logger.warning("No market data available, skipping cycle")
            return

        # Step 2: Get portfolio state
        logger.info("📊 Step 2: Getting portfolio state...")
        portfolio_state = await self.portfolio.get_state()

        # Log portfolio
        logger.info(
            f"Portfolio: Cash ${float(portfolio_state.cash):,.2f} | "
            f"Equity ${float(portfolio_state.equity):,.2f} | "
            f"Positions: {len(portfolio_state.open_positions)}"
        )

        # Step 3: Check exit conditions for open positions
        logger.info("📊 Step 3: Checking exit conditions...")
        await self._check_exits(portfolio_state.open_positions, market_data)

        # Step 4: Get LLM decisions
        logger.info("📊 Step 4: Getting LLM decisions...")

        # Build portfolio context for LLM
        portfolio_context = {
            "cash": float(portfolio_state.cash),
            "equity": float(portfolio_state.equity),
            "return_pct": portfolio_state.return_pct,
            "positions": [
                {
                    "symbol": p.symbol,
                    "side": p.side,
                    "entry_price": float(p.entry_price),
                    "unrealized_pnl": float(p.unrealized_pnl),
                }
                for p in portfolio_state.open_positions
            ],
        }

        decisions = await self.llm.get_decisions(
            market_data=market_data,
            portfolio_context=portfolio_context,
        )

        if not decisions:
            logger.info("No actionable decisions from LLM")

        # Step 5: Validate and execute decisions
        logger.info(f"📊 Step 5: Executing {len(decisions)} decisions...")

        # Refresh portfolio for validation
        portfolio_state = await self.portfolio.get_state()

        for symbol, decision in decisions.items():
            await self._execute_decision(
                decision=decision,
                market_data=market_data,
                portfolio_state=portfolio_state,
            )

        # Step 6: Record equity snapshot
        await self.portfolio.record_snapshot()

    async def _check_exits(self, positions: list, market_data: dict) -> None:
        """Check if any positions should be closed."""
        for position in positions:
            if position.symbol not in market_data:
                continue

            current_price = market_data[position.symbol].price
            should_exit, reason = self.risk.check_exit_conditions(position, current_price)

            if should_exit:
                logger.info(f"⚡ Exit triggered for {position.symbol}: {reason}")
                await self.execution.close_position(
                    position=position,
                    current_price=current_price,
                    reason=reason,
                )

    async def _execute_decision(
        self,
        decision,
        market_data: dict,
        portfolio_state,
    ) -> None:
        """Validate and execute a single decision."""

        # Only process entry signals
        if decision.signal not in ["buy_to_enter", "sell_to_enter"]:
            return

        # Check if already have position
        symbol_positions = [
            p for p in portfolio_state.open_positions if p.symbol == decision.symbol
        ]
        if symbol_positions:
            logger.info(f"   {decision.symbol}: Already have position, skipping")
            return

        # Get current price
        if decision.symbol not in market_data:
            return
        current_price = market_data[decision.symbol].price

        # Validate with risk block
        # Use equity (not cash) as capital base for max exposure calc
        validation = self.risk.validate_entry(
            symbol=decision.symbol,
            side=decision.side,
            size_pct=decision.size_pct,
            entry_price=current_price,
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit,
            capital=portfolio_state.equity,  # Use equity for max_margin calc
            current_positions=portfolio_state.open_positions,
        )

        if not validation:
            logger.info(f"   ❌ {decision.symbol}: {validation.reason}")
            return

        # Execute trade
        result = await self.execution.open_position(
            symbol=decision.symbol,
            side=decision.side,
            size_pct=decision.size_pct,
            entry_price=current_price,
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit,
            leverage=decision.leverage,
        )

        if result.success:
            logger.info(f"✅ {decision.side.upper()} {decision.symbol} @ ${current_price:,.2f}")

            # Log to activity
            ActivityLogger.log_trade_entry(
                bot_name="0xBot",
                symbol=decision.symbol,
                side=decision.side,
                quantity=float(result.position.quantity),
                entry_price=float(current_price),
                stop_loss=float(decision.stop_loss),
                take_profit=float(decision.take_profit),
                confidence=decision.confidence,
            )
        else:
            logger.error(f"❌ {decision.symbol}: {result.error}")
