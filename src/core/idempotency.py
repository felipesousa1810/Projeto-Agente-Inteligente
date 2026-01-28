"""Idempotency Manager - Ensures each message is processed only once."""

from typing import Any

import redis.asyncio as redis

from src.utils.logger import get_logger

logger = get_logger(__name__)


class IdempotencyManager:
    """Manages idempotency using Redis to prevent duplicate message processing.

    Each message_id is stored in Redis with a TTL. If a message_id already exists,
    the message is considered a duplicate and should not be processed again.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        ttl_seconds: int = 86400,  # 24 hours
        prefix: str = "idempotency:",
    ) -> None:
        """Initialize the IdempotencyManager.

        Args:
            redis_url: Redis connection URL
            ttl_seconds: Time-to-live for idempotency keys (default: 24 hours)
            prefix: Prefix for Redis keys
        """
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self.prefix = prefix
        self._client: redis.Redis | None = None

    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            try:
                self._client = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                # Test connection
                await self._client.ping()
                logger.info("redis_connected", url=self.redis_url)
            except Exception as e:
                logger.warning(
                    "redis_connection_failed",
                    error=str(e),
                    message="Operating without Redis - idempotency disabled",
                )
                raise
        return self._client

    def _make_key(self, message_id: str) -> str:
        """Create a Redis key for the given message_id."""
        return f"{self.prefix}{message_id}"

    async def check_duplicate(self, message_id: str) -> bool:
        """Check if a message has already been processed.

        Args:
            message_id: The unique message identifier

        Returns:
            True if this is a duplicate (already processed), False otherwise
        """
        try:
            client = await self._get_client()
            key = self._make_key(message_id)
            exists = await client.exists(key)
            if exists:
                logger.info("duplicate_message_detected", message_id=message_id)
            return bool(exists)
        except Exception as e:
            logger.warning(
                "idempotency_check_failed",
                message_id=message_id,
                error=str(e),
            )
            # If Redis is unavailable, allow processing (fail open)
            return False

    async def mark_processed(
        self,
        message_id: str,
        result: dict[str, Any] | None = None,
    ) -> bool:
        """Mark a message as processed.

        Args:
            message_id: The unique message identifier
            result: Optional result data to store

        Returns:
            True if marked successfully, False otherwise
        """
        try:
            client = await self._get_client()
            key = self._make_key(message_id)

            # Store with TTL
            import json

            value = json.dumps(result) if result else "processed"
            await client.setex(key, self.ttl_seconds, value)

            logger.info(
                "message_marked_processed",
                message_id=message_id,
                ttl_seconds=self.ttl_seconds,
            )
            return True
        except Exception as e:
            logger.warning(
                "mark_processed_failed",
                message_id=message_id,
                error=str(e),
            )
            return False

    async def check_and_mark(
        self,
        message_id: str,
    ) -> tuple[bool, dict[str, Any] | None]:
        """Atomically check if duplicate and mark as processing.

        Uses Redis SETNX for atomic operation.

        Args:
            message_id: The unique message identifier

        Returns:
            Tuple of (is_duplicate, cached_result)
            - is_duplicate: True if already processed
            - cached_result: Previous result if available
        """
        try:
            client = await self._get_client()
            key = self._make_key(message_id)

            # Try to set with NX (only if not exists)
            was_set = await client.set(
                key,
                "processing",
                ex=self.ttl_seconds,
                nx=True,
            )

            if was_set:
                # Successfully acquired - not a duplicate
                logger.debug("idempotency_key_acquired", message_id=message_id)
                return False, None
            else:
                # Key exists - get the stored result
                stored = await client.get(key)
                cached_result = None
                if stored and stored != "processing":
                    import json

                    try:
                        cached_result = json.loads(stored)
                    except json.JSONDecodeError:
                        pass

                logger.info(
                    "duplicate_detected_atomic",
                    message_id=message_id,
                    has_cached_result=cached_result is not None,
                )
                return True, cached_result
        except Exception as e:
            logger.warning(
                "atomic_check_failed",
                message_id=message_id,
                error=str(e),
            )
            # Fail open - allow processing
            return False, None

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("redis_connection_closed")
