import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid

if TYPE_CHECKING:
    from .bot import Bot
    from .trade import Trade


class PositionSide(str, enum.Enum):
    LONG = "long"
    SHORT = "short"


class PositionStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    bot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    side: Mapped[str] = mapped_column(
        SQLEnum(PositionSide, name="position_side_enum", create_constraint=True), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=8), nullable=False)
    leverage: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False, default=Decimal("10.0")
    )
    entry_price: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=2), nullable=False)
    current_price: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=2), nullable=False)
    stop_loss: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=20, scale=2), nullable=True)
    take_profit: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=20, scale=2), nullable=True)
    status: Mapped[str] = mapped_column(
        SQLEnum(PositionStatus, name="position_status_enum", create_constraint=True),
        nullable=False,
        default=PositionStatus.OPEN,
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    bot: Mapped["Bot"] = relationship("Bot", back_populates="positions")
    trades: Mapped[list["Trade"]] = relationship("Trade", back_populates="position")

    @property
    def unrealized_pnl(self) -> Decimal:
        if self.status == PositionStatus.CLOSED:
            return Decimal("0")
        price_diff = self.current_price - self.entry_price
        if self.side == PositionSide.SHORT:
            price_diff = -price_diff
        return price_diff * self.quantity

    @property
    def unrealized_pnl_pct(self) -> Decimal:
        if self.entry_price == 0:
            return Decimal("0")
        return (self.unrealized_pnl / self.entry_value) * Decimal("100")

    @property
    def position_value(self) -> Decimal:
        return self.current_price * self.quantity

    @property
    def entry_value(self) -> Decimal:
        return self.entry_price * self.quantity

    def calculate_realized_pnl(self, exit_price: Decimal, exit_quantity: Decimal) -> Decimal:
        price_diff = exit_price - self.entry_price
        if self.side == PositionSide.SHORT:
            price_diff = -price_diff
        return price_diff * exit_quantity

    def __repr__(self) -> str:
        return f"<Position(id={self.id}, symbol={self.symbol}, side={self.side}, qty={self.quantity}, status={self.status})>"
