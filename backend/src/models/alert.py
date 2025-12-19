"""Alert model for user notifications."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid

if TYPE_CHECKING:
    from .bot import Bot
    from .user import User


class AlertType(str, enum.Enum):
    """Alert type enum."""
    TRADE = "trade"
    PNL = "pnl"
    RISK = "risk"
    ERROR = "error"


class AlertSeverity(str, enum.Enum):
    """Alert severity enum."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alert(Base):
    """Alert model for storing user notifications."""
    
    __tablename__ = "alerts"
    
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
    
    bot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bots.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Alert details
    type: Mapped[str] = mapped_column(
        SQLEnum(AlertType, name="alert_type_enum", create_constraint=True),
        nullable=False
    )
    severity: Mapped[str] = mapped_column(
        SQLEnum(AlertSeverity, name="alert_severity_enum", create_constraint=True),
        nullable=False
    )
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    
    # Read status
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="alerts")
    
    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, type={self.type}, severity={self.severity}, read={self.read})>"