"""Handlers package - Request handlers for API endpoints."""

from src.handlers.webhook import router as webhook_router

__all__ = [
    "webhook_router",
]
