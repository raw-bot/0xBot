import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid


class EquitySnapshot(Base):
    __tablename__ = "equity_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    bot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    equity: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=2), nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=2), nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=2), nullable=False, default=Decimal("0"))

    bot = relationship("Bot", backref="equity_snapshots")

    def __repr__(self) -> str:
        return f"<EquitySnapshot(bot={self.bot_id}, equity={self.equity}, ts={self.timestamp})>"
