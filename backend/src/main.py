"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import config
from .core.database import close_db
from .core.di_container import get_container
from .core.logging_config import configure_structured_logging
from .core.redis_client import close_redis, init_redis
from .core.scheduler import start_scheduler, stop_scheduler
from .middleware.error_handler import ErrorHandlerMiddleware
from .middleware.query_profiling import QueryProfilingMiddleware
from .middleware.security import RequestIDMiddleware, SecurityHeadersMiddleware
from .routes import auth_router, bots_router
from .routes.dashboard import router as dashboard_router

# Load environment variables from .env file
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    print("🚀 Starting AI Trading Agent API...")

    # Initialize DI container
    container = get_container()
    print("✅ DI container initialized")

    # Configure structured logging
    configure_structured_logging()
    print("✅ Structured logging configured")

    # Validate configuration
    is_valid, errors = config.validate_config()
    if not is_valid:
        error_msg = f"Configuration validation failed:\n" + "\n".join(errors)
        print(f"❌ {error_msg}")
        raise RuntimeError(error_msg)
    print("✅ Configuration validated")

    # Initialize Redis
    await init_redis()
    print("✅ Redis connected")

    # Initialize database
    print("✅ Database connected")

    # Startup DI container services
    await container.startup()
    print("✅ DI container services started")

    # Start bot scheduler
    await start_scheduler()
    print("✅ Bot scheduler started")

    print("✅ Application ready")
    print("📊 Access API docs at http://localhost:8020/docs")

    yield

    # Shutdown
    print("🛑 Shutting down AI Trading Agent API...")

    # Stop scheduler first
    await stop_scheduler()
    print("✅ Bot scheduler stopped")

    # Shutdown DI container services
    await container.shutdown()
    print("✅ DI container services stopped")

    # Close connections
    await close_db()
    await close_redis()
    print("✅ Database connections closed")
    print("👋 Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="AI Trading Agent API",
    description="Autonomous AI-powered cryptocurrency trading platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# Configure CORS - allow all for file:// dashboard access
CORS_ORIGINS = ["*"]  # Allow all origins including file://

# Add middlewares (order matters - first added is executed last)
app.add_middleware(QueryProfilingMiddleware)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])

app.include_router(bots_router, prefix="/api", tags=["Bots"])

# Public dashboard API (no auth required)
app.include_router(dashboard_router, prefix="/api", tags=["Dashboard"])


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns:
        Status information
    """
    return {"status": "healthy", "service": "AI Trading Agent API", "version": "1.0.0"}


# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> dict:
    """
    Root endpoint.

    Returns:
        Welcome message
    """
    return {"message": "AI Trading Agent API", "docs": "/docs", "health": "/health"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8020, reload=True, log_level="info")
