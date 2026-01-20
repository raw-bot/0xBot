"""Trading cycle manager - orchestrates complete trading cycle."""

import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import config
from ...core.llm_client import LLMClient
from ...core.logger import get_logger
from ...models.bot import Bot
from ...models.equity_snapshot import EquitySnapshot
from ...models.trade import Trade
from ..market_data_service import MarketDataService
from ..market_sentiment_service import MarketSentimentService
from ..multi_coin_prompt.service import MultiCoinPromptService
from ..news_service import NewsService
from ..position_service import PositionService
from ..trading_memory_service import TradingMemoryService
from sqlalchemy import select
from ...core.database import AsyncSessionLocal
from ...core.activity_logger import ActivityLogger

FORCED_MODEL_DEEPSEEK = os.getenv("FORCE_DEEPSEEK_MODEL", "deepseek-chat")

logger = get_logger(__name__)


class TradingCycleManager:
    """Orchestrates the complete trading cycle for a bot."""

    def __init__(
        self,
        bot: Bot,
        db: AsyncSession,
        llm_client: LLMClient,
        sentiment_service: MarketSentimentService,
        market_data_service: MarketDataService,
        prompt_service: MultiCoinPromptService,
        trading_memory: TradingMemoryService,
    ):
        self.bot_id = bot.id
        self.bot = bot
        self.db = db
        self.cycle_count = 0

        self.market_data_service = market_data_service
        self.position_service = PositionService(db)
        self.llm_client = llm_client
        self.sentiment_service = sentiment_service
        self.prompt_service = prompt_service
        self.news_service = NewsService()
        self.trading_memory = trading_memory

        self.trading_symbols = bot.trading_symbols
        self.timeframe = "5m"
        self.timeframe_long = "1h"

    async def execute_cycle(self) -> Tuple[Any, Any, Any]:
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
                return None, None, None

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
                return None, None, None

            all_symbols = list(all_coins_data.keys())
            decisions = self.prompt_service.parse_multi_coin_response(response_text, all_symbols)

            cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
            logger.info(f"Cycle completed in {cycle_duration:.1f}s")

            ActivityLogger.log_cycle_end(
                bot_name=self.bot.name,
                duration_seconds=cycle_duration,
                decisions=decisions,
            )

            await self._record_equity_snapshot()
            await self._log_performance_metrics()

            # Return decisions for execution by DecisionExecutor
            return decisions, all_coins_data, all_positions

        except Exception as e:
            logger.error(f"Cycle error: {e}", exc_info=True)
            return None, None, None

    async def _fetch_sentiment_data(self) -> Any:
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
        from pathlib import Path

        log_file = Path(__file__).parent.parent.parent.parent / "llm_decisions.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        separator = "=" * 80

        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"\n{separator}\nTIMESTAMP: {timestamp}\n{separator}\n\n")
                f.write(f"PROMPT:\n{'-' * 40}\n{prompt}\n\n")
                f.write(f"RESPONSE:\n{'-' * 40}\n{response}\n\n{separator}\n")
        except Exception as e:
            logger.debug(f"Could not write to LLM log: {e}")

    async def _get_portfolio_state(self) -> Tuple[Dict[str, Any], Bot]:
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

    async def _get_all_coins_quick_snapshot(self) -> Dict[str, Any]:
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
