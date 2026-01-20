"""JSON Activity Logger for 0xBot - logs trading activity to structured JSON file."""

import json
import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class ActivityLogger:
    """Logger that writes structured JSON entries for trading activity."""

    LOG_FILE = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "activity.json"
    )
    MAX_ENTRIES = 500

    @classmethod
    def _write_entry(cls, entry: Dict[str, Any]) -> None:
        """Append a JSON entry to the log file."""
        try:
            data = []
            if os.path.exists(cls.LOG_FILE):
                with open(cls.LOG_FILE, "r") as f:
                    try:
                        loaded = json.load(f)
                        if isinstance(loaded, list):
                            data = loaded
                    except json.JSONDecodeError:
                        pass

            data.append(entry)
            if len(data) > cls.MAX_ENTRIES:
                data = data[-cls.MAX_ENTRIES:]

            with open(cls.LOG_FILE, "w") as f:
                json.dump(data, f, indent=2, cls=DecimalEncoder)
        except Exception as e:
            print(f"ActivityLogger error: {e}")

    @classmethod
    def _entry(cls, entry_type: str, bot_name: str, **kwargs: Any) -> None:
        """Create and write a log entry."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": entry_type,
            "bot": bot_name,
            **kwargs
        }
        cls._write_entry(entry)

    @classmethod
    def log_cycle_start(cls, bot_name: str, symbols: list[str]) -> None:
        """Log the start of a trading cycle."""
        cls._entry("CYCLE_START", bot_name, symbols=symbols)

    @classmethod
    def log_cycle_end(cls, bot_name: str, duration_seconds: float, decisions: Dict[str, Any]) -> None:
        """Log the end of a trading cycle with summary."""
        decisions_summary = {
            symbol: {"signal": d.get("signal", "unknown"), "confidence": d.get("confidence", 0)}
            for symbol, d in decisions.items()
        }
        cls._entry(
            "CYCLE_END", bot_name,
            duration_seconds=round(duration_seconds, 1),
            decisions_count=len(decisions),
            decisions_summary=decisions_summary
        )

    @classmethod
    def log_trade_entry(
        cls, bot_name: str, symbol: str, side: str, quantity: float,
        entry_price: float, stop_loss: float, take_profit: float, confidence: float
    ) -> None:
        """Log a new trade entry."""
        cls._entry(
            "TRADE_ENTRY", bot_name,
            symbol=symbol, side=side, quantity=quantity, entry_price=entry_price,
            stop_loss=stop_loss, take_profit=take_profit, confidence=confidence
        )

    @classmethod
    def log_trade_exit(
        cls, bot_name: str, symbol: str, side: str,
        entry_price: float, exit_price: float, pnl: float, reason: str
    ) -> None:
        """Log a trade exit."""
        pnl_pct = round((exit_price - entry_price) / entry_price * 100, 2) if entry_price else 0
        cls._entry(
            "TRADE_EXIT", bot_name,
            symbol=symbol, side=side, entry_price=entry_price,
            exit_price=exit_price, pnl=pnl, pnl_pct=pnl_pct, reason=reason
        )

    @classmethod
    def log_trade_rejected(
        cls, bot_name: str, symbol: str, signal: str, confidence: float, reason: str
    ) -> None:
        """Log a rejected trade."""
        cls._entry(
            "TRADE_REJECTED", bot_name,
            symbol=symbol, signal=signal, confidence=confidence, reason=reason
        )

    @classmethod
    def log_portfolio_snapshot(
        cls, bot_name: str, capital: float, positions: list[Any], unrealized_pnl: float
    ) -> None:
        """Log a portfolio snapshot."""
        position_data = []
        for p in positions or []:
            if isinstance(p, dict):
                position_data.append({
                    "symbol": p.get("symbol", "?"),
                    "side": p.get("side", "?"),
                    "pnl": p.get("pnl", 0)
                })
            else:
                position_data.append({
                    "symbol": getattr(p, "symbol", "?"),
                    "side": getattr(p, "side", "?"),
                    "pnl": getattr(p, "pnl", 0)
                })
        cls._entry(
            "PORTFOLIO_SNAPSHOT", bot_name,
            capital=capital, positions_count=len(positions or []),
            positions=position_data, unrealized_pnl=unrealized_pnl
        )

    @classmethod
    def log_error(cls, bot_name: str, error_type: str, message: str) -> None:
        """Log an error."""
        cls._entry("ERROR", bot_name, error_type=error_type, message=message)


def get_activity_logger() -> type:
    """Get the ActivityLogger class."""
    return ActivityLogger
