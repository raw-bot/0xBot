"""Trading engine service - orchestrates the complete trading cycle."""

import asyncio
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logger import get_logger
from ..core.llm_client import LLMClient, get_llm_client
from ..core.database import AsyncSessionLocal
from ..models.bot import Bot, BotStatus
from ..models.llm_decision import LLMDecision
from ..models.position import PositionStatus
from ..models.trade import Trade
from .market_data_service import MarketDataService
from .indicator_service import IndicatorService
from .position_service import PositionService
from .llm_prompt_service import LLMPromptService
from .trade_executor_service import TradeExecutorService
from .risk_manager_service import RiskManagerService
from .market_analysis_service import MarketAnalysisService
from .enriched_llm_prompt_service import EnrichedLLMPromptService
from .trading_memory_service import get_trading_memory

logger = get_logger(__name__)

# ANSI color codes for terminal output
GREEN = '\033[92m'   # Bright green
YELLOW = '\033[93m'  # Bright yellow (orange-ish)
CYAN = '\033[96m'    # Bright cyan
RED = '\033[91m'     # Bright red
RESET = '\033[0m'    # Reset color


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
        llm_client: Optional[LLMClient] = None
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
        
        # Initialize enriched LLM services (Phase 3B - Expert Roadmap)
        self.enriched_prompt_service = EnrichedLLMPromptService(db)
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
                    position=position,
                    current_price=current_price,
                    reason="engine_stopped"
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
        """Execute one complete trading cycle for all trading symbols."""
        cycle_start = datetime.utcnow()

        try:
            # 0. Update position prices FIRST to get accurate equity
            await self._update_position_prices()

            # 0.1 MANAGE EXISTING POSITIONS FIRST (PRIORITY ABSOLUTE)
            logger.info(f"📍 Step 0.1: Managing existing positions...")
            positions_to_manage = await self.position_service.get_open_positions(self.bot_id)

            if positions_to_manage:
                logger.info(f"📍 Managing {len(positions_to_manage)} active position(s)")
                # Use the better method with 2h timeout conditions
                await self._check_position_exits(positions_to_manage)
                positions_closed_count = len(positions_to_manage) - len(await self.position_service.get_open_positions(self.bot_id))
            else:
                logger.debug("📍 No active positions to manage")
                positions_closed_count = 0

            # 1. Get portfolio state once (this will reload bot with latest capital)
            portfolio_state, current_bot = await self._get_portfolio_state()

            # Get all positions across all symbols
            all_positions = await self.position_service.get_open_positions(self.bot_id)

            # Calculate returns based on total equity (not just cash)
            equity = portfolio_state['total_value']
            return_pct = ((equity - current_bot.initial_capital) / current_bot.initial_capital) * 100

            # Log essential info only (no verbose portfolio details)
            logger.info(f"🤖 {current_bot.name} | {cycle_start.strftime('%H:%M:%S')} | Equity: ${equity:,.2f} ({return_pct:+.2f}%) | Positions: {len(all_positions)}")

            # 1.5 Fetch multi-coin context (correlations, regime, breadth, etc.)
            market_context = await self._get_multi_coin_market_context()

            # 2. Loop through each trading symbol (minimal logging)
            # CRITICAL FIX: Separate symbols with positions from symbols for new entries
            symbols_with_positions = list(set([p.symbol for p in all_positions]))
            symbols_for_new_entries = [s for s in self.trading_symbols if s not in symbols_with_positions]

            # Log analysis plan
            logger.info(f"📊 Step 1.5: Analyzing multi-coin market context...")
            if symbols_with_positions:
                logger.info(f"   Active positions: {', '.join(symbols_with_positions)}")
            if symbols_for_new_entries:
                logger.debug(f"   Scanning for entries: {', '.join(symbols_for_new_entries)}")

            logger.info(f"📈 Step 2: Analyzing individual symbols...")

            # Priority: Handle existing positions FIRST, then look for new entries
            for symbol in symbols_with_positions + symbols_for_new_entries:
                logger.info("─" * 80)

                # Flag if this symbol has an open position
                symbol_positions = [p for p in all_positions if p.symbol == symbol]
                has_position = len(symbol_positions) > 0

                if has_position:
                    logger.info(f"📈 Analyzing {symbol} (HAS POSITION)")
                else:
                    logger.debug(f"📈 Analyzing {symbol} (looking for entry)")

                try:
                    # Fetch market data for this symbol
                    market_data = await self._fetch_market_data(symbol)
                    market_snapshot = market_data['snapshot']
                    indicators_4h = market_data['indicators_4h']
                    
                    # Enrich market_snapshot with time series (Phase 3E - Expert Roadmap)
                    try:
                        candles_5m = await self.market_data_service.fetch_ohlcv(
                            symbol=symbol,
                            timeframe="5m",
                            limit=100
                        )
                        if len(candles_5m) >= 20:
                            closes = self.market_data_service.extract_closes(candles_5m)
                            
                            # Add price series (last 10 points)
                            market_snapshot["price_series"] = [float(c) for c in closes[-10:]]
                            
                            # Add EMA series (last 10 points)
                            ema_series = []
                            for i in range(len(closes) - 10, len(closes)):
                                ema = self._calculate_ema(closes[:i+1], 20)
                                ema_series.append(ema)
                            market_snapshot["ema_series"] = ema_series
                            
                            # Add RSI series (last 10 points)
                            rsi_series = []
                            for i in range(len(closes) - 10, len(closes)):
                                rsi = self._calculate_rsi(closes[:i+1], 7)
                                rsi_series.append(rsi)
                            market_snapshot["rsi_series"] = rsi_series
                    except Exception as e:
                        logger.warning(f"Could not enrich market_snapshot with series: {e}")
                    
                    # Calculate indicators
                    indicators = await self._calculate_indicators(market_snapshot)
                    latest_indicators = IndicatorService.get_latest_values(indicators)
                    
                    # Better RSI handling - calculate from more data if needed
                    rsi = latest_indicators.get('rsi_14')
                    if rsi is None or (isinstance(rsi, float) and rsi == 0):
                        # RSI needs at least 14 candles, log warning
                        logger.warning(f"⚠️ RSI not available for {symbol} (need at least 14 candles)")
                        rsi_str = "N/A (insufficient data)"
                    else:
                        rsi_str = f"{rsi:.1f}"
                    
                    # Minimal price logging for debugging
                    logger.debug(f"📊 {symbol}: ${market_snapshot['current_price']:,.2f} | RSI: {rsi_str}")
                    
                    # Get positions for this specific symbol
                    symbol_positions = [p for p in all_positions if p.symbol == symbol]
                    
                    # Check exits for positions of this symbol
                    await self._check_position_exits(symbol_positions)  # Plus besoin de passer le prix
                    
                    # Build enriched prompt with complete context (Phase 3D - Expert Roadmap)
                    # Get all coins snapshot for multi-coin context
                    all_coins_data = await self._get_all_coins_quick_snapshot()
                    
                    # Build enriched prompt (pass all_positions to avoid async DB queries)
                    prompt_data = self.enriched_prompt_service.get_simple_decision(
                        bot=current_bot,
                        symbol=symbol,
                        market_snapshot=market_snapshot,
                        market_regime=market_context,
                        all_coins_data=all_coins_data,
                        bot_positions=all_positions  # Pass positions to avoid async issues
                    )
                    
                    # Get LLM decision with enriched context
                    llm_response = await self.llm_client.analyze_market(
                        model=current_bot.model_name,
                        prompt=prompt_data["prompt"],
                        max_tokens=1024,
                        temperature=0.7
                    )
                    
                    # Get response text (LLM client returns "response" key, not "text")
                    response_text = llm_response.get("response", "")
                    
                    # Debug: log response preview if parsing fails
                    if not response_text:
                        logger.error(f"🤖 BOT | Empty response from LLM for {symbol}")
                        logger.error(f"🤖 BOT | LLM response keys: {list(llm_response.keys())}")
                    
                    # Parse (with prompt for logging and current_price for fallback)
                    parsed_decision = self.enriched_prompt_service.parse_llm_response(
                        response_text,
                        symbol,
                        original_prompt=prompt_data["prompt"],  # Pass prompt for logging
                        current_price=float(market_snapshot['current_price'])  # Pass price for fallback parser
                    )
                    
                    if not parsed_decision:
                        logger.warning(f"Failed to parse LLM decision for {symbol}, using fallback")
                        llm_decision = {"action": "hold", "confidence": 0.5, "reasoning": "Parse error"}
                    else:
                        # Get current price for default SL/TP calculation
                        current_price = market_snapshot.get("current_price", market_snapshot.get("price", 0))
                        
                        # Validate we have a valid price
                        if not current_price or current_price <= 0:
                            logger.error(f"❌ Invalid market price for {symbol}: {current_price}")
                            continue
                        
                        # Convert to Decimal for calculations
                        current_price_decimal = Decimal(str(current_price))
                        
                        # Get SL/TP from bot's risk_params with fallback values
                        stop_loss_pct = current_bot.risk_params.get("stop_loss_pct", 0.035)  # 3.5% default
                        take_profit_pct = current_bot.risk_params.get("take_profit_pct", 0.07)  # 7% default
                        
                        # Calculate default stop loss and take profit prices
                        default_sl = current_price_decimal * (Decimal("1") - Decimal(str(stop_loss_pct)))
                        default_tp = current_price_decimal * (Decimal("1") + Decimal(str(take_profit_pct)))
                        
                        # Parse avec fallback sur defaults - ensure all are Decimal for consistency
                        stop_loss = Decimal(str(parsed_decision.get("stop_loss"))) if parsed_decision.get("stop_loss") else default_sl
                        take_profit = Decimal(str(parsed_decision.get("profit_target"))) if parsed_decision.get("profit_target") else default_tp

                        # Ensure entry_price is provided (use current market price if LLM didn't provide it)
                        entry_price = parsed_decision.get("entry_price") or parsed_decision.get("price") or float(current_price_decimal)

                        logger.info(f"⚡ ENRICHED | Entry: ${entry_price:,.2f} | SL: ${float(stop_loss):,.2f} | TP: ${float(take_profit):,.2f} (market: ${float(current_price_decimal):,.2f})")

                        # Get size_pct from LLM or use default (5% of capital)
                        size_pct = parsed_decision.get("size_pct") or parsed_decision.get("risk_pct") or 0.05
                        
                        llm_decision = {
                            "action": parsed_decision["signal"],
                            "confidence": float(parsed_decision["confidence"]),
                            "reasoning": parsed_decision["justification"],
                            "entry_price": float(entry_price),
                            "stop_loss": float(stop_loss),
                            "take_profit": float(take_profit),
                            "side": parsed_decision.get("side", "long"),  # Default to long if not specified
                            "size_pct": float(size_pct)  # Position size as percentage
                        }
                    
                    # Save decision (using enriched prompt)
                    # Convert Decimal to float for JSON serialization
                    llm_decision_json = llm_decision.copy()
                    for key in ['entry_price', 'stop_loss', 'take_profit', 'size_pct']:
                        if key in llm_decision_json and isinstance(llm_decision_json[key], Decimal):
                            llm_decision_json[key] = float(llm_decision_json[key])
                    
                    llm_result = {
                        "response": response_text,
                        "parsed_decisions": llm_decision_json,
                        "tokens_used": llm_response.get("tokens_used", 0),
                        "cost": llm_response.get("cost", 0.0)
                    }
                    await self._save_llm_decision(prompt=prompt_data["prompt"], llm_result=llm_result, symbol=symbol)
                    
                    # Parse and display decision
                    action = llm_decision.get('action', 'hold').upper()
                    reasoning = llm_decision.get('reasoning', 'No reasoning provided')
                    confidence = llm_decision.get('confidence', 0)
                    
                    # Log decisions only when they change (ENTRY/EXIT), not HOLD
                    if action in ['ENTRY', 'EXIT']:
                        decision_color = GREEN if action == 'ENTRY' else YELLOW
                        logger.info(f"{decision_color}🧠 {symbol}: {action} ({confidence:.0%}){RESET}")
                    else:
                        logger.debug(f"🧠 {symbol}: HOLD ({confidence:.0%})")
                    
                    # Execute decision for this symbol
                    if action == 'ENTRY':
                        # Ensure the decision includes the correct symbol
                        llm_decision['symbol'] = symbol
                        await self._handle_entry_decision(llm_decision, market_snapshot['current_price'], portfolio_state, current_bot)

                    elif action == 'EXIT':
                        # CRITICAL: Only process EXIT if there's actually a position
                        if not symbol_positions:
                            logger.warning(f"⚠️  {symbol} LLM decided EXIT but NO POSITION exists!")
                            logger.warning(f"   This symbol should NOT have been analyzed for EXIT.")
                            logger.warning(f"   Active positions: {[p.symbol for p in all_positions]}")
                            continue  # Skip this decision

                        await self._handle_exit_decision(llm_decision, symbol_positions, market_snapshot['current_price'])

                    elif action == 'CLOSE_POSITION':
                        if not symbol_positions:
                            logger.warning(f"⚠️  {symbol} LLM decided CLOSE_POSITION but NO POSITION exists!")
                            continue

                        await self._handle_close_position(llm_decision, symbol_positions, market_snapshot['current_price'])
                    
                except Exception as e:
                    logger.error(f"❌ Error analyzing {symbol}: {e}")
                    continue  # Continue with next symbol even if this one fails
            
            # 3. Update all position prices at the end
            await self._update_position_prices()

            # Increment cycle count
            self.cycle_count += 1

            cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()

            # Log essential completion info only
            if positions_closed_count > 0:
                logger.info(f"✅ Cycle {cycle_duration:.1f}s | Closed: {positions_closed_count} position(s)")
            else:
                logger.debug(f"✅ Cycle {cycle_duration:.1f}s | No exits")

            # Get final position count
            final_positions = await self.position_service.get_open_positions(self.bot_id)
            logger.info(f"   Positions: {len(final_positions)} active, {positions_closed_count} closed")

            # Hourly performance summary (every 12 cycles = 1 hour at 5min intervals)
            if self.cycle_count % 12 == 0:
                await self._log_hourly_summary(current_bot)
            
        except Exception as e:
            logger.error(f"❌ Cycle error: {e}", exc_info=True)
    
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
            timeframe_long=self.timeframe_long  # Long-term context (1h)
        )
        
        logger.debug(f"{symbol} current price: ${snapshot['current_price']}")
        
        # Return snapshot (which already contains both timeframes)
        return {
            'snapshot': snapshot,
            'indicators_4h': snapshot['technical_indicators']['1h']
        }
    
    async def _calculate_indicators(self, market_snapshot: dict) -> dict:
        """Calculate technical indicators."""
        logger.debug("Calculating technical indicators...")
        
        ohlcv = market_snapshot['ohlcv']
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
            
            # Calculate value locked in positions
            invested_in_positions = sum((p.position_value for p in positions), Decimal("0"))
            
            # Get unrealized PnL from open positions
            unrealized_pnl = sum((p.unrealized_pnl for p in positions), Decimal("0"))
            
            # Total portfolio value = available cash + value in positions
            total_value = bot.capital + invested_in_positions
            
            # Calculate total PnL from initial capital
            total_pnl = total_value - bot.initial_capital
            
            portfolio = {
                'total_value': total_value,
                'cash': bot.capital,  # Available cash
                'invested': invested_in_positions,  # Value in open positions
                'total_pnl': total_pnl,
                'unrealized_pnl': unrealized_pnl
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
                sl_distance_pct = ((float(position.stop_loss) - current_price) / current_price) * 100
                tp_distance_pct = ((float(position.take_profit) - current_price) / current_price) * 100

                # ✅ DETAILED LOGGING
                logger.info(f"")
                logger.info(f"  [{position.symbol}] Position Status:")
                logger.info(f"    Entry: ${position.entry_price:,.2f} @ {position.opened_at.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"    Current: ${current_price:,.2f} | PnL: {pnl_pct:+.2f}%")
                logger.info(f"    Hold: {hold_hours:.1f}h (warn at 2h)")
                logger.info(f"    SL: ${position.stop_loss:,.2f} (distance: {sl_distance_pct:+.2f}%)")
                logger.info(f"    TP: ${position.take_profit:,.2f} (distance: {tp_distance_pct:+.2f}%)")

            except Exception as e:
                logger.error(f"Error fetching price for {position.symbol}: {e}")
                continue

            # Check stop loss / take profit
            exit_reason = await self.position_service.check_stop_loss_take_profit(
                position, current_price  # ✅ Prix correct maintenant !
            )

            if exit_reason:
                logger.info(f"🚨 {position.symbol} Position {position.id} hit {exit_reason.upper()}")
                logger.info(f"   Entry: ${position.entry_price:,.2f} | Current: ${current_price:,.2f} | "
                          f"SL: ${position.stop_loss:,.2f} | TP: ${position.take_profit:,.2f}")

                await self.trade_executor.execute_exit(
                    position=position,
                    current_price=current_price,
                    reason=exit_reason
                )
                continue

            # Additional exit conditions for stuck positions
            # If position is more than 2 hours old and PnL is negative beyond -2%, force exit
            position_age = datetime.utcnow() - position.opened_at
            if position_age.total_seconds() > 7200:  # 2 hours
                pnl_pct = float(position.unrealized_pnl_pct)
                if pnl_pct < -2.0:
                    logger.warning(f"⏰ Position {position.id} aged {position_age.total_seconds()/3600:.1f}h with {pnl_pct:.2f}% loss - force closing")
                    await self.trade_executor.execute_exit(
                        position=position,
                        current_price=current_price,
                        reason="time_based_loss_limit"
                    )
                elif pnl_pct > 1.0:
                    logger.info(f"⏰ Position {position.id} aged {position_age.total_seconds()/3600:.1f}h with {pnl_pct:.2f}% profit - taking profit")
                    await self.trade_executor.execute_exit(
                        position=position,
                        current_price=current_price,
                        reason="time_based_profit_taking"
                    )
    
    async def _save_llm_decision(self, prompt: str, llm_result: dict, symbol: str = None) -> LLMDecision:
        """Save LLM decision to database.
        
        Args:
            prompt: The prompt sent to LLM
            llm_result: The LLM response result
            symbol: Optional symbol this decision is for
        """
        # Add symbol to parsed decisions if provided
        parsed_decisions = llm_result['parsed_decisions'].copy()
        if symbol and 'symbol' not in parsed_decisions:
            parsed_decisions['symbol'] = symbol
        
        # Create a fresh session for this operation
        async with AsyncSessionLocal() as fresh_db:
            decision = LLMDecision(
                bot_id=self.bot_id,
                prompt=prompt,
                response=llm_result['response'],
                parsed_decisions=parsed_decisions,
                tokens_used=llm_result['tokens_used'],
                cost=Decimal(str(llm_result['cost'])),
                timestamp=datetime.utcnow()
            )
            
            fresh_db.add(decision)
            await fresh_db.commit()
            await fresh_db.refresh(decision)
            
            return decision
    
    async def _handle_entry_decision(self, decision: dict, current_price: Decimal, portfolio_state: dict, current_bot: Bot) -> None:
        """Handle entry decision from LLM."""
        # Get current positions and trades count
        positions = await self.position_service.get_open_positions(self.bot_id)
        trades_today = await self._get_trades_today_count()
        
        max_trades = current_bot.risk_params.get('max_trades_per_day', 10)
        logger.info(f"   📊 Trades: {trades_today}/{max_trades} today")
        
        # Validate decision with risk manager
        is_valid, message = RiskManagerService.validate_complete_decision(
            bot=current_bot,
            decision=decision,
            current_positions=positions,
            current_price=current_price,
            trades_today=trades_today,
            portfolio_value=portfolio_state['total_value']
        )
        
        if not is_valid:
            logger.warning(f"⛔ {symbol} Entry rejected: {message}")
            return

        # Execute entry
        position, trade = await self.trade_executor.execute_entry(
            bot=current_bot,
            decision=decision,
            current_price=current_price
        )

        if position and trade:
            logger.info(f"{GREEN}✅ BUY {position.quantity:.4f} {position.symbol.split('/')[0]} @ ${position.entry_price:,.2f}{RESET}")
        else:
            logger.error(f"❌ {symbol} Trade execution failed")
    
    async def _handle_exit_decision(
        self,
        decision: dict,
        positions: list,
        current_price: Decimal
    ) -> None:
        """Handle exit decision from LLM."""
        logger.info("Processing exit decision...")
        
        # Find position to close (first open position for now)
        if not positions:
            logger.warning(f"Exit requested for {symbol} but no open positions")
            return

        position = positions[0]  # Close first position

        await self.trade_executor.execute_exit(
            position=position,
            current_price=current_price,
            reason="llm_decision"
        )

        logger.info(f"✅ EXIT {position.symbol.split('/')[0]} @ ${current_price:,.2f}")
    
    async def _handle_close_position(
        self,
        decision: dict,
        positions: list,
        current_price: Decimal
    ) -> None:
        """Handle emergency close position."""
        logger.warning("Processing emergency close...")
        
        # Close all positions
        for position in positions:
            await self.trade_executor.execute_exit(
                position=position,
                current_price=current_price,
                reason="emergency_close"
            )
            logger.info(f"🚨 EMERGENCY CLOSE {position.symbol.split('/')[0]} @ ${current_price:,.2f}")
    
    async def _update_position_prices(self) -> None:
        """Update current prices for all open positions."""
        positions = await self.position_service.get_open_positions(self.bot_id)
        
        for position in positions:
            try:
                current_price = await self.market_data_service.get_current_price(position.symbol)
                await self.position_service.update_current_price(position.id, current_price)
            except Exception as e:
                logger.error(f"Error updating price for position {position.id}: {e}")
    
    async def check_exit_conditions(self, position, current_price: float) -> bool:
        """
        Vérifier si une position doit être fermée automatiquement.

        Args:
            position: L'objet position à vérifier
            current_price: Le prix actuel du marché

        Returns:
            True si la position a été fermée, False sinon
        """

        # Calculer le temps de détention
        hold_hours = (datetime.utcnow() - position.opened_at).total_seconds() / 3600

        # Calculer le P&L %
        if position.side.value == "LONG":
            pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
        else:  # SHORT
            pnl_pct = ((position.entry_price - current_price) / position.entry_price) * 100

        # 1. STOP LOSS HIT (avec buffer 0.5% pour éviter les faux déclenchements)
        sl_threshold = position.stop_loss * Decimal("1.005") if position.side.value == "LONG" else position.stop_loss * Decimal("0.995")

        if position.side.value == "LONG" and current_price <= sl_threshold:
            logger.warning(f"🛑 SL HIT: {position.symbol} @ ${current_price:,.2f} (SL: ${position.stop_loss:,.2f})")
            logger.info(f"   Hold time: {hold_hours:.1f}h | P&L: {pnl_pct:.2f}%")
            await self.execute_exit(position, reason="SL_HIT", price=current_price)
            return True

        if position.side.value == "SHORT" and current_price >= sl_threshold:
            logger.warning(f"🛑 SL HIT: {position.symbol} @ ${current_price:,.2f} (SL: ${position.stop_loss:,.2f})")
            logger.info(f"   Hold time: {hold_hours:.1f}h | P&L: {pnl_pct:.2f}%")
            await self.execute_exit(position, reason="SL_HIT", price=current_price)
            return True

        # 2. TAKE PROFIT HIT (avec buffer 0.5%)
        tp_threshold = position.take_profit * Decimal("0.995") if position.side.value == "LONG" else position.take_profit * Decimal("1.005")

        if position.side.value == "LONG" and current_price >= tp_threshold:
            logger.info(f"🎯 TP HIT: {position.symbol} @ ${current_price:,.2f} (TP: ${position.take_profit:,.2f})")
            logger.info(f"   Hold time: {hold_hours:.1f}h | P&L: {pnl_pct:.2f}%")
            await self.execute_exit(position, reason="TP_HIT", price=current_price)
            return True

        if position.side.value == "SHORT" and current_price <= tp_threshold:
            logger.info(f"🎯 TP HIT: {position.symbol} @ ${current_price:,.2f} (TP: ${position.take_profit:,.2f})")
            logger.info(f"   Hold time: {hold_hours:.1f}h | P&L: {pnl_pct:.2f}%")
            await self.execute_exit(position, reason="TP_HIT", price=current_price)
            return True

        # 3. TIMEOUT - Position trop longue en perte
        if hold_hours > 24 and pnl_pct < -1.0:
            logger.warning(f"⏱️ TIMEOUT: {position.symbol} - Position trop longue en perte")
            logger.info(f"   Hold time: {hold_hours:.1f}h | P&L: {pnl_pct:.2f}%")
            await self.execute_exit(position, reason="TIMEOUT_LOSS", price=current_price)
            return True

        # 4. GRANDE PERTE - Protection contre les pertes importantes
        if pnl_pct < -2.5:
            logger.error(f"⚠️ LARGE LOSS: {position.symbol} - Perte importante détectée")
            logger.info(f"   Hold time: {hold_hours:.1f}h | P&L: {pnl_pct:.2f}%")
            await self.execute_exit(position, reason="LARGE_LOSS", price=current_price)
            return True

        # 5. STAGNATION PROLONGÉE - Position breakeven > 12h
        if hold_hours > 12 and abs(pnl_pct) < 0.5:
            logger.info(f"💤 STAGNATION: {position.symbol} - Aucun mouvement significatif")
            logger.info(f"   Hold time: {hold_hours:.1f}h | P&L: {pnl_pct:.2f}%")
            await self.execute_exit(position, reason="STAGNATION", price=current_price)
            return True

        # Position OK, pas de sortie nécessaire
        logger.debug(f"✓ {position.symbol}: Hold time {hold_hours:.1f}h | P&L {pnl_pct:.2f}% | No exit conditions met")
        return False


    async def manage_positions(self) -> dict:
        """
        Gérer toutes les positions actives et vérifier les conditions de sortie.
        Cette fonction doit être appelée au début de chaque cycle de trading.

        Returns:
            dict: Statistiques sur les positions gérées
        """
        stats = {
            "total_positions": 0,
            "positions_checked": 0,
            "positions_closed": 0,
            "reasons": {}
        }

        try:
            # Récupérer toutes les positions actives
            positions = await self.position_service.get_open_positions(self.bot_id)
            stats["total_positions"] = len(positions)

            if not positions:
                logger.debug("📍 No active positions to manage")
                return stats

            logger.info(f"📍 Managing {len(positions)} active position(s)")

            for position in positions:
                stats["positions_checked"] += 1

                try:
                    # Récupérer le prix actuel
                    current_price = await self.market_data_service.get_current_price(position.symbol)

                    # Vérifier les conditions de sortie
                    should_exit = await self.check_exit_conditions(position, current_price)

                    if should_exit:
                        stats["positions_closed"] += 1
                        # Incrémenter le compteur de raison (si disponible)
                        reason = getattr(position, 'exit_reason', 'UNKNOWN')
                        stats["reasons"][reason] = stats["reasons"].get(reason, 0) + 1

                except Exception as e:
                    logger.error(f"❌ Error checking position {position.symbol}: {e}")
                    continue

            # Résumé concis
            if stats["positions_closed"] > 0:
                logger.info(f"✅ Closed {stats['positions_closed']}/{stats['positions_checked']} positions")
            else:
                logger.debug(f"✓ {stats['positions_checked']} positions OK")

        except Exception as e:
            logger.error(f"❌ Error in manage_positions: {e}")

        return stats


    async def execute_exit(self, position, reason: str, price: Optional[float] = None) -> bool:
        """
        Exécuter la fermeture d'une position.

        Args:
            position: La position à fermer
            reason: La raison de la fermeture (SL_HIT, TP_HIT, TIMEOUT, etc.)
            price: Le prix de sortie (optionnel, sera récupéré si None)

        Returns:
            bool: True si la fermeture a réussi, False sinon
        """
        try:
            # Récupérer le prix actuel si non fourni
            if price is None:
                price = await self.market_data_service.get_current_price(position.symbol)

            # Calculer le P&L
            if position.side.value == "LONG":
                pnl = (price - position.entry_price) * position.quantity
                pnl_pct = ((price - position.entry_price) / position.entry_price) * 100
            else:
                pnl = (position.entry_price - price) * position.quantity
                pnl_pct = ((position.entry_price - price) / position.entry_price) * 100

            # Log détaillé
            logger.info(f"🚪 CLOSING POSITION: {position.symbol}")
            logger.info(f"   Entry: ${position.entry_price:,.2f} → Exit: ${price:,.2f}")
            logger.info(f"   Quantity: {position.quantity} | Side: {position.side.value}")
            logger.info(f"   P&L: ${pnl:+,.2f} ({pnl_pct:+.2f}%)")
            logger.info(f"   Reason: {reason}")

            # Exécuter l'ordre de fermeture via l'exchange
            # NOTE: Adapter cette partie selon votre API d'exchange
            result = await self.trade_executor.execute_exit(
                position=position,
                current_price=Decimal(str(price)),
                reason=reason
            )

            if result:
                logger.info(f"✅ Position {position.symbol} closed successfully")
                return True
            else:
                logger.error(f"❌ Failed to close position {position.symbol}")
                return False

        except Exception as e:
            logger.error(f"❌ Error executing exit for {position.symbol}: {e}")
            return False


    async def _check_exit_conditions(self) -> None:
        """
        Check if any open positions should be exited based on SL/TP.
        This function is CRITICAL - without it, positions stay open forever.

        Checks for:
        1. Stop Loss hit (price <= SL + 0.5% buffer)
        2. Take Profit hit (price >= TP - 0.5% buffer)
        3. Timeout (position > 24h in loss > 1%)
        4. Large loss (PnL < -2.5%)
        """
        positions = await self.position_service.get_open_positions(self.bot_id)

        if not positions:
            return

        logger.debug(f"🔍 Checking exit conditions for {len(positions)} positions")

        for position in positions:
            try:
                # Get current price
                current_price = await self.market_data_service.get_current_price(position.symbol)

                # Calculate current PnL
                pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
                if position.side.value == 'short':
                    pnl_pct = -pnl_pct

                # Calculate hold time in hours
                hold_time = datetime.utcnow() - position.opened_at
                hold_hours = hold_time.total_seconds() / 3600

                exit_reason = None

                # 1. CHECK STOP LOSS (with 0.5% buffer to avoid edge cases)
                sl_threshold = position.stop_loss * Decimal("1.005")
                if current_price <= sl_threshold:
                    exit_reason = f"SL_HIT (Price: ${current_price:,.2f} <= SL: ${position.stop_loss:,.2f})"
                    logger.warning(f"🛑 {position.symbol} {exit_reason}")

                # 2. CHECK TAKE PROFIT (with 0.5% buffer)
                elif current_price >= position.take_profit * Decimal("0.995"):
                    exit_reason = f"TP_HIT (Price: ${current_price:,.2f} >= TP: ${position.take_profit:,.2f})"
                    logger.info(f"🎯 {position.symbol} {exit_reason}")

                # 3. CHECK TIMEOUT (position > 24h in loss > 1%)
                elif hold_hours > 24 and pnl_pct < -1.0:
                    exit_reason = f"TIMEOUT_LOSS (Hold: {hold_hours:.1f}h, PnL: {pnl_pct:.2f}%)"
                    logger.warning(f"⏱️ {position.symbol} {exit_reason}")

                # 4. CHECK LARGE LOSS (> 2.5% even if not at SL yet)
                elif pnl_pct < -2.5:
                    exit_reason = f"LARGE_LOSS (PnL: {pnl_pct:.2f}%)"
                    logger.warning(f"⚠️ {position.symbol} {exit_reason}")

                # If any exit condition met, execute exit
                if exit_reason:
                    logger.info(f"💥 Executing automatic exit for {position.symbol}: {exit_reason}")

                    trade = await self.trade_executor.execute_exit(
                        position=position,
                        current_price=current_price,
                        reason=exit_reason.split()[0]  # Extract reason code (SL_HIT, TP_HIT, etc.)
                    )

                    if trade:
                        # Color PnL
                        pnl_color = GREEN if trade.realized_pnl >= 0 else RED
                        logger.info(f"{pnl_color}   ✅ EXIT {position.quantity:.4f} {position.symbol.split('/')[0]} @ ${current_price:,.2f} | PnL: ${trade.realized_pnl:+,.2f} ({pnl_pct:+.2f}%){RESET}")
                    else:
                        logger.error(f"   ❌ Exit execution failed for {position.symbol}")

                else:
                    # Position is safe, log status
                    logger.debug(f"   ✓ {position.symbol}: Price ${current_price:,.2f} | PnL {pnl_pct:+.2f}% | Hold {hold_hours:.1f}h | Status: OK")

            except Exception as e:
                logger.error(f"Error checking exit conditions for position {position.id}: {e}")
                continue
    
    async def _log_hourly_summary(self, bot: Bot) -> None:
        """Log hourly performance summary."""
        # Get current portfolio state
        portfolio_state, _ = await self._get_portfolio_state()
        
        # Get positions
        positions = await self.position_service.get_open_positions(self.bot_id)
        
        # Get trades count today
        trades_today = await self._get_trades_today_count()
        
        # Calculate metrics
        equity = portfolio_state['total_value']
        invested = portfolio_state['invested']
        unrealized_pnl = portfolio_state['unrealized_pnl']
        return_pct = ((equity - bot.initial_capital) / bot.initial_capital) * 100
        capital_utilization = (invested / equity * 100) if equity > 0 else 0
        
        # Calculate session duration
        session_duration = (datetime.utcnow() - self.session_start).total_seconds() / 3600  # in hours
        
        # Colors
        pnl_color = GREEN if unrealized_pnl >= 0 else RED
        return_color = GREEN if return_pct >= 0 else RED
        
        logger.info("")
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║" + " " * 25 + "📊 HOURLY SUMMARY" + " " * 36 + "║")
        logger.info("╠" + "═" * 78 + "╣")
        logger.info(f"║  ⏱️  Session Time: {session_duration:.1f}h | Cycles: {self.cycle_count}" + " " * (78 - 38 - len(str(self.cycle_count))) + "║")
        logger.info("╠" + "─" * 78 + "╣")
        logger.info(f"║  💰 Equity: ${equity:,.2f} | Initial: ${bot.initial_capital:,.2f}" + " " * (78 - 37 - len(f"{equity:,.2f}") - len(f"{bot.initial_capital:,.2f}")) + "║")
        logger.info(f"║  {return_color}📈 Return: {return_pct:+.2f}%{RESET}" + " " * (78 - 17 - len(f"{return_pct:+.2f}")) + "║")
        logger.info(f"║  {pnl_color}💵 Unrealized PnL: ${unrealized_pnl:+,.2f}{RESET}" + " " * (78 - 24 - len(f"{unrealized_pnl:+,.2f}")) + "║")
        logger.info("╠" + "─" * 78 + "╣")
        logger.info(f"║  📍 Open Positions: {len(positions)}" + " " * (78 - 22 - len(str(len(positions)))) + "║")
        logger.info(f"║  🎯 Trades Today: {trades_today}" + " " * (78 - 20 - len(str(trades_today))) + "║")
        logger.info(f"║  📊 Capital Utilization: {capital_utilization:.1f}%" + " " * (78 - 28 - len(f"{capital_utilization:.1f}")) + "║")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("")
    
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
                Trade.realized_pnl == Decimal("0")  # Entry trades have no PnL
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
                        symbol=symbol,
                        timeframe=self.timeframe,
                        limit=50
                    )
                    
                    if not ohlcv or len(ohlcv) < 20:
                        logger.warning(f"Not enough data for {symbol}, skipping")
                        continue
                    
                    # Extract prices (closing prices)
                    closes = self.market_data_service.extract_closes(ohlcv)
                    
                    # Get current price and volume
                    current_price = closes[-1] if closes else 0
                    latest_candle = ohlcv[-1] if ohlcv else None
                    volume = float(latest_candle.volume) if latest_candle else 0  # Use OHLCV object attribute
                    
                    # Calculate approximate market cap (price * volume as proxy)
                    # In real scenario, you'd fetch this from API
                    market_cap = float(current_price) * volume
                    
                    multi_coin_data[symbol] = {
                        'prices': [float(p) for p in closes],
                        'volume': float(volume),
                        'market_cap': market_cap,
                        'current_price': float(current_price)
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
                logger.warning(f"Not enough symbols with data ({len(multi_coin_data)}), skipping multi-coin analysis")
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
                    timeframe_long=self.timeframe_long
                )
                
                if snapshot:
                    # Use the COMPLETE snapshot with all calculated indicators
                    all_coins[symbol] = snapshot
                    logger.debug(f"✓ {symbol}: Complete snapshot with technical indicators")
                    
            except Exception as e:
                logger.warning(f"Error fetching snapshot for {symbol}: {e}")
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
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
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