import asyncio
import logging
from typing import Callable, Optional

import websockets
import websockets.exceptions

from config import Config

logger = logging.getLogger(__name__)


class WebSocketWorker:
    """
    Maintains a resilient WebSocket connection to a single exchange endpoint.

    Frames are pushed raw onto `data_queue` for downstream normalisation.
    Reconnection uses exponential backoff capped at MAX_RECONNECT_DELAY to
    avoid hammering exchange rate-limit policies during outages.
    """

    def __init__(
        self,
        url: str,
        data_queue: asyncio.Queue,
        label: str = "worker",
        on_connect: Optional[Callable] = None,
    ):
        self.url = url
        self.queue = data_queue
        self.label = label
        self._on_connect = on_connect  # coroutine called after each reconnect (e.g. subscribe msg)
        self._running = True

    async def run(self) -> None:
        delay = Config.INITIAL_RECONNECT_DELAY
        while self._running:
            try:
                logger.info(f"[{self.label}] Connecting to {self.url} …")
                async with websockets.connect(
                    self.url,
                    ping_interval=Config.HEARTBEAT_INTERVAL,
                    ping_timeout=10,
                ) as ws:
                    logger.info(f"[{self.label}] Connection established.")
                    delay = Config.INITIAL_RECONNECT_DELAY

                    if self._on_connect:
                        await self._on_connect(ws)

                    async for message in ws:
                        if not self._running:
                            break
                        await self.queue.put((self.label, message))

            except (websockets.exceptions.ConnectionClosed, OSError) as exc:
                logger.warning(
                    f"[{self.label}] Connection lost ({exc}). Retry in {delay:.0f}s …"
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, Config.MAX_RECONNECT_DELAY)

            except asyncio.CancelledError:
                logger.info(f"[{self.label}] Task cancelled — exiting.")
                break

            except Exception as exc:
                logger.error(f"[{self.label}] Unexpected error: {exc}", exc_info=True)
                await asyncio.sleep(delay)
                delay = min(delay * 2, Config.MAX_RECONNECT_DELAY)

    def stop(self) -> None:
        self._running = False
