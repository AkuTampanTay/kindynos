import asyncio
import logging
import os

from consumer import MarketDataConsumer
from models import ArbitrageOpportunity
from publisher import RedisPublisher
from redis_store import RedisStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP        = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC            = os.getenv("KAFKA_TOPIC", "market-data")
REDIS_HOST             = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT             = int(os.getenv("REDIS_PORT", "6379"))
DETECTION_INTERVAL_MS  = int(os.getenv("DETECTION_INTERVAL_MS", "100"))
RISK_SNAPSHOT_INTERVAL = int(os.getenv("RISK_SNAPSHOT_INTERVAL_S", "5"))


async def main() -> None:
    publisher   = RedisPublisher(host=REDIS_HOST, port=REDIS_PORT)
    redis_store = RedisStore(host=REDIS_HOST, port=REDIS_PORT)

    await publisher.connect()
    await redis_store.ping()
    logger.info("Redis connections established.")

    async def on_opportunity(opp: ArbitrageOpportunity) -> None:
        payload = {
            "cycle":        opp.cycle,
            "profit_ratio": opp.profit_ratio,
            "profit_pct":   round(opp.profit_pct, 6),
            "timestamp_ms": opp.timestamp_ms,
            "legs": [
                {
                    "source":   e.source,
                    "target":   e.target,
                    "exchange": e.exchange,
                    "rate":     e.rate,
                    "fee":      e.fee,
                }
                for e in opp.legs
            ],
        }
        await publisher.publish_opportunity(payload)
        await redis_store.store_latest_opportunity(payload)

    async def on_risk_snapshot(snapshot: dict) -> None:
        await publisher.publish_risk(snapshot)
        logger.debug(f"Risk snapshot published — {len(snapshot)} pairs tracked.")

    consumer = MarketDataConsumer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        topic=KAFKA_TOPIC,
        detection_interval_ms=DETECTION_INTERVAL_MS,
        risk_snapshot_interval_s=RISK_SNAPSHOT_INTERVAL,
        redis_store=redis_store,
        on_opportunity=on_opportunity,
        on_risk_snapshot=on_risk_snapshot,
    )

    logger.info("Arbitrage engine starting …")
    try:
        await consumer.run()
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        await consumer.stop()
        await redis_store.close()
        await publisher.close()
        logger.info("Engine offline.")


if __name__ == "__main__":
    asyncio.run(main())
