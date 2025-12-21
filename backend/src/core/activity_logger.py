"""
JSON Activity Logger for 0xBot
Logs all trading activity to a structured JSON file for easy monitoring.
"""

import json
import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal types."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class ActivityLogger:
    """Logger that writes structured JSON entries for easy parsing."""

    LOG_FILE = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "activity.json"
    )

    @classmethod
    def _write_entry(cls, entry: Dict[str, Any]) -> None:
        """Append a JSON entry to the log file."""
        try:
            # Read existing data or create new list
            if os.path.exists(cls.LOG_FILE):
                with open(cls.LOG_FILE, "r") as f:
                    try:
                        data = json.load(f)
                        if not isinstance(data, list):
                            data = []
                    except json.JSONDecodeError:
                        data = []
            else:
                data = []

            # Add new entry
            data.append(entry)

            # Keep only last 500 entries to prevent file from growing too large
            if len(data) > 500:
                data = data[-500:]

            # Write back
            with open(cls.LOG_FILE, "w") as f:
                json.dump(data, f, indent=2, cls=DecimalEncoder)

        except Exception as e:
            print(f"ActivityLogger error: {e}")

    @classmethod
    def log_cycle_start(cls, bot_name: str, symbols: list) -> None:
        """Log the start of a trading cycle."""
        cls._write_entry(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "CYCLE_START",
                "bot": bot_name,
                "symbols": symbols,
            }
        )

    @classmethod
    def log_cycle_end(cls, bot_name: str, duration_seconds: float, decisions: Dict) -> None:
        """Log the end of a trading cycle with summary."""
        cls._write_entry(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "CYCLE_END",
                "bot": bot_name,
                "duration_seconds": round(duration_seconds, 1),
                "decisions_count": len(decisions),
                "decisions_summary": {
                    symbol: {
                        "signal": d.get("signal", "unknown"),
                        "confidence": d.get("confidence", 0),
                    }
                    for symbol, d in decisions.items()
                },
            }
        )

    @classmethod
    def log_trade_entry(
        cls,
        bot_name: str,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        confidence: float,
    ) -> None:
        """Log a new trade entry."""
        cls._write_entry(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "TRADE_ENTRY",
                "bot": bot_name,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "confidence": confidence,
            }
        )

    @classmethod
    def log_trade_exit(
        cls,
        bot_name: str,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        pnl: float,
        reason: str,
    ) -> None:
        """Log a trade exit."""
        cls._write_entry(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "TRADE_EXIT",
                "bot": bot_name,
                "symbol": symbol,
                "side": side,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl": pnl,
                "pnl_pct": (
                    round((exit_price - entry_price) / entry_price * 100, 2) if entry_price else 0
                ),
                "reason": reason,
            }
        )

    @classmethod
    def log_trade_rejected(
        cls,
        bot_name: str,
        symbol: str,
        signal: str,
        confidence: float,
        reason: str,
    ) -> None:
        """Log a rejected trade."""
        cls._write_entry(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "TRADE_REJECTED",
                "bot": bot_name,
                "symbol": symbol,
                "signal": signal,
                "confidence": confidence,
                "reason": reason,
            }
        )

    @classmethod
    def log_portfolio_snapshot(
        cls,
        bot_name: str,
        capital: float,
        positions: list,
        unrealized_pnl: float,
    ) -> None:
        """Log a portfolio snapshot."""
        cls._write_entry(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "PORTFOLIO_SNAPSHOT",
                "bot": bot_name,
                "capital": capital,
                "positions_count": len(positions),
                "positions": (
                    [
                        {
                            "symbol": p.get("symbol", p.symbol if hasattr(p, "symbol") else "?"),
                            "side": p.get("side", p.side if hasattr(p, "side") else "?"),
                            "pnl": p.get("pnl", 0),
                        }
                        for p in positions
                    ]
                    if positions
                    else []
                ),
                "unrealized_pnl": unrealized_pnl,
            }
        )

    @classmethod
    def log_error(cls, bot_name: str, error_type: str, message: str) -> None:
        """Log an error."""
        cls._write_entry(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "ERROR",
                "bot": bot_name,
                "error_type": error_type,
                "message": message,
            }
        )


# Convenience function to get the logger
def get_activity_logger() -> type:
    """Get the ActivityLogger class."""
    return ActivityLogger
