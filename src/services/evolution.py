"""Evolution API Client - WhatsApp message operations."""

import httpx

from src.config.settings import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EvolutionAPIClient:
    """Client for Evolution API (WhatsApp integration).

    Handles sending messages and managing WhatsApp connections.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        instance_name: str | None = None,
    ) -> None:
        """Initialize Evolution API client.

        Args:
            base_url: Evolution API base URL.
            api_key: API authentication key.
            instance_name: WhatsApp instance name.
        """
        settings = get_settings()
        self.base_url = (base_url or settings.evolution_api_url).rstrip("/")
        self.api_key = api_key or settings.evolution_api_key
        self.instance_name = instance_name or settings.evolution_instance_name

        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client.

        Returns:
            Async HTTP client.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "apikey": self.api_key,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def send_text_message(
        self,
        to_number: str,
        text: str,
    ) -> dict:
        """Send text message via WhatsApp.

        Args:
            to_number: Recipient phone number in E.164 format.
            text: Message text.

        Returns:
            API response dict.

        Raises:
            httpx.HTTPError: If request fails.
        """
        client = await self._get_client()

        # Normalize phone number (remove + for Evolution API)
        phone = to_number.lstrip("+")

        payload = {
            "number": phone,
            "text": text,
        }

        url = f"/message/sendText/{self.instance_name}"

        logger.info(
            "evolution_send_message",
            to_number=to_number,
            text_length=len(text),
        )

        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()

            logger.info(
                "evolution_message_sent",
                to_number=to_number,
                message_id=result.get("key", {}).get("id"),
            )

            return result

        except httpx.HTTPError as e:
            logger.error(
                "evolution_send_error",
                to_number=to_number,
                error=str(e),
            )
            raise

    async def check_instance_status(self) -> dict:
        """Check WhatsApp instance connection status.

        Returns:
            Instance status dict.
        """
        client = await self._get_client()

        url = f"/instance/connectionState/{self.instance_name}"

        response = await client.get(url)
        response.raise_for_status()

        return response.json()

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


# Global client instance
_evolution_client: EvolutionAPIClient | None = None


def get_evolution_client() -> EvolutionAPIClient:
    """Get or create Evolution API client.

    Returns:
        EvolutionAPIClient instance.
    """
    global _evolution_client
    if _evolution_client is None:
        _evolution_client = EvolutionAPIClient()
    return _evolution_client


async def send_whatsapp_reply(to_number: str, text: str) -> dict:
    """Convenience function to send WhatsApp reply.

    Args:
        to_number: Recipient phone number.
        text: Message text.

    Returns:
        API response.
    """
    client = get_evolution_client()
    return await client.send_text_message(to_number, text)
