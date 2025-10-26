"""API route modules."""

from .auth import router as auth_router
from .bots import router as bots_router

__all__ = ['auth_router', 'bots_router']