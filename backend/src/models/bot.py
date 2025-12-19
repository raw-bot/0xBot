"""Bot model for AI trading agents."""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, Boolean, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid

if TYPE_CHECKING:
    from .llm_decision import LLMDecision
    from .position import Position
    from .trade import Trade
    from .user import User


class BotStatus(str, enum.Enum):
    """Bot status enum."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"


class ModelName(str, enum.Enum):
    """Supported LLM models."""
    CLAUDE_SONNET = "claude-4.5-sonnet"
    GPT4 = "gpt-4"
    DEEPSEEK_CHAT = "deepseek-chat"
    # GEMINI_PRO = "gemini-2.5-pro"  # NOT PLANNED: Focus on DeepSeek for now


class Bot(Base):
    """Bot model for AI trading agents."""

    __tablename__ = "bots"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )

    # Foreign keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Bot configuration
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_name: Mapped[str] = mapped_column(
        String(50),  # Use String instead of Enum - validation done in service
        nullable=False
    )
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=2), nullable=False)
    capital: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=2), nullable=False)

    # Trading symbols (JSON list)
    trading_symbols: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: ["BTC/USDT"]  # Default to BTC only
    )

    # Risk parameters (JSON)
    risk_params: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: {
            "max_position_pct": 0.10,
            "max_drawdown_pct": 0.20,
            "max_trades_per_day": 10,
            "stop_loss_pct": 0.035,      # 3.5% stop loss (default if not specified)
            "take_profit_pct": 0.07       # 7% take profit (default if not specified)
        }
    )

    # Bot status
    status: Mapped[str] = mapped_column(
        SQLEnum(BotStatus, name="bot_status_enum", create_constraint=True),
        nullable=False,
        default=BotStatus.INACTIVE
    )

    # Trading mode
    paper_trading: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="bots")
    positions: Mapped[list["Position"]] = relationship(
        "Position",
        back_populates="bot",
        cascade="all, delete-orphan"
    )
    trades: Mapped[list["Trade"]] = relationship(
        "Trade",
        back_populates="bot",
        cascade="all, delete-orphan"
    )
    decisions: Mapped[list["LLMDecision"]] = relationship(
        "LLMDecision",
        back_populates="bot",
        cascade="all, delete-orphan"
    )

    @property
    def total_realized_pnl(self) -> Decimal:
        """Calculate total realized PnL from all trades."""
        return sum((trade.realized_pnl for trade in self.trades), Decimal("0"))

    @property
    def total_unrealized_pnl(self) -> Decimal:
        """Calculate total unrealized PnL from open positions."""
        from .position import PositionStatus
        return sum(
            (pos.unrealized_pnl for pos in self.positions if pos.status == PositionStatus.OPEN),
            Decimal("0")
        )

    @property
    def total_pnl(self) -> Decimal:
        """Calculate total PnL (realized + unrealized)."""
        return self.total_realized_pnl + self.total_unrealized_pnl

    @property
    def portfolio_value(self) -> Decimal:
        """Calculate current portfolio value (current capital reflects all trades)."""
        return self.capital

    @property
    def return_pct(self) -> Decimal:
        """Calculate portfolio return percentage based on initial capital."""
        if self.initial_capital == 0:
            return Decimal("0")
        return ((self.capital - self.initial_capital) / self.initial_capital) * Decimal("100")

    def __repr__(self) -> str:
        return f"<Bot(id={self.id}, name={self.name}, model={self.model_name}, status={self.status})>"
