"""Structured logging configuration."""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import Request


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for prettier console output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Level colors
    DEBUG = "\033[36m"      # Cyan
    INFO = "\033[32m"       # Green
    WARNING = "\033[33m"    # Yellow
    ERROR = "\033[31m"      # Red
    CRITICAL = "\033[35m"   # Magenta
    
    # Component colors
    TIMESTAMP = "\033[90m"  # Gray
    LOGGER = "\033[94m"     # Light blue
    LOCATION = "\033[90m"   # Gray
    KEY = "\033[96m"        # Light cyan


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    
    Outputs logs in JSON format for easier parsing and analysis.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record
            
        Returns:
            JSON-formatted log string
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add request ID if available
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        # Add user ID if available
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        
        # Add extra fields
        if hasattr(record, "extra"):
            log_data["extra"] = record.extra
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add file location
        log_data["location"] = {
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName
        }
        
        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable formatter with colors and better structure.
    
    Perfect for development and debugging.
    """
    
    def __init__(self, use_colors: bool = True):
        """
        Initialize formatter.
        
        Args:
            use_colors: Whether to use ANSI colors
        """
        super().__init__()
        self.use_colors = use_colors
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record in a human-readable way.
        
        Args:
            record: Log record
            
        Returns:
            Formatted log string
        """
        # Color setup
        if self.use_colors:
            level_colors = {
                "DEBUG": Colors.DEBUG,
                "INFO": Colors.INFO,
                "WARNING": Colors.WARNING,
                "ERROR": Colors.ERROR,
                "CRITICAL": Colors.CRITICAL
            }
            level_color = level_colors.get(record.levelname, Colors.RESET)
            reset = Colors.RESET
            dim = Colors.DIM
            bold = Colors.BOLD
            timestamp_color = Colors.TIMESTAMP
            logger_color = Colors.LOGGER
            key_color = Colors.KEY
        else:
            level_color = reset = dim = bold = timestamp_color = logger_color = key_color = ""
        
        # Format timestamp (only time, no milliseconds for cleaner look)
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        
        # Abbreviate logger names for cleaner output
        logger_abbrev = {
            "trading_engine_service": "🤖 BOT",
            "trade_executor_service": "💰 TRADE",
            "market_data_service": "📊 DATA",
            "market_analysis_service": "📈 ANALYSIS",
            "llm_prompt_service": "🧠 LLM",
            "position_service": "📍 POSITION",
            "risk_manager_service": "⚠️  RISK",
            "bot_service": "🔧 SERVICE",
            "exchange_client": "🔗 EXCHANGE",
            "indicator_service": "📉 INDICATOR",
        }
        
        # Extract short logger name (last part)
        logger_parts = record.name.split(".")
        short_logger = logger_parts[-1] if logger_parts else record.name
        
        # Use abbreviation or show only for warnings/errors
        if record.levelno >= logging.WARNING:
            # Show full context for errors/warnings
            aligned_logger = logger_abbrev.get(short_logger, f"⚡ {short_logger[:8].upper()}")
            log_line_prefix = f"{timestamp_color}{timestamp}{reset} | {level_color}{aligned_logger}{reset} | "
        else:
            # For INFO/DEBUG, just timestamp
            log_line_prefix = f"{timestamp_color}{timestamp}{reset} | "
        
        # Color based on level
        if record.levelno >= logging.ERROR:
            msg_color = Colors.ERROR
        elif record.levelno >= logging.WARNING:
            msg_color = Colors.WARNING
        else:
            msg_color = ""
        
        # Build main log line
        log_line = f"{log_line_prefix}{msg_color}{record.getMessage()}{reset}"
        
        # Add extra fields if present
        extras = []
        
        if hasattr(record, "request_id"):
            extras.append(f"{key_color}request_id{reset}={record.request_id}")
        
        if hasattr(record, "user_id"):
            extras.append(f"{key_color}user_id{reset}={record.user_id}")
        
        if hasattr(record, "extra") and record.extra:
            for key, value in record.extra.items():
                # Format value based on type
                if isinstance(value, (int, float)):
                    formatted_value = f"{value}"
                elif isinstance(value, str):
                    formatted_value = f'"{value}"'
                else:
                    formatted_value = str(value)
                extras.append(f"{key_color}{key}{reset}={formatted_value}")
        
        if extras:
            log_line += f"\n  {dim}└─ {' · '.join(extras)}{reset}"
        
        # Add exception if present
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            log_line += f"\n{Colors.ERROR}{exc_text}{reset}"
        
        # Add location in dim for debug
        if record.levelno <= logging.DEBUG:
            location = f"{record.filename}:{record.lineno} in {record.funcName}()"
            log_line += f"\n  {dim}📍 {location}{reset}"
        
        return log_line


class NoiseFilter(logging.Filter):
    """
    Filter out noisy/repetitive log messages.
    
    Filters out common patterns like "Fetching", "Created", etc.
    """
    
    def __init__(self):
        """Initialize filter with patterns to exclude."""
        super().__init__()
        self.excluded_patterns = [
            "Fetching",
            "Created order",
            "Closing database connection",
            "Opening database connection",
            "Connection pool",
            "HTTP Request:",
            "HTTP Response:",
        ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Determine if record should be logged.
        
        Args:
            record: Log record
            
        Returns:
            True if should be logged, False otherwise
        """
        message = record.getMessage()
        
        # Check if message contains any excluded pattern
        for pattern in self.excluded_patterns:
            if pattern.lower() in message.lower():
                return False
        
        return True


class RequestLogger:
    """
    Logger wrapper with request context.
    
    Automatically includes request ID and user ID in logs.
    """
    
    def __init__(self, logger: logging.Logger, request: Optional[Request] = None):
        """
        Initialize request logger.
        
        Args:
            logger: Base logger
            request: Optional request object
        """
        self.logger = logger
        self.request = request
    
    def _add_context(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add request context to log extras."""
        context = extra or {}
        
        if self.request:
            if hasattr(self.request.state, "request_id"):
                context["request_id"] = self.request.state.request_id
            
            if hasattr(self.request.state, "user_id"):
                context["user_id"] = self.request.state.user_id
        
        return context
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message."""
        self.logger.debug(message, extra=self._add_context(extra))
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log info message."""
        self.logger.info(message, extra=self._add_context(extra))
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log warning message."""
        self.logger.warning(message, extra=self._add_context(extra))
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log error message."""
        self.logger.error(message, extra=self._add_context(extra))
    
    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log critical message."""
        self.logger.critical(message, extra=self._add_context(extra))


def setup_logging(log_level: str = "INFO", use_json: bool = False) -> None:
    """
    Configure application logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: Use JSON formatter instead of human-readable (default: False for dev)
    """
    # Check environment variable for format preference
    log_format = os.getenv("LOG_FORMAT", "human" if not use_json else "json").lower()
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Add noise filter to reduce clutter
    noise_filter = NoiseFilter()
    console_handler.addFilter(noise_filter)
    
    # Choose formatter based on configuration
    if log_format == "json":
        formatter = JSONFormatter()
    else:
        # Use human-readable formatter by default (better for development)
        use_colors = sys.stdout.isatty()  # Auto-detect if terminal supports colors
        formatter = HumanReadableFormatter(use_colors=use_colors)
    
    console_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Silence noisy loggers - keep only important messages
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def get_request_logger(name: str, request: Optional[Request] = None) -> RequestLogger:
    """
    Get request-aware logger.
    
    Args:
        name: Logger name
        request: Optional request object
        
    Returns:
        Request logger instance
    """
    logger = logging.getLogger(name)
    return RequestLogger(logger, request)


# Initialize logging on module import
setup_logging()