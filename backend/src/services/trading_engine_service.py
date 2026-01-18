"""Trading engine service - orchestrates the complete trading cycle."""

import asyncio
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.activity_logger import ActivityLogger
from ..core.config import config
from ..core.database import AsyncSessionLocal
from ..core.llm_client import LLMClient, get_llm_client
from ..core.logger import get_logger
from ..models.bot import Bot, BotStatus
from ..models.equity_snapshot import EquitySnapshot
from ..models.llm_decision import LLMDecision
from ..models.position import PositionStatus
from ..models.trade import Trade
from .indicator_service import IndicatorService
from .llm_decision_validator import LLMDecisionValidator
from .market_analysis_service import MarketAnalysisService
from .market_data_service import MarketDataService
from .market_sentiment_service import get_sentiment_service
from .news_service import NewsService
from .position_service import PositionService
from .risk_manager_service import RiskManagerService
from .trade_executor_service import TradeExecutorService
from .trading_memory_service import get_trading_memory

FORCED_MODEL_DEEPSEEK = os.getenv("FORCE_DEEPSEEK_MODEL", "deepseek-chat")

logger = get_logger(__name__)

GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"


class TradingEngine:
    """Trading engine that runs the complete trading cycle."""

    def __init__(
        self,
        bot: Bot,
        db: AsyncSession,
        cycle_interval: int = 300,
        llm_client: Optional[LLMClient] = None,
    ):
        self.bot_id = bot.id
        self.bot = bot
        self.db = db
        self.cycle_interval = cycle_interval
        self.is_running = False
        self.cycle_count = 0
        self.session_start = datetime.utcnow()

        self.market_data_service = MarketDataService()
        self.position_service = PositionService(db)
        self.trade_executor = TradeExecutorService(db)
        self.llm_client = llm_client or get_llm_client()
        self.sentiment_service = get_sentiment_service()

        from .multi_coin_prompt_service import MultiCoinPromptService

        self.prompt_service = MultiCoinPromptService()
        self.news_service = NewsService()
        self.trading_memory = get_trading_memory(db, bot.id)

        self.trading_symbols = bot.trading_symbols
        self.timeframe = "5m"
        self.timeframe_long = "1h"

        logger.info(f"Trading engine initialized for bot {bot.id} ({bot.name})")
        logger.info(f"Trading symbols: {', '.join(self.trading_symbols)}")

    async def start(self) -> None:
        """Start the trading engine loop."""
        if self.is_running:
            logger.warning(f"Engine already running for bot {self.bot_id}")
            return

        self.is_running = True
        logger.info(f"Starting trading engine for bot {self.bot_id}")

        try:
            bot_status = await self._get_bot_status()
            while self.is_running and bot_status == BotStatus.ACTIVE:
                try:
                    await self._trading_cycle()
                except Exception as e:
                    logger.error(f"Error in trading cycle: {e}")
                await asyncio.sleep(self.cycle_interval)
                bot_status = await self._get_bot_status()
        finally:
            self.is_running = False
            logger.info(f"Trading engine stopped for bot {self.bot_id}")

    async def stop(self) -> None:
        """Stop the trading engine and close all positions."""
        logger.info(f"Stopping trading engine for bot {self.bot_id}")
        self.is_running = False

        positions = await self.position_service.get_open_positions(self.bot_id)
        for position in positions:
            try:
                ticker = await self.market_data_service.fetch_ticker(position.symbol)
                await self.trade_executor.execute_exit(
                    position=position, current_price=ticker.last, reason="engine_stopped"
                )
                logger.info(f"Closed position {position.id} on engine stop")
            except Exception as e:
                logger.error(f"Error closing position {position.id}: {e}")

        await self._update_bot_status(BotStatus.STOPPED)

    async def _get_bot_status(self) -> BotStatus:
        """Get the current bot status from database."""
        bot = await self._get_fresh_bot()
        return bot.status

    async def _get_fresh_bot(self) -> Bot:
        """Get fresh bot instance from database."""
        async with AsyncSessionLocal() as fresh_db:
            query = select(Bot).where(Bot.id == self.bot_id)
            result = await fresh_db.execute(query)
            return result.scalar_one()

    async def _update_bot_status(self, status: BotStatus) -> None:
        """Update bot status in database."""
        async with AsyncSessionLocal() as fresh_db:
            query = select(Bot).where(Bot.id == self.bot_id)
            result = await fresh_db.execute(query)
            bot = result.scalar_one()
            bot.status = status
            await fresh_db.commit()

    async def _trading_cycle(self) -> None:
        """Execute one complete trading cycle for all trading symbols."""
        cycle_start = datetime.utcnow()
        self.cycle_count += 1

        try:
            all_coins_data = await self._get_all_coins_quick_snapshot()
            all_positions = await self.position_service.get_open_positions(self.bot_id)

            all_positions_dict = [
                {
                    "symbol": p.symbol,
                    "entry_price": float(p.entry_price),
                    "size": float(p.quantity),
                    "pnl_pct": float(p.unrealized_pnl_pct),
                    "status": "OPEN",
                }
                for p in all_positions
            ]

            if not all_coins_data:
                logger.warning("No market data available")
                return

            portfolio_state, _ = await self._get_portfolio_state()
            news_data = await self.news_service.get_latest_news(self.trading_symbols)
            sentiment_data = await self._fetch_sentiment_data()

            prompt_data = self.prompt_service.get_multi_coin_decision(
                bot=self.bot,
                all_coins_data=all_coins_data,
                all_positions=all_positions_dict,
                news_data=news_data,
                portfolio_state=portfolio_state,
                sentiment_data=sentiment_data,
            )

            logger.info(f"Analyzing {len(all_coins_data)} coins...")

            llm_response = await self.llm_client.analyze_market(
                model=FORCED_MODEL_DEEPSEEK,
                prompt=prompt_data["prompt"],
                max_tokens=6000,
                temperature=0.7,
            )

            response_text = llm_response.get("response", "")
            self._log_llm_decision(prompt_data["prompt"], response_text)

            if not response_text:
                logger.error("Empty LLM response")
                return

            all_symbols = list(all_coins_data.keys())
            decisions = self.prompt_service.parse_multi_coin_response(response_text, all_symbols)

            logger.info(f"Executing decisions for {len(decisions)} symbols...")
            await self._execute_all_decisions(all_coins_data, decisions, all_positions)

            cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
            logger.info(f"Cycle completed in {cycle_duration:.1f}s")

            ActivityLogger.log_cycle_end(
                bot_name=self.bot.name,
                duration_seconds=cycle_duration,
                decisions=decisions,
            )

            await self._record_equity_snapshot()
            await self._log_performance_metrics()

        except Exception as e:
            logger.error(f"Cycle error: {e}", exc_info=True)

    async def _fetch_sentiment_data(self):
        """Fetch market sentiment data with error handling."""
        try:
            sentiment_data = await self.sentiment_service.get_market_sentiment()
            if sentiment_data:
                logger.info(
                    f"F&G: {sentiment_data.fear_greed.value} "
                    f"({sentiment_data.fear_greed.label}) | "
                    f"BTC Dom: {sentiment_data.global_market.btc_dominance:.1f}%"
                )
            return sentiment_data
        except Exception as e:
            logger.warning(f"Could not fetch sentiment: {e}")
            return None

    def _log_llm_decision(self, prompt: str, response: str) -> None:
        """Log LLM prompt and response to file for analysis."""
        log_file = Path(__file__).parent.parent.parent / "llm_decisions.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        separator = "=" * 80

        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"\n{separator}\nTIMESTAMP: {timestamp}\n{separator}\n\n")
                f.write(f"PROMPT:\n{'-' * 40}\n{prompt}\n\n")
                f.write(f"RESPONSE:\n{'-' * 40}\n{response}\n\n{separator}\n")
        except Exception as e:
            logger.debug(f"Could not write to LLM log: {e}")

    async def _execute_all_decisions(
        self,
        all_coins_data: Dict,
        decisions: Dict[str, Dict],
        current_positions: list,
    ) -> None:
        """Execute decisions for all coins."""
        position_symbols = {p.symbol for p in current_positions}

        signal_map = {
            "buy_to_enter": ("ENTRY", "long"),
            "sell_to_enter": ("ENTRY", "short"),
            "close": ("EXIT", None),
            "hold": ("HOLD", None),
        }

        for symbol, decision in decisions.items():
            try:
                raw_signal = decision.get("signal", "hold").lower()
                confidence = float(decision.get("confidence", 0.0))
                reasoning = decision.get("justification", decision.get("reasoning", ""))
                current_price = all_coins_data.get(symbol, {}).get("current_price", 0)

                logger.info(f"{YELLOW}{symbol}: {raw_signal} ({confidence:.0%}){RESET}")

                action, side = signal_map.get(raw_signal, ("HOLD", None))

                if symbol in position_symbols:
                    await self._handle_exit_if_needed(
                        symbol, action, confidence, current_positions, current_price
                    )
                elif action == "ENTRY" and confidence >= config.MIN_CONFIDENCE_ENTRY:
                    await self._handle_entry(
                        symbol, side, confidence, reasoning, decision, current_price, current_positions
                    )
            except Exception as e:
                logger.error(f"Error executing decision for {symbol}: {e}")

    async def _handle_exit_if_needed(
        self,
        symbol: str,
        action: str,
        confidence: float,
        current_positions: list,
        current_price: float,
    ) -> None:
        """Handle exit decision for existing position."""
        if action != "EXIT" or confidence < config.MIN_CONFIDENCE_EXIT_NORMAL:
            return

        position = next((p for p in current_positions if p.symbol == symbol), None)
        if not position:
            return

        pnl_pct = float(position.unrealized_pnl_pct)
        exit_type = "Protection" if pnl_pct < 0 else "LLM-triggered"
        logger.info(f"{symbol}: {exit_type} exit (PnL: {pnl_pct:+.2f}%)")

        await self.trade_executor.execute_exit(
            position=position,
            current_price=Decimal(str(current_price)),
            reason="llm_decision",
        )

    async def _handle_entry(
        self,
        symbol: str,
        side: str,
        confidence: float,
        reasoning: str,
        decision: dict,
        current_price: float,
        current_positions: list,
    ) -> None:
        """Handle entry decision for new position."""
        portfolio_state, current_bot = await self._get_portfolio_state()
        total_value = float(portfolio_state.get("total_value", 1))

        default_size = (
            config.SHORT_POSITION_SIZE_PCT if side == "short" else config.DEFAULT_POSITION_SIZE_PCT
        )
        size_pct = self._calculate_size_pct(decision, current_price, total_value, default_size)

        is_valid, reason, fixed_decision = LLMDecisionValidator.validate_and_fix_decision(
            decision=decision, current_price=current_price, symbol=symbol
        )

        if not is_valid and fixed_decision.get("signal", "").lower() == "hold":
            logger.warning(f"{symbol} Decision invalid: {reason}")
            return

        validated_sl = float(fixed_decision.get("stop_loss", current_price * 0.965))
        validated_tp = float(
            fixed_decision.get("take_profit", decision.get("profit_target", current_price * 1.07))
        )
        validated_entry = float(fixed_decision.get("entry_price", current_price))

        requested_leverage = int(decision.get("leverage", 1))
        final_size_pct = size_pct

        if side == "short":
            requested_leverage = min(requested_leverage, int(config.SHORT_MAX_LEVERAGE))
            final_size_pct = min(size_pct, config.SHORT_POSITION_SIZE_PCT)
            logger.info(f"SHORT limits: lev={requested_leverage}x, size={final_size_pct:.1%}")

        entry_decision = {
            "symbol": symbol,
            "action": "ENTRY",
            "side": side,
            "confidence": confidence,
            "reasoning": reasoning,
            "entry_price": validated_entry,
            "stop_loss": validated_sl,
            "take_profit": validated_tp,
            "size_pct": final_size_pct,
            "leverage": requested_leverage,
        }

        is_valid, reason = RiskManagerService.validate_entry(
            bot=current_bot,
            decision=entry_decision,
            current_positions=current_positions,
            current_price=Decimal(str(current_price)),
        )

        if not is_valid:
            logger.warning(f"Trade REJECTED by Risk Manager: {reason}")
            ActivityLogger.log_trade_rejected(
                bot_name=current_bot.name,
                symbol=symbol,
                signal=decision.get("signal", ""),
                confidence=confidence,
                reason=reason,
            )
            return

        await self._handle_entry_decision(
            entry_decision, Decimal(str(current_price)), portfolio_state, current_bot
        )

    def _calculate_size_pct(
        self, decision: dict, current_price: float, total_value: float, default_size: float
    ) -> float:
        """Calculate position size percentage from LLM quantity or use default."""
        quantity = float(decision.get("quantity", 0))
        if quantity > 0 and current_price > 0 and total_value > 0:
            calculated_size = (quantity * current_price) / total_value
            if 0.05 <= calculated_size <= default_size:
                return calculated_size
        return default_size

    async def _get_portfolio_state(self) -> tuple[dict, Bot]:
        """Get current portfolio state and bot."""
        async with AsyncSessionLocal() as fresh_db:
            query = select(Bot).where(Bot.id == self.bot_id)
            result = await fresh_db.execute(query)
            bot = result.scalar_one()

            temp_position_service = PositionService(fresh_db)
            positions = await temp_position_service.get_open_positions(self.bot_id)

            leverage = Decimal(str(config.DEFAULT_LEVERAGE))
            invested_in_positions = sum((p.entry_value / leverage for p in positions), Decimal("0"))
            unrealized_pnl = sum((p.unrealized_pnl for p in positions), Decimal("0"))
            total_value = bot.capital + invested_in_positions + unrealized_pnl

            return {
                "total_value": total_value,
                "cash": bot.capital,
                "invested": invested_in_positions,
                "total_pnl": total_value - bot.initial_capital,
                "unrealized_pnl": unrealized_pnl,
            }, bot

    async def _check_position_exits(self, positions: list) -> None:
        """Check if any positions should be closed due to stop loss or take profit."""
        if not positions:
            return

        logger.info(f"Checking exit conditions for {len(positions)} position(s)")

        for position in positions:
            if position.status != PositionStatus.OPEN:
                continue

            try:
                ticker = await self.market_data_service.fetch_ticker(position.symbol)
                current_price = ticker.last
                hold_hours = (datetime.utcnow() - position.opened_at).total_seconds() / 3600

                logger.info(
                    f"[{position.symbol}] Hold: {hold_hours:.1f}h | PnL: {position.unrealized_pnl_pct:+.2f}%"
                )

                exit_reason = await self.position_service.check_stop_loss_take_profit(
                    position, current_price
                )

                if exit_reason:
                    logger.info(f"{position.symbol} closing: {exit_reason.upper()}")
                    await self.trade_executor.execute_exit(
                        position=position, current_price=current_price, reason=exit_reason
                    )
            except Exception as e:
                logger.error(f"Error checking {position.symbol}: {e}")

    async def _save_llm_decision(
        self, prompt: str, llm_result: dict, symbol: str = None
    ) -> LLMDecision:
        """Save LLM decision to database."""
        parsed_decisions = llm_result["parsed_decisions"].copy()
        if symbol and "symbol" not in parsed_decisions:
            parsed_decisions["symbol"] = symbol

        async with AsyncSessionLocal() as fresh_db:
            decision = LLMDecision(
                bot_id=self.bot_id,
                prompt=prompt,
                response=llm_result["response"],
                parsed_decisions=parsed_decisions,
                tokens_used=llm_result["tokens_used"],
                cost=Decimal(str(llm_result["cost"])),
                timestamp=datetime.utcnow(),
            )
            fresh_db.add(decision)
            await fresh_db.commit()
            await fresh_db.refresh(decision)
            return decision

    async def _handle_entry_decision(
        self, decision: dict, current_price: Decimal, portfolio_state: dict, current_bot: Bot
    ) -> None:
        """Handle entry decision from LLM."""
        symbol = decision.get("symbol", "UNKNOWN")
        position, trade = await self.trade_executor.execute_entry(
            bot=current_bot, decision=decision, current_price=current_price
        )

        if position and trade:
            logger.info(
                f"{GREEN}BUY {position.quantity:.4f} {position.symbol.split('/')[0]} "
                f"@ ${position.entry_price:,.2f}{RESET}"
            )
            ActivityLogger.log_trade_entry(
                bot_name=current_bot.name,
                symbol=position.symbol,
                side=position.side,
                quantity=float(position.quantity),
                entry_price=float(position.entry_price),
                stop_loss=float(position.stop_loss),
                take_profit=float(position.take_profit),
                confidence=float(decision.get("confidence", 0)),
            )
        else:
            logger.error(f"{symbol} Trade execution failed")

    async def _handle_close_all_positions(self, positions: list, current_price: Decimal) -> None:
        """Handle emergency close of all positions."""
        logger.warning("Processing emergency close...")
        for position in positions:
            await self.trade_executor.execute_exit(
                position=position, current_price=current_price, reason="emergency_close"
            )
            logger.info(f"EMERGENCY CLOSE {position.symbol.split('/')[0]} @ ${current_price:,.2f}")

    async def _get_all_coins_quick_snapshot(self) -> dict:
        """Get complete snapshot of all tradable coins with technical indicators."""
        all_coins = {}
        for symbol in self.trading_symbols:
            try:
                snapshot = await self.market_data_service.get_market_data_multi_timeframe(
                    symbol=symbol,
                    timeframe_short=self.timeframe,
                    timeframe_long=self.timeframe_long,
                )
                if snapshot:
                    all_coins[symbol] = snapshot
            except Exception:
                continue
        return all_coins

    async def _record_equity_snapshot(self) -> None:
        """Record current equity for dashboard chart."""
        try:
            async with AsyncSessionLocal() as fresh_db:
                query = select(Bot).where(Bot.id == self.bot_id)
                result = await fresh_db.execute(query)
                bot = result.scalar_one()
                cash = Decimal(str(bot.capital))

                temp_position_service = PositionService(fresh_db)
                positions = await temp_position_service.get_open_positions(self.bot_id)
                unrealized_pnl = sum(
                    (Decimal(str(pos.unrealized_pnl)) for pos in positions), Decimal("0")
                )
                equity = cash + unrealized_pnl

                snapshot = EquitySnapshot(
                    bot_id=self.bot_id,
                    equity=equity,
                    cash=cash,
                    unrealized_pnl=unrealized_pnl,
                )
                fresh_db.add(snapshot)
                await fresh_db.commit()

                logger.info(
                    f"Equity: ${float(equity):,.2f} (cash: ${float(cash):,.2f}, "
                    f"unrealized: ${float(unrealized_pnl):,.2f})"
                )
        except Exception as e:
            logger.error(f"Error recording equity snapshot: {e}")

    async def _log_performance_metrics(self) -> None:
        """Log key performance metrics at end of each cycle."""
        try:
            async with AsyncSessionLocal() as db:
                query = select(Trade).where(
                    Trade.bot_id == self.bot_id, Trade.realized_pnl.isnot(None)
                )
                result = await db.execute(query)
                trades = list(result.scalars().all())

                if not trades:
                    return

                total_trades = len(trades)
                winning_trades = sum(1 for t in trades if float(t.realized_pnl) > 0)
                win_rate = (winning_trades / total_trades * 100) if total_trades else 0
                total_pnl = sum(float(t.realized_pnl) for t in trades)
                avg_pnl = total_pnl / total_trades if total_trades else 0
                total_fees = sum(float(t.fees or 0) for t in trades)

                logger.info(
                    f"METRICS | Trades: {total_trades} | Win: {win_rate:.0f}% | "
                    f"Avg PnL: ${avg_pnl:+.2f} | Total: ${total_pnl:+.2f} | Fees: ${total_fees:.2f}"
                )
        except Exception as e:
            logger.debug(f"Metrics calculation skipped: {e}")
