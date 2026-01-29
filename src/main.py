"""FastAPI Application - Main entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import get_settings
from src.handlers.webhook import router as webhook_router
from src.services.logfire_config import (
    configure_logfire,
)
from src.services.observability import instrument_fastapi, setup_tracing
from src.utils.logger import get_logger, setup_logging

# Initialize settings early
settings = get_settings()

# Setup logging
setup_logging(settings.log_level)

# Configure Logfire BEFORE creating agents (must be early!)
configure_logfire()

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info(
        "application_starting",
        environment=settings.app_env,
        port=settings.api_port,
    )

    # Setup tracing
    setup_tracing()

    yield

    # Shutdown
    logger.info("application_shutting_down")

    # Note: IdempotencyManager connections are managed per-request
    # No global cleanup needed


# Create FastAPI app
app = FastAPI(
    title="WhatsApp Agent API",
    description="Agente de Atendimento WhatsApp com Pydantic AI",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instrument with OpenTelemetry
instrument_fastapi(app)

# Include routers
app.include_router(webhook_router)


@app.get("/")
async def root() -> dict:
    """Root endpoint.

    Returns:
        Welcome message.
    """
    return {
        "message": "WhatsApp Agent API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Health status with environment info.
    """
    return {
        "status": "healthy",
        "environment": settings.app_env,
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development,
    )
