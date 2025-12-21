"""Block: LLM Decision - Handles LLM calls and decision parsing.

This block is responsible for:
- Building prompts for the LLM
- Calling the LLM API
- Parsing and validating responses
- Fixing out-of-range values
"""

import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional

from ..core.config import config
from ..core.llm_client import LLMClient
from ..core.logger import get_logger
from ..services.llm_decision_validator import LLMDecisionValidator
from ..services.multi_coin_prompt_service import MultiCoinPromptService

logger = get_logger(__name__)

FORCED_MODEL = os.getenv("FORCE_DEEPSEEK_MODEL", "deepseek-chat")


@dataclass
class TradingDecision:
    """A parsed trading decision from the LLM."""

    symbol: str
    signal: str  # buy_to_enter, sell_to_enter, close, hold
    confidence: float
    side: str  # long or short
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    size_pct: float = config.DEFAULT_POSITION_SIZE_PCT
    leverage: int = int(config.DEFAULT_LEVERAGE)
    reasoning: str = ""


class LLMDecisionBlock:
    """Handles LLM calls and decision parsing."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()
        self.prompt_service = MultiCoinPromptService()
        self.validator = LLMDecisionValidator()

    async def get_decisions(
        self,
        market_data: Dict[str, Any],
        portfolio_context: Dict[str, Any],
        bot_name: str = "0xBot",
    ) -> Dict[str, TradingDecision]:
        """
        Get trading decisions for all symbols.

        Args:
            market_data: Dict of symbol -> market snapshot
            portfolio_context: Current portfolio state
            bot_name: Bot name for logging

        Returns:
            Dict of symbol -> TradingDecision
        """
        try:
            # Convert market snapshots to dict format for prompt service
            all_coins_data = {}
            for symbol, snap in market_data.items():
                all_coins_data[symbol] = {
                    "price": float(snap.price),
                    "change_24h": snap.change_24h,
                    "rsi": snap.rsi,
                    "ema_fast": snap.ema_fast,
                    "ema_slow": snap.ema_slow,
                    "atr": snap.atr,
                    "trend": snap.trend,
                }

            # Get positions from context
            positions = portfolio_context.get("positions", [])

            # Build prompt using prompt service
            prompt_result = self.prompt_service.get_multi_coin_decision(
                bot=None,  # Not needed for prompt generation
                all_coins_data=all_coins_data,
                all_positions=positions,
                portfolio_state=portfolio_context,
            )
            prompt = prompt_result.get("prompt", "")

            # Call LLM using DeepSeek
            logger.info(f"📊 Calling LLM for {len(market_data)} symbols...")
            response = await self.llm_client.analyze_market(
                model=FORCED_MODEL,
                prompt=prompt,
                max_tokens=2048,
                temperature=0.7,
            )

            logger.info(f"DeepSeek response: " f"{response.get('tokens_used', '?')} tokens")

            # Parse response
            raw_decisions = self._parse_response(response)

            # Validate and fix decisions
            decisions = {}
            for symbol, raw in raw_decisions.items():
                decision = self._validate_and_fix(symbol, raw, market_data)
                if decision:
                    decisions[symbol] = decision
                    logger.info(
                        f"🧠 {symbol}: {decision.signal} " f"({decision.confidence*100:.0f}%)"
                    )

            return decisions

        except Exception as e:
            logger.error(f"Error getting LLM decisions: {e}")
            return {}

    def _parse_response(self, response: dict) -> Dict[str, dict]:
        """Parse LLM response into raw decisions."""
        # Get raw response content
        content = response.get("response", "")

        if not content:
            logger.warning("Empty LLM response")
            return {}

        # Use prompt service to parse the response
        parsed = self.prompt_service.parse_multi_coin_response(content)

        if not parsed:
            logger.warning("Empty parsed response")
            return {}

        # Handle both formats:
        # 1. {symbol: {signal, ...}} - direct format from fallback
        # 2. {decisions: {symbol: {...}}} - nested format
        if "decisions" in parsed:
            return parsed["decisions"]

        # Check if it looks like direct symbol dict
        first_key = next(iter(parsed.keys()), "")
        if "/" in first_key or "USDT" in first_key:
            return parsed

        logger.warning("Unexpected response format")
        return {}

    def _validate_and_fix(
        self,
        symbol: str,
        raw: dict,
        market_data: Dict[str, Any],
    ) -> Optional[TradingDecision]:
        """Validate and fix a single decision."""
        try:
            signal = raw.get("signal", "hold").lower()
            confidence = float(raw.get("confidence", 0))

            # Skip hold signals
            if signal == "hold":
                return None

            # Skip low confidence
            if confidence < config.MIN_CONFIDENCE_ENTRY:
                logger.info(
                    f"   {symbol}: Skipped (confidence {confidence:.0%} < {config.MIN_CONFIDENCE_ENTRY:.0%})"
                )
                return None

            # Get current price
            current_price = None
            if symbol in market_data:
                snapshot = market_data[symbol]
                if hasattr(snapshot, "price"):
                    current_price = float(snapshot.price)
                elif isinstance(snapshot, dict):
                    current_price = float(snapshot.get("price", 0))

            if not current_price or current_price <= 0:
                logger.warning(f"{symbol}: No valid price, skipping")
                return None

            # Determine side
            side = raw.get("side", "long").lower()
            if signal == "sell_to_enter":
                side = "short"
            elif signal == "buy_to_enter":
                side = "long"

            # Get or calculate SL/TP
            stop_loss = self._get_stop_loss(raw, current_price, side)
            take_profit = self._get_take_profit(raw, current_price, side)

            # Validate SL/TP
            if not self._validate_sl_tp(stop_loss, take_profit, current_price, side):
                logger.info(f"   ✅ {symbol} Decision fixed: SL/TP reset to defaults")
                stop_loss = self._default_stop_loss(current_price, side)
                take_profit = self._default_take_profit(current_price, side)

            return TradingDecision(
                symbol=symbol,
                signal=signal,
                confidence=confidence,
                side=side,
                stop_loss=Decimal(str(stop_loss)),
                take_profit=Decimal(str(take_profit)),
                size_pct=float(raw.get("size_pct", config.DEFAULT_POSITION_SIZE_PCT)),
                leverage=int(raw.get("leverage", config.DEFAULT_LEVERAGE)),
                reasoning=raw.get("reasoning", raw.get("justification", "")),
            )

        except Exception as e:
            logger.error(f"Error validating decision for {symbol}: {e}")
            return None

    def _get_stop_loss(self, raw: dict, price: float, side: str) -> float:
        """Get stop loss price from decision or calculate default."""
        sl = raw.get("stop_loss")
        if sl and float(sl) > 0:
            return float(sl)
        return self._default_stop_loss(price, side)

    def _get_take_profit(self, raw: dict, price: float, side: str) -> float:
        """Get take profit price from decision or calculate default."""
        tp = raw.get("take_profit")
        if tp and float(tp) > 0:
            return float(tp)
        return self._default_take_profit(price, side)

    def _default_stop_loss(self, price: float, side: str) -> float:
        """Calculate default stop loss."""
        sl_pct = config.DEFAULT_STOP_LOSS_PCT
        if side == "long":
            return price * (1 - sl_pct)
        else:
            return price * (1 + sl_pct)

    def _default_take_profit(self, price: float, side: str) -> float:
        """Calculate default take profit."""
        tp_pct = config.DEFAULT_TAKE_PROFIT_PCT
        if side == "long":
            return price * (1 + tp_pct)
        else:
            return price * (1 - tp_pct)

    def _validate_sl_tp(
        self,
        sl: float,
        tp: float,
        price: float,
        side: str,
    ) -> bool:
        """Validate stop loss and take profit positions."""
        if side == "long":
            # SL below entry, TP above entry
            return sl < price < tp
        else:
            # SL above entry, TP below entry
            return tp < price < sl
