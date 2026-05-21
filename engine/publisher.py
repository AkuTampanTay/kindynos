import json
import logging
from typing import Any, Dict

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

OPPORTUNITIES_CHANNEL = "arbitrage:opportunities"
RISK_CHANNEL = "arbitrage:risk"


class RedisPublisher:
    """
    Publishes arbitrage signals and risk snapshots to Redis Pub/Sub channels
    so the dashboard WebSocket layer can forward them to connected clients.
    """

    def __init__(self, host: str = "localhost", port: int = 6379):
        self._host = host
        self._port = port
        self._client: aioredis.Redis | None = None

    async def connect(self) -> None:
        self._client = aioredis.Redis(
            host=self._host, port=self._port, decode_responses=True
        )
        await self._client.ping()
        logger.info(f"Redis publisher connected to {self._host}:{self._port}")

    async def publish_opportunity(self, data: Dict[str, Any]) -> None:
        await self._publish(OPPORTUNITIES_CHANNEL, data)

    async def publish_risk(self, data: Dict[str, Any]) -> None:
        await self._publish(RISK_CHANNEL, data)

    async def _publish(self, channel: str, data: Dict[str, Any]) -> None:
        if not self._client:
            raise RuntimeError("RedisPublisher.connect() has not been called.")
        await self._client.publish(channel, json.dumps(data))

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            logger.info("Redis publisher closed.")
