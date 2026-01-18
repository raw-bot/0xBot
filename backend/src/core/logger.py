"""Structured logging configuration."""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Request


class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    DEBUG = "\033[36m"
    INFO = "\033[32m"
    WARNING = "\033[33m"
    ERROR = "\033[31m"
    CRITICAL = "\033[35m"
    TIMESTAMP = "\033[90m"
    LOGGER = "\033[94m"
    KEY = "\033[96m"


LEVEL_COLORS = {
    "DEBUG": Colors.DEBUG,
    "INFO": Colors.INFO,
    "WARNING": Colors.WARNING,
    "ERROR": Colors.ERROR,
    "CRITICAL": Colors.CRITICAL,
}

LOGGER_ABBREVIATIONS = {
    "trading_engine_service": "BOT",
    "trade_executor_service": "TRADE",
    "market_data_service": "DATA",
    "market_analysis_service": "ANALYSIS",
    "llm_prompt_service": "LLM",
    "position_service": "POSITION",
    "risk_manager_service": "RISK",
    "bot_service": "SERVICE",
    "exchange_client": "EXCHANGE",
    "indicator_service": "INDICATOR",
}


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for attr in ("request_id", "user_id"):
            if hasattr(record, attr):
                log_data[attr] = getattr(record, attr)

        if hasattr(record, "extra"):
            log_data["extra"] = record.extra

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        log_data["location"] = {
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
        }

        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter with optional colors."""

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        c = Colors if self.use_colors else type("NoColors", (), {k: "" for k in dir(Colors) if not k.startswith("_")})()

        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        level_color = LEVEL_COLORS.get(record.levelname, c.RESET) if self.use_colors else ""

        short_logger = record.name.split(".")[-1]

        if record.levelno >= logging.WARNING:
            abbrev = LOGGER_ABBREVIATIONS.get(short_logger, short_logger[:8].upper())
            prefix = f"{c.TIMESTAMP}{timestamp}{c.RESET} | {level_color}{abbrev}{c.RESET} | "
        else:
            prefix = f"{c.TIMESTAMP}{timestamp}{c.RESET} | "

        msg_color = c.ERROR if record.levelno >= logging.ERROR else (c.WARNING if record.levelno >= logging.WARNING else "")
        log_line = f"{prefix}{msg_color}{record.getMessage()}{c.RESET}"

        # Add extras
        extras = []
        for attr in ("request_id", "user_id"):
            if hasattr(record, attr):
                extras.append(f"{c.KEY}{attr}{c.RESET}={getattr(record, attr)}")

        if hasattr(record, "extra") and record.extra:
            for key, value in record.extra.items():
                formatted = f'"{value}"' if isinstance(value, str) else str(value)
                extras.append(f"{c.KEY}{key}{c.RESET}={formatted}")

        if extras:
            log_line += f"\n  {c.DIM}|- {' . '.join(extras)}{c.RESET}"

        if record.exc_info:
            log_line += f"\n{c.ERROR}{self.formatException(record.exc_info)}{c.RESET}"

        if record.levelno <= logging.DEBUG:
            log_line += f"\n  {c.DIM}@ {record.filename}:{record.lineno} in {record.funcName}(){c.RESET}"

        return log_line


class NoiseFilter(logging.Filter):
    """Filter out noisy log messages."""

    EXCLUDED = [
        "fetching", "created order", "closing database", "opening database",
        "connection pool", "http request:", "http response:",
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage().lower()
        return not any(pattern in message for pattern in self.EXCLUDED)


class RequestLogger:
    """Logger wrapper with request context."""

    def __init__(self, logger: logging.Logger, request: Optional[Request] = None):
        self.logger = logger
        self.request = request

    def _add_context(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = extra or {}
        if self.request:
            for attr in ("request_id", "user_id"):
                if hasattr(self.request.state, attr):
                    context[attr] = getattr(self.request.state, attr)
        return context

    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        self.logger.debug(message, extra=self._add_context(extra))

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        self.logger.info(message, extra=self._add_context(extra))

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        self.logger.warning(message, extra=self._add_context(extra))

    def error(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        self.logger.error(message, extra=self._add_context(extra))

    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        self.logger.critical(message, extra=self._add_context(extra))


def setup_logging(log_level: str = "INFO", use_json: bool = False) -> None:
    """Configure application logging."""
    log_format = os.getenv("LOG_FORMAT", "human" if not use_json else "json").lower()
    level = getattr(logging, log_level.upper())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    noise_filter = NoiseFilter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.addFilter(noise_filter)

    if log_format == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(HumanReadableFormatter(use_colors=sys.stdout.isatty()))

    root_logger.addHandler(console_handler)

    # File handlers
    project_root = Path(__file__).parent.parent.parent.parent
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)

    # JSON log file
    json_handler = logging.FileHandler(str(log_dir / "bot.log"))
    json_handler.setLevel(level)
    json_handler.addFilter(noise_filter)
    json_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(json_handler)

    # Human-readable log file
    readable_handler = logging.FileHandler(str(log_dir / "bot_console.log"))
    readable_handler.setLevel(level)
    readable_handler.addFilter(noise_filter)
    readable_handler.setFormatter(HumanReadableFormatter(use_colors=False))
    root_logger.addHandler(readable_handler)

    # Silence noisy loggers
    for name in ["uvicorn.access", "uvicorn.error", "httpx", "httpcore",
                 "urllib3", "asyncio", "sqlalchemy.engine", "sqlalchemy.pool"]:
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get logger instance."""
    return logging.getLogger(name)


def get_request_logger(name: str, request: Optional[Request] = None) -> RequestLogger:
    """Get request-aware logger."""
    return RequestLogger(logging.getLogger(name), request)


setup_logging()
