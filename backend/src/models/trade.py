"""Trade model for tracking executed trades."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, String, Numeric, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import Base, generate_uuid

if TYPE_CHECKING:
    from .bot import Bot
    from .position import Position


class TradeSide(str, enum.Enum):
    """Trade side enum."""
    BUY = "buy"
    SELL = "sell"


class Trade(Base):
    """Trade model for tracking executed trades."""
    
    __tablename__ = "trades"
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )
    
    # Foreign keys
    bot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bots.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    position_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Trade details
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    side: Mapped[str] = mapped_column(
        SQLEnum(TradeSide, name="trade_side_enum", create_constraint=True),
        nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=8), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=2), nullable=False)
    fees: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=2),
        nullable=False,
        default=Decimal("0")
    )
    
    # PnL (for closing trades)
    realized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=2),
        nullable=False,
        default=Decimal("0")
    )
    
    # Timestamp
    executed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    
    # Relationships
    bot: Mapped["Bot"] = relationship("Bot", back_populates="trades")
    position: Mapped[Optional["Position"]] = relationship("Position", back_populates="trades")
    
    @property
    def total_cost(self) -> Decimal:
        """Calculate total cost including fees."""
        return (self.price * self.quantity) + self.fees
    
    @property
    def net_amount(self) -> Decimal:
        """Calculate net amount after fees."""
        gross = self.price * self.quantity
        return gross - self.fees if self.side == TradeSide.SELL else gross + self.fees
    
    def __repr__(self) -> str:
        return f"<Trade(id={self.id}, symbol={self.symbol}, side={self.side}, qty={self.quantity}, price={self.price})>"