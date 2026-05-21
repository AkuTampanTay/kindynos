import asyncio
import json
import logging
import os

import redis.asyncio as aioredis
import websockets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
WS_HOST = os.getenv("WS_HOST", "0.0.0.0")
WS_PORT = int(os.getenv("WS_PORT", "8765"))

CHANNELS = ("arbitrage:opportunities", "arbitrage:risk")

_clients: set = set()


async def handle_client(websocket) -> None:
    _clients.add(websocket)
    addr = getattr(websocket, "remote_address", "unknown")
    logger.info(f"Client connected: {addr}  ({len(_clients)} total)")

    # Push current state immediately so the UI isn't blank on load
    try:
        r = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        latest = await r.get("opportunity:latest")
        await r.aclose()
        if latest:
            await websocket.send(
                json.dumps({"type": "opportunity", "data": json.loads(latest)})
            )
    except Exception as exc:
        logger.warning(f"Could not fetch initial state: {exc}")

    try:
        # Drain unexpected client frames; exits when connection closes
        async for _ in websocket:
            pass
    except Exception:
        pass
    finally:
        _clients.discard(websocket)
        logger.info(f"Client disconnected: {addr}  ({len(_clients)} remaining)")


async def _broadcast(payload: str) -> None:
    clients = list(_clients)
    if not clients:
        return
    results = await asyncio.gather(
        *[c.send(payload) for c in clients],
        return_exceptions=True,
    )
    for client, result in zip(clients, results):
        if isinstance(result, Exception):
            _clients.discard(client)


async def redis_listener() -> None:
    while True:
        try:
            r = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
            pubsub = r.pubsub()
            await pubsub.subscribe(*CHANNELS)
            logger.info(f"Subscribed to Redis channels: {CHANNELS}")

            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                channel = message["channel"]
                try:
                    data = json.loads(message["data"])
                except json.JSONDecodeError:
                    continue

                if channel == "arbitrage:opportunities":
                    event_type = "opportunity"
                elif channel == "arbitrage:risk":
                    event_type = "risk"
                else:
                    continue

                await _broadcast(json.dumps({"type": event_type, "data": data}))

        except (asyncio.CancelledError, KeyboardInterrupt):
            break
        except Exception as exc:
            logger.error(f"Redis error: {exc} — reconnecting in 3s …")
            await asyncio.sleep(3)


async def main() -> None:
    async with websockets.serve(handle_client, WS_HOST, WS_PORT):
        logger.info(f"WebSocket bridge listening on ws://{WS_HOST}:{WS_PORT}")
        try:
            await redis_listener()
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
    logger.info("Bridge offline.")


if __name__ == "__main__":
    asyncio.run(main())
