"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.database import close_db
from .core.redis_client import init_redis, close_redis
from .core.scheduler import start_scheduler, stop_scheduler
from .middleware.error_handler import ErrorHandlerMiddleware
from .middleware.security import SecurityHeadersMiddleware, RequestIDMiddleware
from .routes import auth_router, bots_router

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
    
    # Initialize Redis
    await init_redis()
    print("✅ Redis connected")
    
    # Initialize database
    print("✅ Database connected")
    
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
    lifespan=lifespan
)


# Configure CORS
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173"  # React dev servers
).split(",")

# Add middlewares (order matters - first added is executed last)
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
app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"]
)

app.include_router(
    bots_router,
    prefix="/api",
    tags=["Bots"]
)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """
    Health check endpoint.
    
    Returns:
        Status information
    """
    return {
        "status": "healthy",
        "service": "AI Trading Agent API",
        "version": "1.0.0"
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> dict:
    """
    Root endpoint.
    
    Returns:
        Welcome message
    """
    return {
        "message": "AI Trading Agent API",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8020,
        reload=True,
        log_level="info"
    )