"""LLM Decision model for storing AI analysis and decisions."""

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
    """LLM Decision model for storing AI market analysis and trading decisions."""
    
    __tablename__ = "llm_decisions"
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid
    )
    
    # Foreign key
    bot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bots.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # LLM interaction details
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_decisions: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Token usage and cost tracking
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=6),
        nullable=False,
        default=Decimal("0")
    )
    
    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    
    # Relationships
    bot: Mapped["Bot"] = relationship("Bot", back_populates="decisions")
    
    def __repr__(self) -> str:
        return f"<LLMDecision(id={self.id}, bot_id={self.bot_id}, tokens={self.tokens_used}, timestamp={self.timestamp})>"