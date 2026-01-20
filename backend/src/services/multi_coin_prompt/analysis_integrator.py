"""
Analysis Integrator - Integrates technical and sentiment analysis, parses LLM responses.
"""

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AnalysisIntegrator:
    """Integrates analysis components and parses LLM responses."""

    def __init__(self) -> None:
        """Initialize AnalysisIntegrator."""
        pass

    def prepare_price_data(self, all_coins_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Prepare price data structure for narrative analysis."""
        price_data = {}
        for symbol, data in all_coins_data.items():
            current = data.get("current_price", 0)
            price_1h_ago = self._get_price_at_offset(data, 12)
            change_pct = ((current - price_1h_ago) / price_1h_ago * 100) if price_1h_ago > 0 else 0
            price_data[symbol] = {
                "current_price": current,
                "price_1h_ago": price_1h_ago,
                "change_pct": change_pct,
                "volume_ratio": self._calc_volume_ratio(data),
            }
        return price_data

    def extract_position_symbols(self, all_positions: list[Any]) -> set[str]:
        """Extract symbols from all positions."""
        position_symbols = {
            pos.symbol if hasattr(pos, "symbol") else pos.get("symbol")
            for pos in all_positions
            if hasattr(pos, "symbol") or (isinstance(pos, dict) and "symbol" in pos)
        }
        return position_symbols

    def parse_multi_coin_response(
        self, response_text: str, target_symbols: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Parse LLM response for multi-coin decisions."""
        target_symbols = target_symbols or []

        try:
            data = self._extract_json(response_text)
            if not data:
                logger.error(f"Could not find JSON in response: {response_text[:100]}...")
                return self._create_fallback_response(target_symbols, "JSON parse error")

            decisions = data.get("decisions", data)
            missing = [s for s in target_symbols if s not in decisions]
            if missing:
                logger.warning(f"LLM response missing {len(missing)} symbols: {missing}")
                for sym in missing:
                    decisions[sym] = {"signal": "hold", "confidence": 0.50, "justification": "Missing from response"}
                logger.info(f"Auto-filled {len(missing)} missing symbols with HOLD")

            return decisions if "decisions" not in data else data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return self._create_fallback_response(target_symbols, "JSON parse error")
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return self._create_fallback_response(target_symbols, "Parse error")

    def get_decision_for_symbol(self, symbol: str, response_text: str) -> dict[str, Any]:
        """Extract decision for a specific symbol from LLM response."""
        default = {"action": "hold", "confidence": 0.6, "reasoning": f"Default HOLD for {symbol}"}
        if not response_text.strip():
            return {**default, "reasoning": f"Empty LLM response for {symbol}"}

        try:
            decisions = self.parse_multi_coin_response(response_text, [symbol])
            if symbol not in decisions:
                return {**default, "reasoning": f"Symbol {symbol} not in response"}
            d = decisions[symbol]
            return {
                "action": d.get("signal", "hold"),
                "confidence": d.get("confidence", 0.6),
                "reasoning": d.get("justification", d.get("reasoning", f"Decision for {symbol}")),
            }
        except Exception as e:
            logger.warning(f"Error parsing {symbol}: {e}")
            return {**default, "reasoning": f"Parsing error for {symbol}"}

    def parse_simple_response(self, response_text: str, symbol: str, current_market_price: float = 0) -> dict[str, Any]:
        """Compatibility method for SimpleLLMPromptService interface."""
        return self.get_decision_for_symbol(symbol, response_text)

    def _get_price_at_offset(self, market_data: dict[str, Any], offset: int) -> float:
        """Get price from series at offset candles back, or current price if unavailable."""
        current = market_data.get("current_price", 0)
        price_series = market_data.get("price_series", [])
        if len(price_series) > offset:
            val = price_series[-offset]
            if isinstance(val, (int, float)):
                return float(val)
        return float(current)

    def _calc_volume_ratio(self, market_data: dict[str, Any]) -> float:
        """Calculate current volume vs average."""
        tech = market_data.get("technical_indicators", {}).get("1h", {})
        avg_vol = tech.get("avg_volume", 1)
        return tech.get("volume", 0) / avg_vol if avg_vol > 0 else 1.0

    def _extract_json(self, text: str) -> Optional[dict[str, Any]]:
        """Extract JSON from response text."""
        text = text.strip()
        if text.startswith("{"):
            return json.loads(text)  # type: ignore[no-any-return]
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start:end + 1])  # type: ignore[no-any-return]
        return None

    def _create_fallback_response(self, symbols: list[str], reason: str = "default HOLD") -> dict[str, dict[str, Any]]:
        """Create fallback HOLD response for all symbols."""
        return {
            symbol: {"signal": "hold", "confidence": 0.50, "justification": reason}
            for symbol in symbols
        }
