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
        
        # Initialize services
        self.market_data_service = MarketDataService()
        self.position_service = PositionService(db)
        self.trade_executor = TradeExecutorService(db)
        self.llm_client = llm_client or get_llm_client()
        
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
        logger.info("=" * 80)
        
        try:
            # 1. Get portfolio state once (this will reload bot with latest capital)
            portfolio_state, current_bot = await self._get_portfolio_state()
            
            # Log general bot info
            logger.info(f"🤖 {current_bot.name} | {cycle_start.strftime('%H:%M:%S')}")
            
            # Calculate returns based on total equity (not just cash)
            equity = portfolio_state['total_value']
            cash = portfolio_state['cash']
            invested = portfolio_state['invested']
            return_pct = ((equity - current_bot.initial_capital) / current_bot.initial_capital) * 100
            
            # Color capital based on performance
            capital_color = GREEN if return_pct >= 0 else YELLOW
            logger.info(f"{capital_color}💰 Equity: ${equity:,.2f} (Cash: ${cash:,.2f} + Invested: ${invested:,.2f}) | Initial: ${current_bot.initial_capital:,.2f} | Return: {return_pct:+.2f}%{RESET}")
            
            # Get all positions across all symbols
            all_positions = await self.position_service.get_open_positions(self.bot_id)
            logger.info(f"📍 Total Positions: {len(all_positions)}")
            
            if all_positions:
                for pos in all_positions:
                    # Color position based on PnL
                    pnl_color = GREEN if pos.unrealized_pnl >= 0 else YELLOW
                    logger.info(f"{pnl_color}   • {pos.symbol} {pos.side.upper()} {pos.quantity:.4f} @ ${pos.entry_price:,.2f} | PnL: ${pos.unrealized_pnl:+,.2f}{RESET}")
            
            # 1.5 Fetch multi-coin context (correlations, regime, breadth, etc.)
            logger.info("📊 Analyzing multi-coin market context...")
            market_context = await self._get_multi_coin_market_context()
            
            if market_context and market_context.get('regime'):
                regime = market_context['regime']['regime']
                confidence = market_context['regime']['confidence']
                breadth = market_context['breadth']
                logger.info(f"   Market Regime: {regime.upper()} ({confidence:.0%} confidence)")
                logger.info(f"   Breadth: {breadth.get('advancing', 0)} up / {breadth.get('declining', 0)} down")
            
            # 2. Loop through each trading symbol
            for symbol in self.trading_symbols:
                logger.info("─" * 80)
                logger.info(f"📈 Analyzing {symbol}")
                
                try:
                    # Fetch market data for this symbol
                    market_data = await self._fetch_market_data(symbol)
                    market_snapshot = market_data['snapshot']
                    indicators_4h = market_data['indicators_4h']
                    
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
                    
                    logger.info(f"📊 ${market_snapshot['current_price']:,.2f} | RSI: {rsi_str}")
                    
                    # Get positions for this specific symbol
                    symbol_positions = [p for p in all_positions if p.symbol == symbol]
                    
                    # Check exits for positions of this symbol
                    await self._check_position_exits(symbol_positions, market_snapshot['current_price'])
                    
                    # Build enhanced LLM prompt with multi-coin context for this symbol
                    prompt = LLMPromptService.build_enhanced_market_prompt(
                        symbol=symbol,
                        market_data=market_snapshot,
                        indicators=latest_indicators,
                        positions=symbol_positions,
                        portfolio=portfolio_state,
                        risk_params=current_bot.risk_params,
                        indicators_4h=indicators_4h,
                        market_context=market_context  # NEW: Include multi-coin analysis
                    )
                    
                    # Get LLM decision for this symbol
                    llm_result = await self.llm_client.analyze_market(
                        model=current_bot.model_name,
                        prompt=prompt,
                        max_tokens=1024,
                        temperature=0.7
                    )
                    
                    # Save decision
                    await self._save_llm_decision(prompt=prompt, llm_result=llm_result, symbol=symbol)
                    
                    # Parse and display decision
                    decision = llm_result['parsed_decisions']
                    action = decision.get('action', 'hold').upper()
                    reasoning = decision.get('reasoning', 'No reasoning provided')
                    confidence = decision.get('confidence', 0)
                    
                    # Color decision based on action
                    if action == 'ENTRY':
                        decision_color = GREEN
                    elif action == 'EXIT':
                        decision_color = YELLOW
                    else:  # HOLD
                        decision_color = CYAN
                    logger.info(f"{decision_color}🧠 {symbol} Decision: {action} (Confidence: {confidence:.0%}){RESET}")
                    logger.info(f"   Reasoning: {reasoning[:100]}...")  # Shortened for multi-symbol
                    
                    # Execute decision for this symbol
                    if action == 'ENTRY':
                        # Ensure the decision includes the correct symbol
                        decision['symbol'] = symbol
                        await self._handle_entry_decision(decision, market_snapshot['current_price'], portfolio_state, current_bot)
                    elif action == 'EXIT':
                        await self._handle_exit_decision(decision, symbol_positions, market_snapshot['current_price'])
                    elif action == 'CLOSE_POSITION':
                        await self._handle_close_position(decision, symbol_positions, market_snapshot['current_price'])
                    
                except Exception as e:
                    logger.error(f"❌ Error analyzing {symbol}: {e}")
                    continue  # Continue with next symbol even if this one fails
            
            # 3. Update all position prices at the end
            await self._update_position_prices()
            
            cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
            logger.info("─" * 80)
            logger.info(f"✅ Cycle completed in {cycle_duration:.1f}s | Next in {self.cycle_interval//60}min")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"❌ Cycle error: {e}", exc_info=True)
    
    async def _fetch_market_data(self, symbol: str) -> dict:
        """Fetch current market data with multi-timeframe support for a specific symbol.
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            
        Returns:
            Dictionary with snapshot and 4h indicators
        """
        logger.debug(f"Fetching multi-timeframe market data for {symbol}...")
        
        # Fetch multi-timeframe data (5min + 1h)
        multi_tf_data = await self.market_data_service.get_market_data_multi_timeframe(
            symbol=symbol,
            timeframe_short=self.timeframe,  # Current timeframe (5min - ALIGNED with cycle)
            timeframe_long=self.timeframe_long  # Long-term context (1h)
        )
        
        snapshot = multi_tf_data['short']
        logger.debug(f"{symbol} current price: ${snapshot['current_price']}")
        
        # Return both short and long timeframe data
        return {
            'snapshot': snapshot,
            'indicators_4h': multi_tf_data['long']
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
    
    async def _check_position_exits(self, positions: list, current_price: Decimal) -> None:
        """Check if any positions should be closed due to stop loss, take profit, or time-based exit."""
        for position in positions:
            if position.status != PositionStatus.OPEN:
                continue
            
            # Check stop loss / take profit
            exit_reason = await self.position_service.check_stop_loss_take_profit(
                position, current_price
            )
            
            if exit_reason:
                logger.info(f"🚨 Position {position.id} hit {exit_reason}, executing exit")
                
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
            logger.warning(f"   ⛔ Entry rejected: {message}")
            return
        
        # Execute entry
        position, trade = await self.trade_executor.execute_entry(
            bot=current_bot,
            decision=decision,
            current_price=current_price
        )
        
        if position and trade:
            logger.info(f"{GREEN}   ✅ BUY {position.quantity:.4f} {position.symbol.split('/')[0]} @ ${position.entry_price:,.2f} (${position.position_value:,.2f}){RESET}")
        else:
            logger.error("   ❌ Trade execution failed")
    
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
            logger.warning("Exit requested but no open positions")
            return
        
        position = positions[0]  # Close first position
        
        await self.trade_executor.execute_exit(
            position=position,
            current_price=current_price,
            reason="llm_decision"
        )
        
        logger.info(f"Exit executed for position {position.id}")
    
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