import json
import logging
from typing import Any, Optional

from aiokafka import AIOKafkaProducer

from .config import settings

logger = logging.getLogger(__name__)


class KafkaProducer:
    def __init__(self):
        self._producer: Optional[AIOKafkaProducer] = None

    async def start(self):
        if self._producer is None:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8")
            )
            await self._producer.start()
            logger.info("Kafka producer started")

    async def stop(self):
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")

    async def send(self, topic: str, value: Any, key: str | None = None):
        if not self._producer:
            logger.warning("Kafka producer not initialized; skip send")
            return
        try:
            await self._producer.send_and_wait(topic, value=value, key=(key.encode() if key else None))
        except Exception as e:
            logger.exception("Failed to send Kafka message: %s", e)


kafka_producer = KafkaProducer()
