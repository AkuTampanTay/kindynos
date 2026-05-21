import json
import logging
from typing import Any, Dict, Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

METRICS_TTL_SECONDS = 86_400  # 24 h


class RedisStore:
    """
    Persists computed risk metrics and confirmed arbitrage signals in Redis
    so the dashboard can query current state on connect without waiting for
    the next Pub/Sub event.

    Data layout:
      risk:{pair}           Hash  – {volatility, var_95, samples}
      opportunity:latest    String – JSON of last confirmed signal (TTL 5 min)
    """

    def __init__(self, host: str = "localhost", port: int = 6379):
        self._client = aioredis.Redis(host=host, port=port, decode_responses=True)

    async def ping(self) -> bool:
        return await self._client.ping()

    async def store_risk_metrics(self, pair: str, metrics: Dict[str, Any]) -> None:
        key = f"risk:{pair}"
        # Only write fields that have an actual value
        mapping = {k: str(v) for k, v in metrics.items() if v is not None}
        if not mapping:
            return
        async with self._client.pipeline(transaction=False) as pipe:
            pipe.hset(key, mapping=mapping)
            pipe.expire(key, METRICS_TTL_SECONDS)
            await pipe.execute()

    async def get_risk_metrics(self, pair: str) -> Optional[Dict[str, str]]:
        return await self._client.hgetall(f"risk:{pair}") or None

    async def store_latest_opportunity(self, data: Dict[str, Any]) -> None:
        await self._client.set("opportunity:latest", json.dumps(data), ex=300)

    async def get_latest_opportunity(self) -> Optional[Dict[str, Any]]:
        raw = await self._client.get("opportunity:latest")
        return json.loads(raw) if raw else None

    async def close(self) -> None:
        await self._client.aclose()
        logger.info("RedisStore closed.")
