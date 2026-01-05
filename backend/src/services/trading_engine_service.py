"""
Fichier TradingEngine temporaire avec ancien système désactivé
Généré par le script de nettoyage automatique
"""

"""Trading engine service - orchestrates the complete trading cycle."""

import asyncio

# === PATCH DEEPSEEK - FORCER LE MODÈLE ===
import os
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.activity_logger import ActivityLogger
from ..core.config import config
from ..core.database import AsyncSessionLocal
from ..core.llm_client import LLMClient, get_llm_client
from ..core.logger import get_logger
from ..models.bot import Bot, BotStatus
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
# === FIN PATCH ===


logger = get_logger(__name__)

# ANSI color codes for terminal output
GREEN = "\033[92m"  # Bright green
YELLOW = "\033[93m"  # Bright yellow (orange-ish)
CYAN = "\033[96m"  # Bright cyan
RED = "\033[91m"  # Bright red
RESET = "\033[0m"  # Reset color


class TradingEngine:
    """
    Trading engine that runs the complete trading cycle.

    Executes every 3 minutes (configurable) and performs:
    1. Fetch market data
    2. Calculate indicators
    3. Get portfolio state
    4. Build LLM prompt
    5. Get LLM decision
    6. Validate with risk manager
    7. Execute trades
    8. Update positions
    9. Log everything
    """

    def __init__(
        self,
        bot: Bot,
        db: AsyncSession,
        cycle_interval: int = 300,  # 5 minutes in seconds (ALIGNED with timeframe)
        llm_client: Optional[LLMClient] = None,
    ):
        """
        Initialize trading engine.

        Args:
            bot: Bot instance to manage
            db: Database session
            cycle_interval: Time between trading cycles in seconds (default: 300 = 5min)
            llm_client: Optional LLM client instance
        """
        self.bot_id = bot.id  # Store bot ID instead of instance
        self.bot = bot
        self.db = db
        self.cycle_interval = cycle_interval
        self.is_running = False

        # Performance tracking
        self.cycle_count = 0  # Track number of cycles for hourly summaries
        self.session_start = datetime.utcnow()

        # Initialize services
        self.market_data_service = MarketDataService()
        self.position_service = PositionService(db)
        self.trade_executor = TradeExecutorService(db)
        self.llm_client = llm_client or get_llm_client()
        self.sentiment_service = get_sentiment_service()

        # Initialize multi-coin prompt service
        try:
            from .multi_coin_prompt_service import MultiCoinPromptService

            self.prompt_service = MultiCoinPromptService()
            self.news_service = NewsService()
        except ImportError as e:
            logger.error(f"MultiCoinPromptService not available: {e}")
            raise
        self.trading_memory = get_trading_memory(db, bot.id)

        # Trading parameters - ALIGNED timeframe with cycle
        self.trading_symbols = bot.trading_symbols  # List of trading pairs
        self.timeframe = "5m"  # Changed from "1h" to "5m" to align with 5min cycle
        self.timeframe_long = "1h"  # Keep 1h for longer-term context

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
            # Reload bot to check status
            bot_status = await self._get_bot_status()

            while self.is_running and bot_status == BotStatus.ACTIVE:
                try:
                    # Execute trading cycle
                    await self._trading_cycle()

                    # Wait for next cycle
                    await asyncio.sleep(self.cycle_interval)

                    # Reload bot status from database for next iteration
                    bot_status = await self._get_bot_status()

                except Exception as e:
                    logger.error(f"Error in trading cycle: {e}")
                    # Continue running despite errors
                    await asyncio.sleep(self.cycle_interval)
                    # Reload status even after error
                    bot_status = await self._get_bot_status()

        finally:
            self.is_running = False
            logger.info(f"Trading engine stopped for bot {self.bot_id}")

    async def stop(self) -> None:
        """Stop the trading engine and close all positions."""
        logger.info(f"Stopping trading engine for bot {self.bot_id}")
        self.is_running = False

        # Close all open positions
        positions = await self.position_service.get_open_positions(self.bot_id)

        for position in positions:
            try:
                # Get current price
                ticker = await self.market_data_service.fetch_ticker(position.symbol)
                current_price = ticker.last

                # Execute exit
                await self.trade_executor.execute_exit(
                    position=position, current_price=current_price, reason="engine_stopped"
                )

                logger.info(f"Closed position {position.id} on engine stop")

            except Exception as e:
                logger.error(f"Error closing position {position.id}: {e}")

        # Update bot status using fresh session
        async with AsyncSessionLocal() as fresh_db:
            query = select(Bot).where(Bot.id == self.bot_id)
            result = await fresh_db.execute(query)
            bot = result.scalar_one()
            bot.status = BotStatus.STOPPED
            await fresh_db.commit()

    async def _get_bot_status(self) -> BotStatus:
        """Get the current bot status from database."""
        async with AsyncSessionLocal() as fresh_db:
            query = select(Bot).where(Bot.id == self.bot_id)
            result = await fresh_db.execute(query)
            bot = result.scalar_one()
            return bot.status

    async def _trading_cycle(self) -> None:
        """Execute one complete trading cycle for all trading symbols using optimized Multi-Coin analysis."""
        cycle_start = datetime.utcnow()
        self.cycle_count += 1

        try:
            # 1. Get all market data and positions efficiently
            all_coins_data = await self._get_all_coins_quick_snapshot()
            all_positions = await self.position_service.get_open_positions(self.bot_id)

            # Convert positions to dict format for prompt service
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
                logger.warning("⚠️  No market data available")
                return

            # 2. Generate Enhanced NoF1-Style Prompt
            # Includes: Raw Data, Narrative Analysis, Pain Trade, Alpha Setups
            portfolio_state_tuple = await self._get_portfolio_state()
            portfolio_state = portfolio_state_tuple[0] if portfolio_state_tuple else {}

            # Fetch News for Narrative Analysis
            news_data = await self.news_service.get_latest_news(self.trading_symbols)

            # Fetch Market Sentiment (Fear & Greed, Global Data)
            sentiment_data = None
            try:
                sentiment_data = await self.sentiment_service.get_market_sentiment()
                if sentiment_data:
                    logger.info(
                        f"📊 F&G: {sentiment_data.fear_greed.value} "
                        f"({sentiment_data.fear_greed.label}) | "
                        f"BTC Dom: {sentiment_data.global_market.btc_dominance:.1f}%"
                    )
            except Exception as e:
                logger.warning(f"Could not fetch sentiment: {e}")

            # Generate comprehensive prompt with all analysis
            prompt_data = self.prompt_service.get_multi_coin_decision(
                bot=self.bot,
                all_coins_data=all_coins_data,
                all_positions=all_positions_dict,
                news_data=news_data,
                portfolio_state=portfolio_state,
                sentiment_data=sentiment_data,
            )

            logger.info(
                f"📊 Step 1: Analyzing {len(all_coins_data)} coins with NoF1-style prompt..."
            )

            # 3. Call LLM ONCE for all coins (increased tokens for comprehensive response)
            llm_response = await self.llm_client.analyze_market(
                model=FORCED_MODEL_DEEPSEEK,
                prompt=prompt_data["prompt"],
                max_tokens=6000,  # Increased for NoF1-style Chain of Thought responses
                temperature=0.7,
            )

            response_text = llm_response.get("response", "")

            # Log detailed LLM interaction for analysis
            self._log_llm_decision(prompt_data["prompt"], response_text)

            if not response_text:
                logger.error("🤖 Empty LLM response")
                return

            # 4. Parse response for ALL coins
            all_symbols = list(all_coins_data.keys())
            decisions = self.prompt_service.parse_multi_coin_response(response_text, all_symbols)

            logger.info(f"📈 Step 2: Executing decisions for {len(decisions)} symbols...")

            # 5. Execute decisions
            await self._execute_all_decisions(all_coins_data, decisions, all_positions)

            # Log cycle completion
            cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
            logger.info(f"✅ Cycle completed in {cycle_duration:.1f}s")

            # Log to JSON activity file
            ActivityLogger.log_cycle_end(
                bot_name=self.bot.name,
                duration_seconds=cycle_duration,
                decisions=decisions,
            )

            # Record equity snapshot every cycle (5 min) to populate chart
            # Previously was % 10 (50 min) which was too slow
            if self.cycle_count == 1 or self.cycle_count % 1 == 0:
                await self._record_equity_snapshot()

        except Exception as e:
            logger.error(f"❌ Cycle error: {e}", exc_info=True)

    def _log_llm_decision(self, prompt: str, response: str) -> None:
        """Log detailed LLM prompt and response to dedicated file for analysis."""
        import os

        log_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        log_file = os.path.join(log_dir, "llm_decisions.log")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        separator = "=" * 80

        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"\n{separator}\n")
                f.write(f"TIMESTAMP: {timestamp}\n")
                f.write(f"{separator}\n\n")
                f.write("📝 PROMPT SENT TO LLM:\n")
                f.write("-" * 40 + "\n")
                f.write(prompt + "\n\n")
                f.write("🤖 LLM RESPONSE:\n")
                f.write("-" * 40 + "\n")
                f.write(response + "\n")
                f.write(f"\n{separator}\n")
        except Exception as e:
            logger.debug(f"Could not write to LLM log: {e}")

    async def _execute_all_decisions(
        self,
        all_coins_data: Dict,
        decisions: Dict[str, Dict],
        current_positions: list,
    ):
        """Execute decisions for all coins."""
        position_symbols = {p.symbol for p in current_positions}

        for symbol, decision in decisions.items():
            try:
                # Monk Mode fields
                raw_signal = decision.get("signal", "hold").lower()
                confidence = float(decision.get("confidence", 0.0))
                reasoning = decision.get("justification", decision.get("reasoning", "No reasoning"))

                market_data = all_coins_data.get(symbol, {})
                current_price = market_data.get("current_price", 0)

                logger.info(f"{YELLOW}🧠 {symbol}: {raw_signal} ({confidence:.0%}){RESET}")

                # Map signals to Action/Side
                action = "HOLD"
                side = None
                if raw_signal == "buy_to_enter":
                    action = "ENTRY"
                    side = "long"  # lowercase to match position_service
                elif raw_signal == "sell_to_enter":
                    action = "ENTRY"
                    side = "short"  # lowercase to match position_service
                elif raw_signal == "close":
                    action = "EXIT"
                elif raw_signal == "hold":
                    action = "HOLD"

                if symbol in position_symbols:
                    # Handle EXIT or HOLD
                    if action == "EXIT" and confidence >= config.MIN_CONFIDENCE_EXIT_NORMAL:
                        # Find the position object
                        position = next((p for p in current_positions if p.symbol == symbol), None)
                        if position:
                            # Smart Exit Protection:
                            # - ALWAYS allow exit if losing (protection mode)
                            # - Only allow profit-taking if profit >= MIN_PNL_PCT_FOR_PROFIT_EXIT
                            pnl_pct = float(position.unrealized_pnl_pct)

                            # Allow exit if: losing OR significant profit
                            if pnl_pct < 0:
                                # Protection mode - exit to limit losses
                                logger.info(f"🛡️ {symbol}: Protection exit (PnL: {pnl_pct:+.2f}%)")
                            elif pnl_pct >= config.MIN_PNL_PCT_FOR_PROFIT_EXIT:
                                # Significant profit - allow exit
                                logger.info(f"💰 {symbol}: Profit exit (PnL: {pnl_pct:+.2f}%)")
                            else:
                                # Micro-profit - block exit, let it run
                                logger.info(
                                    f"⏳ {symbol}: Exit blocked - PnL {pnl_pct:+.2f}% < "
                                    f"{config.MIN_PNL_PCT_FOR_PROFIT_EXIT}% (let profit run)"
                                )
                                continue

                            await self.trade_executor.execute_exit(
                                position=position,
                                current_price=Decimal(str(current_price)),
                                reason="llm_decision",
                            )
                else:
                    # Handle ENTRY
                    if action == "ENTRY" and confidence >= config.MIN_CONFIDENCE_ENTRY:
                        # Get fresh portfolio state first to calculate size_pct if needed
                        portfolio_state, current_bot = await self._get_portfolio_state()
                        total_value = float(portfolio_state.get("total_value", 1))

                        # Calculate size_pct from quantity (Monk Mode provides quantity)
                        quantity = float(decision.get("quantity", 0))
                        size_pct = 0.05  # Default fallback

                        if quantity > 0 and current_price > 0 and total_value > 0:
                            notional = quantity * current_price
                            size_pct = notional / total_value
                            # Cap at reasonable max if calculation goes wild
                            if size_pct > 0.25:
                                size_pct = 0.25

                        # Validate and fix LLM decision BEFORE processing
                        is_valid, reason, fixed_decision = (
                            LLMDecisionValidator.validate_and_fix_decision(
                                decision=decision, current_price=current_price, symbol=symbol
                            )
                        )

                        if not is_valid and fixed_decision.get("signal", "").lower() == "hold":
                            logger.warning(f"⚠️ {symbol} Decision invalid and not fixable: {reason}")
                            continue

                        # Use fixed values (validator applies defaults if needed)
                        validated_sl = float(fixed_decision.get("stop_loss", current_price * 0.965))
                        validated_tp = float(
                            fixed_decision.get(
                                "take_profit", decision.get("profit_target", current_price * 1.07)
                            )
                        )
                        validated_entry = float(fixed_decision.get("entry_price", current_price))

                        # Apply SHORT-specific limits (safer due to risk)
                        requested_leverage = int(decision.get("leverage", 1))
                        final_size_pct = size_pct
                        if side == "short":
                            # Cap SHORT leverage at 3x
                            requested_leverage = min(
                                requested_leverage, int(config.SHORT_MAX_LEVERAGE)
                            )
                            # Cap SHORT position size at 15%
                            final_size_pct = min(size_pct, config.SHORT_POSITION_SIZE_PCT)
                            logger.info(
                                f"📉 SHORT limits: lev={requested_leverage}x, "
                                f"size={final_size_pct:.1%}"
                            )

                        # Prepare decision dict for entry handler
                        entry_decision = {
                            "symbol": symbol,
                            "action": "ENTRY",
                            "side": side,  # Critical: Added side
                            "confidence": confidence,
                            "reasoning": reasoning,
                            "entry_price": validated_entry,
                            "stop_loss": validated_sl,
                            "take_profit": validated_tp,
                            "size_pct": final_size_pct,
                            "leverage": requested_leverage,
                        }

                        # 🚨 CRITICAL FIX: Validate entry with RiskManager BEFORE execution
                        is_valid, reason = RiskManagerService.validate_entry(
                            bot=current_bot,
                            decision=entry_decision,
                            current_positions=current_positions,  # Fixed variable name
                            current_price=Decimal(str(current_price)),
                        )

                        if not is_valid:
                            logger.warning(f"⚠️  Trade REJECTED by Risk Manager: {reason}")
                            ActivityLogger.log_trade_rejected(
                                bot_name=current_bot.name,
                                symbol=symbol,
                                signal=raw_signal,
                                confidence=confidence,
                                reason=reason,
                            )
                            continue

                        await self._handle_entry_decision(
                            entry_decision,
                            Decimal(str(current_price)),
                            portfolio_state,
                            current_bot,
                        )
            except Exception as e:
                logger.error(f"Error executing decision for {symbol}: {e}")

    async def _fetch_market_data(self, symbol: str) -> dict:
        """Fetch current market data with multi-timeframe support for a specific symbol.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")

        Returns:
            Dictionary with snapshot (already enriched with 4h data)
        """
        logger.debug(f"Fetching multi-timeframe market data for {symbol}...")

        # Fetch multi-timeframe data (5min + 1h)
        # This returns an enriched snapshot with both timeframes combined
        snapshot = await self.market_data_service.get_market_data_multi_timeframe(
            symbol=symbol,
            timeframe_short=self.timeframe,  # Current timeframe (5min - ALIGNED with cycle)
            timeframe_long=self.timeframe_long,  # Long-term context (1h)
        )

        logger.debug(f"{symbol} current price: ${snapshot['current_price']}")

        # Return snapshot (which already contains both timeframes)
        return {"snapshot": snapshot, "indicators_4h": snapshot["technical_indicators"]["1h"]}

    async def _calculate_indicators(self, market_snapshot: dict) -> dict:
        """Calculate technical indicators."""
        logger.debug("Calculating technical indicators...")

        ohlcv = market_snapshot["ohlcv"]
        closes = self.market_data_service.extract_closes(ohlcv)
        highs = self.market_data_service.extract_highs(ohlcv)
        lows = self.market_data_service.extract_lows(ohlcv)

        indicators = IndicatorService.calculate_all_indicators(closes, highs, lows)

        return indicators

    async def _get_portfolio_state(self) -> tuple[dict, Bot]:
        """Get current portfolio state and bot. Capital now reflects actual available cash.

        Returns:
            Tuple of (portfolio_state dict, bot instance)
        """
        # Create a fresh session for this operation
        async with AsyncSessionLocal() as fresh_db:
            # Reload bot from database to get latest capital value
            query = select(Bot).where(Bot.id == self.bot_id)
            result = await fresh_db.execute(query)
            bot = result.scalar_one()

            # Create temporary position service with fresh session
            temp_position_service = PositionService(fresh_db)
            # Get open positions
            positions = await temp_position_service.get_open_positions(self.bot_id)

            # Calculate value locked in positions (Margin)
            # Invested = Entry Value / Leverage (Margin is based on cost basis)
            leverage = Decimal(str(config.DEFAULT_LEVERAGE))
            invested_in_positions = sum((p.entry_value / leverage for p in positions), Decimal("0"))

            # Get unrealized PnL from open positions
            unrealized_pnl = sum((p.unrealized_pnl for p in positions), Decimal("0"))

            # Total portfolio value = available cash + margin locked + unrealized PnL
            total_value = bot.capital + invested_in_positions + unrealized_pnl

            # Calculate total PnL from initial capital
            total_pnl = total_value - bot.initial_capital

            portfolio = {
                "total_value": total_value,
                "cash": bot.capital,  # Available cash
                "invested": invested_in_positions,  # Value in open positions
                "total_pnl": total_pnl,
                "unrealized_pnl": unrealized_pnl,
            }

            return portfolio, bot

    async def _check_position_exits(self, positions: list) -> None:
        """Check if any positions should be closed due to stop loss, take profit, or time-based exit."""

        if not positions:
            logger.debug("✓ No positions to check for exits")
            return

        logger.info(f"🔍 Checking exit conditions for {len(positions)} position(s):")

        for position in positions:
            if position.status != PositionStatus.OPEN:
                continue

            # CRITICAL FIX: Fetch current price for THIS position's symbol
            try:
                ticker = await self.market_data_service.fetch_ticker(position.symbol)
                current_price = ticker.last

                # Calculate metrics for logging
                position_age = datetime.utcnow() - position.opened_at
                hold_hours = position_age.total_seconds() / 3600
                pnl_pct = float(position.unrealized_pnl_pct)

                # Calculate distances to SL/TP
                sl_distance_pct = (
                    (float(position.stop_loss) - current_price) / current_price
                ) * 100
                tp_distance_pct = (
                    (float(position.take_profit) - current_price) / current_price
                ) * 100

                # ✅ MINIMAL ESSENTIAL LOGGING
                logger.info(f"")
                logger.info(
                    f"  [{position.symbol}] Hold: {hold_hours:.1f}h | PnL: {pnl_pct:+.2f}% | SL: {sl_distance_pct:+.1f}% | TP: {tp_distance_pct:+.1f}%"
                )

            except Exception as e:
                logger.error(f"Error fetching price for {position.symbol}: {e}")
                continue

            # Check stop loss / take profit
            exit_reason = await self.position_service.check_stop_loss_take_profit(
                position, current_price  # ✅ Prix correct maintenant !
            )

            if exit_reason:
                logger.info(f"    → 🚨 EXIT TRIGGERED: {exit_reason.upper()}")
                logger.info(f"")
                logger.info(
                    f"🚨 {position.symbol} Position {position.id} closing due to {exit_reason.upper()}"
                )
                logger.info(f"   Entry: ${position.entry_price:,.2f} → Exit: ${current_price:,.2f}")
                logger.info(f"   Hold time: {hold_hours:.1f}h | PnL: {pnl_pct:+.2f}%")

                await self.trade_executor.execute_exit(
                    position=position, current_price=current_price, reason=exit_reason
                )
                continue

            # Additional exit conditions for stuck positions
            if position_age.total_seconds() > config.MAX_POSITION_AGE_SECONDS:  # 2 hours
                if pnl_pct < -2.0:
                    logger.info(
                        f"    → ⏰ EXIT TRIGGERED: TIMEOUT_LOSS (2h+ with {pnl_pct:.2f}% loss)"
                    )
                    logger.warning(
                        f"⏰ {position.symbol} Position aged {hold_hours:.1f}h with {pnl_pct:.2f}% loss - force closing"
                    )
                    await self.trade_executor.execute_exit(
                        position=position,
                        current_price=current_price,
                        reason="time_based_loss_limit",
                    )
                    continue

                elif pnl_pct > 1.0:
                    logger.info(
                        f"    → ⏰ EXIT TRIGGERED: PROFIT_TAKING (2h+ with {pnl_pct:.2f}% profit)"
                    )
                    logger.info(
                        f"⏰ {position.symbol} Position aged {hold_hours:.1f}h with {pnl_pct:.2f}% profit - taking profit"
                    )
                    await self.trade_executor.execute_exit(
                        position=position,
                        current_price=current_price,
                        reason="time_based_profit_taking",
                    )
                    continue

            # No exit conditions met
            logger.info(f"    → ✓ HOLD (no exit conditions met)")

    async def _save_llm_decision(
        self, prompt: str, llm_result: dict, symbol: str = None
    ) -> LLMDecision:
        """Save LLM decision to database.

        Args:
            prompt: The prompt sent to LLM
            llm_result: The LLM response result
            symbol: Optional symbol this decision is for
        """
        # Add symbol to parsed decisions if provided
        parsed_decisions = llm_result["parsed_decisions"].copy()
        if symbol and "symbol" not in parsed_decisions:
            parsed_decisions["symbol"] = symbol

        # Create a fresh session for this operation
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
        # Extract symbol from decision
        symbol = decision.get("symbol", "UNKNOWN")

        # Get current positions and trades count
        positions = await self.position_service.get_open_positions(self.bot_id)
        trades_today = await self._get_trades_today_count()

        # Removed duplicate trade count logging (now in risk manager)

        # Execute entry directly (confidence filter already applied above)
        position, trade = await self.trade_executor.execute_entry(
            bot=current_bot, decision=decision, current_price=current_price
        )

        if position and trade:
            logger.info(
                f"{GREEN}✅ BUY {position.quantity:.4f} {position.symbol.split('/')[0]} @ ${position.entry_price:,.2f}{RESET}"
            )
            # Log to JSON
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
            logger.error(f"❌ {symbol} Trade execution failed")

    async def _handle_exit_decision(
        self, decision: dict, positions: list, current_price: Decimal
    ) -> None:
        """Handle exit decision from LLM."""
        logger.info("Processing exit decision...")

        # Find position to close (first open position for now)
        if not positions:
            # Extract symbol from decision or positions
            symbol = decision.get("symbol", "UNKNOWN")
            logger.warning(f"Exit requested for {symbol} but no open positions")
            return

        position = positions[0]  # Close first position

        await self.trade_executor.execute_exit(
            position=position, current_price=current_price, reason="llm_decision"
        )

        logger.info(f"✅ EXIT {position.symbol.split('/')[0]} @ ${current_price:,.2f}")

    async def _handle_close_position(
        self, decision: dict, positions: list, current_price: Decimal
    ) -> None:
        """Handle emergency close position."""
        logger.warning("Processing emergency close...")

        # Close all positions
        for position in positions:
            await self.trade_executor.execute_exit(
                position=position, current_price=current_price, reason="emergency_close"
            )
            logger.info(
                f"🚨 EMERGENCY CLOSE {position.symbol.split('/')[0]} @ ${current_price:,.2f}"
            )

    async def _update_position_prices(self) -> None:
        """Update current prices for all open positions."""
        positions = await self.position_service.get_open_positions(self.bot_id)

        for position in positions:
            try:
                current_price = await self.market_data_service.get_current_price(position.symbol)
                await self.position_service.update_current_price(position.id, current_price)
            except Exception as e:
                logger.error(f"Error updating price for position {position.id}: {e}")

    async def _get_trades_today_count(self) -> int:
        """
        Get number of ENTRY trades (position openings) executed today.

        Only counts ENTRY trades (position openings), not exits.
        This gives the true number of trading decisions made today.
        A HOLD decision creates no trade, so it's not counted.
        """
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # Create a fresh session for this operation
        async with AsyncSessionLocal() as fresh_db:
            # Only count entry trades (trades with realized_pnl = 0 are entries)
            query = select(Trade).where(
                Trade.bot_id == self.bot_id,
                Trade.executed_at >= today_start,
                Trade.realized_pnl == Decimal("0"),  # Entry trades have no PnL
            )

            result = await fresh_db.execute(query)
            trades = list(result.scalars().all())

            return len(trades)

    async def _get_multi_coin_market_context(self) -> dict:
        """
        Get comprehensive multi-coin market context.

        Collects data from all trading symbols and analyzes:
        - Correlations between assets
        - Market regime (risk-on/risk-off)
        - Market breadth
        - Capital flows
        - BTC dominance

        Returns:
            Dict with comprehensive market analysis
        """
        try:
            if len(self.trading_symbols) < 2:
                logger.debug("Need at least 2 symbols for multi-coin analysis")
                return {}

            # Collect data from all symbols
            multi_coin_data = {}

            for symbol in self.trading_symbols:
                try:
                    # Fetch recent OHLCV data (last 50 candles for correlation analysis)
                    ohlcv = await self.market_data_service.fetch_ohlcv(
                        symbol=symbol, timeframe=self.timeframe, limit=50
                    )

                    if not ohlcv or len(ohlcv) < 20:
                        logger.warning(f"Not enough data for {symbol}, skipping")
                        continue

                    # Extract prices (closing prices)
                    closes = self.market_data_service.extract_closes(ohlcv)

                    # Get current price and volume
                    current_price = closes[-1] if closes else 0
                    latest_candle = ohlcv[-1] if ohlcv else None
                    volume = (
                        float(latest_candle.volume) if latest_candle else 0
                    )  # Use OHLCV object attribute

                    # Calculate approximate market cap (price * volume as proxy)
                    # In real scenario, you'd fetch this from API
                    market_cap = float(current_price) * volume

                    multi_coin_data[symbol] = {
                        "prices": [float(p) for p in closes],
                        "volume": float(volume),
                        "market_cap": market_cap,
                        "current_price": float(current_price),
                    }

                except Exception as e:
                    logger.error(f"Error fetching data for {symbol}: {e}")
                    continue

            # If we have enough data, analyze
            if len(multi_coin_data) >= 2:
                context = MarketAnalysisService.get_comprehensive_market_context(multi_coin_data)
                logger.debug(f"Multi-coin context generated for {len(multi_coin_data)} symbols")
                return context
            else:
                logger.warning(
                    f"Not enough symbols with data ({len(multi_coin_data)}), skipping multi-coin analysis"
                )
                return {}

        except Exception as e:
            logger.error(f"Error getting multi-coin market context: {e}")
            return {}

    async def _get_all_coins_quick_snapshot(self) -> dict:
        """
        Obtenir un snapshot COMPLET de tous les coins tradables
        Avec TOUS les indicateurs techniques nécessaires
        Phase 3C - Expert Roadmap - FIXED
        """
        all_coins = {}
        for symbol in self.trading_symbols:
            try:
                # Fetch COMPLETE snapshot with all technical indicators
                snapshot = await self.market_data_service.get_market_data_multi_timeframe(
                    symbol=symbol,
                    timeframe_short=self.timeframe,
                    timeframe_long=self.timeframe_long,
                )

                if snapshot:
                    # Use the COMPLETE snapshot with all calculated indicators
                    all_coins[symbol] = snapshot
                    # Removed verbose logging for cleaner output

            except Exception as e:
                # Removed verbose warning for cleaner output
                continue
        return all_coins

    def _calculate_rsi(self, prices: list, period: int = 14) -> float:
        """
        Calculer le RSI (Relative Strength Index)
        Phase 3C - Expert Roadmap
        """
        if len(prices) < period + 1:
            return 50.0

        # Convert to float if needed
        prices = [float(p) for p in prices]

        # Calculate price changes
        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]

        # Separate gains and losses
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        # Calculate average gain and loss
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100.0

        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return round(rsi, 2)

    def _calculate_ema(self, prices: list, period: int) -> float:
        """
        Calculer l'EMA (Exponential Moving Average)
        Phase 3C - Expert Roadmap
        """
        if len(prices) < period:
            return sum([float(p) for p in prices]) / len(prices)

        # Convert to float (handles both Decimal and float)
        prices = [float(p) for p in prices]

        # Calculate multiplier
        multiplier = 2.0 / (period + 1)

        # Initialize with SMA
        ema = sum(prices[:period]) / period

        # Calculate EMA for remaining prices
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema

        return round(ema, 2)

    async def _record_equity_snapshot(self) -> None:
        """Record current equity for dashboard chart."""
        try:
            from decimal import Decimal

            from ..models.equity_snapshot import EquitySnapshot

            # Reload fresh bot capital from database
            async with AsyncSessionLocal() as fresh_db:
                query = select(Bot).where(Bot.id == self.bot_id)
                result = await fresh_db.execute(query)
                bot = result.scalar_one()
                cash = Decimal(str(bot.capital))

                # Get open positions and sum unrealized PnL
                temp_position_service = PositionService(fresh_db)
                positions = await temp_position_service.get_open_positions(self.bot_id)
                unrealized_pnl = Decimal("0")
                for pos in positions:
                    unrealized_pnl += Decimal(str(pos.unrealized_pnl))

                equity = cash + unrealized_pnl

                # Create snapshot
                snapshot = EquitySnapshot(
                    bot_id=self.bot_id,
                    equity=equity,
                    cash=cash,
                    unrealized_pnl=unrealized_pnl,
                )
                fresh_db.add(snapshot)
                await fresh_db.commit()

                logger.info(
                    f"📊 Equity snapshot: ${float(equity):,.2f} (cash: ${float(cash):,.2f}, unrealized: ${float(unrealized_pnl):,.2f})"
                )

        except Exception as e:
            logger.error(f"Error recording equity snapshot: {e}")


# 🚨 SÉCURITÉ: Ancien système désactivé par nettoyage automatique
# ⚠️ NE PAS RÉACTIVER sans validation complète du nouveau système
