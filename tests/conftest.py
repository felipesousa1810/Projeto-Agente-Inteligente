"""Pytest Configuration - Shared fixtures for tests."""

import os
from collections.abc import AsyncGenerator
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

# Set test environment before importing app
os.environ["OPENAI_API_KEY"] = "sk-test-key-for-testing"
os.environ["APP_ENV"] = "development"


@pytest.fixture
def sample_whatsapp_message() -> dict:
    """Sample valid WhatsApp message payload."""
    return {
        "message_id": "3EB0E51D3B4B1A25AA4AA001",
        "from_number": "+5511987654321",
        "body": "Quero agendar para 15 de fevereiro às 14h",
        "timestamp": datetime.now().isoformat(),
    }


@pytest.fixture
def sample_message_schedule() -> dict:
    """Sample message with scheduling intent."""
    return {
        "message_id": "MSG123456789012345678",
        "from_number": "+5511999999999",
        "body": "Quero agendar para dia 20/02/2026 às 10h",
        "timestamp": "2026-01-28T10:30:00Z",
    }


@pytest.fixture
def sample_message_cancel() -> dict:
    """Sample message with cancellation intent."""
    return {
        "message_id": "MSG987654321098765432",
        "from_number": "+5511999999999",
        "body": "Preciso cancelar meu agendamento APPT-ABC123",
        "timestamp": "2026-01-28T11:00:00Z",
    }


@pytest.fixture
def sample_message_faq() -> dict:
    """Sample message with FAQ intent."""
    return {
        "message_id": "MSGFAQ12345678901234",
        "from_number": "+5511888888888",
        "body": "Vocês atendem aos sábados?",
        "timestamp": "2026-01-28T09:00:00Z",
    }


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing FastAPI app."""
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
