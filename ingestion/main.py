import asyncio
import json
import logging
from typing import Optional

from config import Config
from connection import WebSocketWorker
from kafka_producer import KafkaPublisher
from parser import MarketDataParser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _bybit_subscribe(ws) -> None:
    payload = json.dumps({
        "op": "subscribe",
        "args": ["orderbook.1.BTCUSDT", "orderbook.1.ETHUSDT", "orderbook.1.ETHBTC"],
    })
    await ws.send(payload)


async def _okx_subscribe(ws) -> None:
    payload = json.dumps({
        "op": "subscribe",
        "args": [
            {"channel": "tickers", "instId": "BTC-USDT"},
            {"channel": "tickers", "instId": "ETH-USDT"},
            {"channel": "tickers", "instId": "ETH-BTC"},
        ],
    })
    await ws.send(payload)


NORMALIZERS = {
    "binance": MarketDataParser.normalize_binance_ticker,
    "bybit":   MarketDataParser.normalize_bybit_ticker,
    "okx":     MarketDataParser.normalize_okx_ticker,
}


async def dispatcher(queue: asyncio.Queue, publisher: Optional[KafkaPublisher]) -> None:
    logger.info("Dispatcher started.")
    while True:
        try:
            label, raw_msg = await queue.get()
            normalizer = NORMALIZERS.get(label)
            if normalizer is None:
                queue.task_done()
                continue

            data = normalizer(raw_msg)
            if data is None:
                if label in ("bybit", "okx"):
                    logger.debug(f"[{label}] dropped: {raw_msg[:300]}")
                queue.task_done()
                continue

            latency = data["ingest_timestamp"] - data["exchange_timestamp"]

            if Config.DRY_RUN or publisher is None:
                logger.info(
                    f"[DRY-RUN] {data['exchange']} {data['base']}/{data['quote']}"
                    f"  bid={data['bid']}  ask={data['ask']}  latency={latency}ms"
                )
            else:
                await publisher.send(data)
                logger.info(
                    f"Published {data['exchange']} {data['base']}/{data['quote']}"
                    f"  bid={data['bid']}  latency={latency}ms"
                )

            queue.task_done()

        except asyncio.CancelledError:
            logger.info("Dispatcher cancelled.")
            break
        except Exception as exc:
            logger.error(f"Dispatcher error: {exc}", exc_info=True)


async def main() -> None:
    queue: asyncio.Queue = asyncio.Queue(maxsize=Config.QUEUE_MAX_SIZE)

    workers = [
        WebSocketWorker(Config.BINANCE_WS_URL, queue, label="binance"),
        WebSocketWorker(Config.BYBIT_WS_URL,   queue, label="bybit",  on_connect=_bybit_subscribe),
        WebSocketWorker(Config.OKX_WS_URL,     queue, label="okx",    on_connect=_okx_subscribe),
    ]

    publisher: Optional[KafkaPublisher] = None
    if not Config.DRY_RUN:
        publisher = KafkaPublisher()
        await publisher.start()

    tasks = [asyncio.create_task(w.run()) for w in workers]
    tasks.append(asyncio.create_task(dispatcher(queue, publisher)))

    try:
        await asyncio.gather(*tasks)
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Shutdown signal received — stopping workers …")
    finally:
        for w in workers:
            w.stop()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if publisher:
            await publisher.stop()
        logger.info("Ingestion service offline.")


if __name__ == "__main__":
    asyncio.run(main())
