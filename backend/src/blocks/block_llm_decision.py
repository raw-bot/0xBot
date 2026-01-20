"""Block: LLM Decision - Handles LLM calls and decision parsing."""

import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, cast
from uuid import UUID

from ..core.config import config
from ..core.llm_client import LLMClient
from ..core.logger import get_logger
from ..core.memory.memory_manager import MemoryManager
from ..services.multi_coin_prompt_service import MultiCoinPromptService
from ..services.trading_memory_service import TradingMemoryService

logger = get_logger(__name__)

FORCED_MODEL = os.getenv("FORCE_DEEPSEEK_MODEL", "deepseek-chat")
MAX_SIZE_PCT = 0.25


@dataclass
class TradingDecision:
    """A parsed trading decision from the LLM."""

    symbol: str
    signal: str
    confidence: float
    side: str
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    size_pct: float = config.DEFAULT_POSITION_SIZE_PCT
    leverage: int = int(config.DEFAULT_LEVERAGE)
    reasoning: str = ""


class LLMDecisionBlock:
    """Handles LLM calls and decision parsing with memory integration."""

    def __init__(self, llm_client: Optional[LLMClient] = None, bot_id: Optional[UUID] = None):
        self.llm_client = llm_client or LLMClient()
        self.prompt_service = MultiCoinPromptService()
        self.bot_id = bot_id
        self.memory = TradingMemoryService(bot_id) if bot_id else None

    async def get_decisions(
        self,
        market_data: Dict[str, Any],
        portfolio_context: Dict[str, Any],
        bot_name: str = "0xBot",
    ) -> Dict[str, TradingDecision]:
        """Get trading decisions for all symbols."""
        try:
            all_coins_data = self._build_coins_data(market_data)
            positions = portfolio_context.get("positions", [])

            prompt_result = self.prompt_service.get_multi_coin_decision(
                bot=None,
                all_coins_data=all_coins_data,
                all_positions=positions,
                portfolio_state=portfolio_context,
            )

            logger.info(f"Calling LLM for {len(market_data)} symbols...")
            response = await self.llm_client.analyze_market(
                model=FORCED_MODEL,
                prompt=prompt_result.get("prompt", ""),
                max_tokens=2048,
                temperature=0.7,
            )

            raw_decisions = self._parse_response(response)

            decisions = {}
            for symbol, raw in raw_decisions.items():
                decision = self._validate_and_fix(symbol, raw, market_data)
                if decision:
                    # Adjust confidence based on memory (if enabled)
                    if self.memory and MemoryManager.is_enabled():
                        adjusted_decision = await self._apply_memory_adjustment(symbol, decision)
                        decisions[symbol] = adjusted_decision
                    else:
                        decisions[symbol] = decision

                    logger.info(f"{symbol}: {decision.signal} ({decision.confidence*100:.0f}%)")

            return decisions

        except Exception as e:
            logger.error(f"Error getting LLM decisions: {e}")
            return {}

    def _build_coins_data(self, market_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Convert market snapshots to format expected by prompt service."""
        result = {}
        for symbol, snap in market_data.items():
            ohlcv = getattr(snap, "ohlcv_1h", None) or []
            price_series = [float(c.close) for c in ohlcv] if ohlcv else []

            result[symbol] = {
                "current_price": float(snap.price),
                "funding_rate": 0.0,
                "open_interest": {"latest": 0},
                "technical_indicators": {
                    "1h": {
                        "rsi14": snap.rsi or 50,
                        "ema20": snap.ema_fast or 0,
                        "ema50": snap.ema_slow or 0,
                    }
                },
                "price_series": price_series,
                "ohlcv": ohlcv,
                "timeframe": "1h",
                "change_24h": snap.change_24h or 0,
                "atr": snap.atr or 0,
                "trend": snap.trend or "neutral",
            }
        return result

    def _parse_response(self, response: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Parse LLM response into raw decisions."""
        content = response.get("response", "")
        if not content:
            return {}

        parsed = self.prompt_service.parse_multi_coin_response(content)
        if not parsed:
            return {}

        if "decisions" in parsed:
            return cast(Dict[str, Dict[str, Any]], parsed["decisions"])

        first_key = next(iter(parsed.keys()), "")
        if "/" in first_key or "USDT" in first_key:
            return cast(Dict[str, Dict[str, Any]], parsed)

        return {}

    def _validate_and_fix(
        self,
        symbol: str,
        raw: Dict[str, Any],
        market_data: Dict[str, Any],
    ) -> Optional[TradingDecision]:
        """Validate and fix a single decision."""
        signal = raw.get("signal", "hold").lower()
        confidence = float(raw.get("confidence", 0))

        if signal == "hold":
            return None

        if signal == "close":
            return TradingDecision(
                symbol=symbol,
                signal="close",
                confidence=confidence,
                side="",
                reasoning=raw.get("justification", raw.get("reasoning", "LLM close signal")),
            )

        if signal in ["buy_to_enter", "sell_to_enter"]:
            if confidence < config.MIN_CONFIDENCE_ENTRY:
                return None

        current_price = self._get_price(symbol, market_data)
        if not current_price:
            return None

        side = "short" if signal == "sell_to_enter" else "long"

        stop_loss = self._get_stop_loss(raw, current_price, side)
        take_profit = self._get_take_profit(raw, current_price, side)

        if not self._validate_sl_tp(stop_loss, take_profit, current_price, side):
            stop_loss = self._default_stop_loss(current_price, side)
            take_profit = self._default_take_profit(current_price, side)

        return TradingDecision(
            symbol=symbol,
            signal=signal,
            confidence=confidence,
            side=side,
            stop_loss=Decimal(str(stop_loss)),
            take_profit=Decimal(str(take_profit)),
            size_pct=min(MAX_SIZE_PCT, float(raw.get("size_pct", config.DEFAULT_POSITION_SIZE_PCT))),
            leverage=int(raw.get("leverage", config.DEFAULT_LEVERAGE)),
            reasoning=raw.get("reasoning", raw.get("justification", "")),
        )

    def _get_price(self, symbol: str, market_data: Dict[str, Any]) -> Optional[float]:
        """Extract price from market data."""
        if symbol not in market_data:
            return None
        snapshot = market_data[symbol]
        if hasattr(snapshot, "price"):
            return float(snapshot.price)
        if isinstance(snapshot, dict):
            return float(snapshot.get("price", 0)) or None
        return None

    def _get_stop_loss(self, raw: Dict[str, Any], price: float, side: str) -> float:
        """Get stop loss price from decision or calculate default."""
        sl = raw.get("stop_loss")
        if sl and float(sl) > 0:
            return float(sl)
        return self._default_stop_loss(price, side)

    def _get_take_profit(self, raw: Dict[str, Any], price: float, side: str) -> float:
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
        return price * (1 + sl_pct)

    def _default_take_profit(self, price: float, side: str) -> float:
        """Calculate default take profit."""
        tp_pct = config.DEFAULT_TAKE_PROFIT_PCT
        if side == "long":
            return price * (1 + tp_pct)
        return price * (1 - tp_pct)

    def _validate_sl_tp(self, sl: float, tp: float, price: float, side: str) -> bool:
        """Validate stop loss and take profit positions."""
        if side == "long":
            return sl < price < tp
        return tp < price < sl

    async def _apply_memory_adjustment(
        self, symbol: str, decision: TradingDecision
    ) -> TradingDecision:
        """Apply memory-based confidence adjustment.

        Adjusts LLM confidence based on historical performance with this symbol.
        """
        try:
            # Get confidence adjustment factor from memory
            if self.memory is None:
                return decision
            adjustment = await self.memory.suggest_confidence_adjustment(symbol)

            # Apply adjustment
            original_confidence = decision.confidence
            adjusted_confidence = min(0.99, max(0.01, decision.confidence * adjustment))

            if adjustment != 1.0:
                logger.info(
                    f"[MEMORY] {symbol}: confidence {original_confidence*100:.0f}% "
                    f"→ {adjusted_confidence*100:.0f}% (factor: {adjustment:.2f}x)"
                )

            # Update decision confidence
            decision.confidence = adjusted_confidence
            return decision

        except Exception as e:
            logger.warning(f"[MEMORY] Failed to adjust confidence for {symbol}: {e}")
            # Return unchanged decision on error
            return decision
