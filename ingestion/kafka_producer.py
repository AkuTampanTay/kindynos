import json
import logging
from typing import Any, Dict

from aiokafka import AIOKafkaProducer

from config import Config

logger = logging.getLogger(__name__)


class KafkaPublisher:
    """Thin async wrapper around AIOKafkaProducer."""

    def __init__(self):
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            compression_type="gzip",
            acks="all",
        )
        await self._producer.start()
        logger.info(f"Kafka producer connected to {Config.KAFKA_BOOTSTRAP_SERVERS}.")

    async def send(self, data: Dict[str, Any]) -> None:
        if self._producer is None:
            raise RuntimeError("KafkaPublisher.start() has not been called.")
        await self._producer.send_and_wait(Config.KAFKA_TOPIC, value=data)

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped.")
