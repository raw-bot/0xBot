"""Decision executor - executes LLM trading decisions."""

from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import config
from ...core.logger import get_logger
from ...models.bot import Bot
from ..llm_decision_validator import LLMDecisionValidator
from ..position_service import PositionService
from ..risk_manager_service import RiskManagerService
from ..trade_executor_service import TradeExecutorService
from ...core.activity_logger import ActivityLogger

logger = get_logger(__name__)

GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"


class DecisionExecutor:
    """Executes LLM decisions for trading positions."""

    def __init__(self, db: AsyncSession, bot_id: str):
        self.db = db
        self.bot_id = bot_id
        self.position_service = PositionService(db)
        self.trade_executor = TradeExecutorService(db)

    async def execute_decisions(
        self,
        all_coins_data: dict[str, Any],
        decisions: dict[str, dict[str, Any]],
        current_positions: list[Any],
        current_bot: Bot,
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
                    if side is not None:
                        await self._handle_entry(
                            symbol,
                            side,
                            confidence,
                            reasoning,
                            decision,
                            current_price,
                            current_positions,
                            current_bot,
                        )
            except Exception as e:
                logger.error(f"Error executing decision for {symbol}: {e}")

    async def _handle_exit_if_needed(
        self,
        symbol: str,
        action: str,
        confidence: float,
        current_positions: list[Any],
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
        decision: dict[str, Any],
        current_price: float,
        current_positions: list[Any],
        current_bot: Bot,
    ) -> None:
        """Handle entry decision for new position."""
        portfolio_state: dict[str, Any] = {"total_value": 1}
        # TODO: Get portfolio state from cycle manager if needed
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
        self, decision: dict[str, Any], current_price: float, total_value: float, default_size: float
    ) -> float:
        """Calculate position size percentage from LLM quantity or use default."""
        quantity = float(decision.get("quantity", 0))
        if quantity > 0 and current_price > 0 and total_value > 0:
            calculated_size = (quantity * current_price) / total_value
            if 0.05 <= calculated_size <= default_size:
                return calculated_size
        return default_size

    async def _handle_entry_decision(
        self, decision: dict[str, Any], current_price: Decimal, portfolio_state: dict[str, Any], current_bot: Bot
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
            sl = position.stop_loss
            tp = position.take_profit
            ActivityLogger.log_trade_entry(
                bot_name=current_bot.name,
                symbol=position.symbol,
                side=position.side,
                quantity=float(position.quantity),
                entry_price=float(position.entry_price),
                stop_loss=float(sl) if sl is not None else 0.0,
                take_profit=float(tp) if tp is not None else 0.0,
                confidence=float(decision.get("confidence", 0)),
            )
        else:
            logger.error(f"{symbol} Trade execution failed")
