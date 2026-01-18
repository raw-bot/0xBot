import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid

if TYPE_CHECKING:
    from .bot import Bot


class LLMDecision(Base):
    __tablename__ = "llm_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    bot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_decisions: Mapped[dict] = mapped_column(JSON, nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=6), nullable=False, default=Decimal("0"))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    bot: Mapped["Bot"] = relationship("Bot", back_populates="decisions")

    def __repr__(self) -> str:
        return f"<LLMDecision(id={self.id}, bot_id={self.bot_id}, tokens={self.tokens_used}, timestamp={self.timestamp})>"
