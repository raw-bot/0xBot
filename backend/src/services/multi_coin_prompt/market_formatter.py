"""
Market Data Formatter - Formats market data for prompt generation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..fvg_detector_service import get_fvg_detector


class MarketDataFormatter:
    """Formats market data for LLM prompt generation."""

    COIN_MAPPING = {
        "BTC/USDT": "Bitcoin",
        "ETH/USDT": "Ethereum",
        "SOL/USDT": "Solana",
        "BNB/USDT": "BNB",
        "XRP/USDT": "XRP",
    }

    def __init__(self) -> None:
        """Initialize MarketDataFormatter."""
        self.coin_mapping = self.COIN_MAPPING
        self.fvg_detector = get_fvg_detector()

    def format_market_data(self, symbols: List[str], all_coins_data: dict[str, dict[str, Any]]) -> str:
        """Format all market data into dashboard text."""
        lines = []
        for symbol in symbols:
            if symbol not in all_coins_data:
                continue
            data = all_coins_data[symbol]
            coin_name = self.coin_mapping.get(symbol, symbol.split("/")[0])
            current = data.get("current_price", 0)
            funding = data.get("funding_rate", 0)
            oi = data.get("open_interest", {}).get("latest", 0)
            tech_1h = data.get("technical_indicators", {}).get("1h", {})
            high_4h, low_4h = self._get_price_range(data, 48)

            lines.extend([
                f"### {coin_name} ({symbol})",
                f"- **Price**: ${current:,.2f} (4H Range: ${low_4h:,.2f} - ${high_4h:,.2f})",
                f"- **Net Funding**: {funding:+.4f}% / 8h",
                f"- **Open Interest**: {oi:,.0f}",
                f"- **RSI(14)**: {tech_1h.get('rsi14', 50):.1f} | **EMA20**: ${tech_1h.get('ema20', 0):,.2f} | **EMA50**: ${tech_1h.get('ema50', 0):,.2f}",
                f"- **Vol Ratio**: {self._calc_volume_ratio(data):.2f}x average",
                "",
            ])

        return "\n".join(lines)

    def format_fvg_analysis(self, symbols: List[str], all_coins_data: dict[str, dict[str, Any]]) -> str:
        """Format Fair Value Gap analysis for all symbols."""
        lines = []
        for symbol in symbols:
            if symbol not in all_coins_data:
                continue
            data = all_coins_data[symbol]
            fvg_text = self._analyze_fvg(symbol, data)
            lines.append(fvg_text)

        return "\n".join(lines)

    def format_positions(self, all_positions: list[Any]) -> str:
        """Format all positions for prompt."""
        if not all_positions:
            return "### No Open Positions"

        lines = []
        for pos in all_positions:
            lines.extend(self._format_position(pos))

        return "\n".join(lines)

    def _format_position(self, pos: Any) -> list[str]:
        """Format a single position for the prompt."""
        lines = []
        if hasattr(pos, "symbol"):
            coin = self.coin_mapping.get(pos.symbol, pos.symbol)
            side = getattr(pos, "side", "UNKNOWN").upper()
            qty = float(getattr(pos, "quantity", 0))
            entry = float(getattr(pos, "entry_price", 0))
            current = float(getattr(pos, "current_price", entry))
            sl = float(getattr(pos, "stop_loss", 0))
            tp = float(getattr(pos, "take_profit", 0))

            if side == "LONG":
                pnl = (current - entry) * qty
                sl_dist = ((sl - current) / current * 100) if current > 0 else 0
                tp_dist = ((tp - current) / current * 100) if current > 0 else 0
            else:
                pnl = (entry - current) * qty
                sl_dist = ((current - sl) / current * 100) if current > 0 else 0
                tp_dist = ((current - tp) / current * 100) if current > 0 else 0
            pnl_pct = (pnl / (entry * qty) * 100) if entry * qty > 0 else 0

            hold_hours = 0.0
            if hasattr(pos, "opened_at") and pos.opened_at:
                hold_hours = (datetime.utcnow() - pos.opened_at).total_seconds() / 3600

            lines.extend([
                f"**{coin}** ({pos.symbol}):",
                f"  - Side: {side} | Qty: {qty:.6f}",
                f"  - Entry: ${entry:,.2f} -> Current: ${current:,.2f}",
                f"  - **Unrealized P&L: ${pnl:+,.2f} ({pnl_pct:+.2f}%)**",
                f"  - SL: ${sl:,.2f} ({sl_dist:+.1f}% away) | TP: ${tp:,.2f} ({tp_dist:+.1f}% away)",
                f"  - Hold time: {hold_hours:.1f} hours",
                "  - **DECIDE: HOLD or CLOSE this position?**",
                "",
            ])
        elif isinstance(pos, dict):
            symbol = pos.get("symbol", "UNKNOWN")
            coin = self.coin_mapping.get(symbol, symbol)
            lines.append(f"- **{coin}**: {pos.get('side', 'LONG').upper()} @ ${pos.get('entry_price', 0):,.2f}")

        return lines

    def _get_price_at_offset(self, market_data: dict[str, Any], offset: int) -> Any:
        """Get price from series at offset candles back, or current price if unavailable."""
        current = market_data.get("current_price", 0)
        price_series = market_data.get("price_series", [])
        return price_series[-offset] if len(price_series) > offset else current

    def _get_price_range(self, market_data: dict[str, Any], lookback: int) -> tuple[Any, Any]:
        """Get (high, low) from recent price series."""
        current = market_data.get("current_price", 0)
        price_series = market_data.get("price_series", [])
        recent = price_series[-lookback:] if len(price_series) > lookback else price_series
        if not recent:
            return current, current
        return max(recent), min(recent)

    def _calc_volume_ratio(self, market_data: dict[str, Any]) -> float:
        """Calculate current volume vs average."""
        tech = market_data.get("technical_indicators", {}).get("1h", {})
        avg_vol = tech.get("avg_volume", 1)
        result = tech.get("volume", 0) / avg_vol if avg_vol > 0 else 1.0
        return float(result)

    def _analyze_fvg(self, symbol: str, market_data: dict[str, Any]) -> str:
        """Analyze Fair Value Gaps for a symbol."""
        ohlcv_data = market_data.get("ohlcv", [])
        if not ohlcv_data or len(ohlcv_data) < 3:
            return f"### FVG Analysis ({symbol})\nInsufficient data for FVG detection.\n"

        candles = [
            {
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close),
                "timestamp": c.datetime.isoformat(),
            }
            for c in ohlcv_data
        ]

        price_series = market_data.get("price_series", [])
        if price_series and len(price_series) > 20:
            range_high, range_low = max(price_series[-20:]), min(price_series[-20:])
        else:
            range_high = max(c["high"] for c in candles[-20:])
            range_low = min(c["low"] for c in candles[-20:])

        self.fvg_detector.detect_fvgs(symbol, candles, market_data.get("timeframe", "1h"))
        current_price = market_data.get("current_price", 0)
        if current_price > 0:
            self.fvg_detector.update_mitigation(symbol, current_price)

        return self.fvg_detector.format_for_prompt(symbol, range_high, range_low)
