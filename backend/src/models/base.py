"""Base model configuration for SQLAlchemy."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""
    
    pass


def generate_uuid() -> uuid.UUID:
    """Generate a new UUID for primary keys."""
    return uuid.uuid4()