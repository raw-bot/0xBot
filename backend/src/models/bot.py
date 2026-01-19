import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid
from ..config import TRADING_CONFIG, LIMITS_CONFIG

if TYPE_CHECKING:
    from .llm_decision import LLMDecision
    from .position import Position
    from .trade import Trade
    from .user import User


class BotStatus(str, enum.Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"


class ModelName(str, enum.Enum):
    CLAUDE_SONNET = "claude-4.5-sonnet"
    GPT4 = "gpt-4"
    DEEPSEEK_CHAT = "deepseek-chat"


class Bot(Base):
    __tablename__ = "bots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=2), nullable=False)
    capital: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=2), nullable=False)
    trading_symbols: Mapped[list] = mapped_column(JSON, nullable=False, default=lambda: ["BTC/USDT"])
    risk_params: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: {
            "max_position_pct": TRADING_CONFIG["DEFAULT_BOT_MAX_POSITION_PCT"],
            "max_drawdown_pct": LIMITS_CONFIG["BOT_MAX_DRAWDOWN_PCT"],
            "max_trades_per_day": LIMITS_CONFIG["BOT_MAX_TRADES_PER_DAY"],
            "stop_loss_pct": TRADING_CONFIG["DEFAULT_STOP_LOSS_PCT"],
            "take_profit_pct": TRADING_CONFIG["DEFAULT_TAKE_PROFIT_PCT"],
        },
    )
    status: Mapped[str] = mapped_column(
        SQLEnum(BotStatus, name="bot_status_enum", create_constraint=True),
        nullable=False,
        default=BotStatus.INACTIVE,
    )
    paper_trading: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="bots")
    positions: Mapped[list["Position"]] = relationship(
        "Position", back_populates="bot", cascade="all, delete-orphan"
    )
    trades: Mapped[list["Trade"]] = relationship(
        "Trade", back_populates="bot", cascade="all, delete-orphan"
    )
    decisions: Mapped[list["LLMDecision"]] = relationship(
        "LLMDecision", back_populates="bot", cascade="all, delete-orphan"
    )

    @property
    def total_realized_pnl(self) -> Decimal:
        return sum((trade.realized_pnl for trade in self.trades), Decimal("0"))

    @property
    def total_unrealized_pnl(self) -> Decimal:
        from .position import PositionStatus
        return sum(
            (pos.unrealized_pnl for pos in self.positions if pos.status == PositionStatus.OPEN),
            Decimal("0"),
        )

    @property
    def total_pnl(self) -> Decimal:
        return self.total_realized_pnl + self.total_unrealized_pnl

    @property
    def portfolio_value(self) -> Decimal:
        return self.capital

    @property
    def return_pct(self) -> Decimal:
        if self.initial_capital == 0:
            return Decimal("0")
        return ((self.capital - self.initial_capital) / self.initial_capital) * Decimal("100")

    def __repr__(self) -> str:
        return f"<Bot(id={self.id}, name={self.name}, model={self.model_name}, status={self.status})>"
