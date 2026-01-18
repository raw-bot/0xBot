import uuid

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def generate_uuid() -> uuid.UUID:
    return uuid.uuid4()
