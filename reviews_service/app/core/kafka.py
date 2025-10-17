import asyncio
import json
import logging
from aiokafka import AIOKafkaProducer
from .config import settings

logger = logging.getLogger(__name__)

class KafkaProducer:
    def __init__(self) -> None:
        self._producer: AIOKafkaProducer | None = None

    async def start(self):
        if self._producer is None:
            self._producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BROKER)
            await self._producer.start()
            logger.info("Kafka producer started")

    async def stop(self):
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")
            self._producer = None

    async def send_review_created(self, payload: dict):
        if not self._producer:
            return
        value = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        await self._producer.send_and_wait(settings.KAFKA_REVIEW_TOPIC, value=value)

kafka_producer = KafkaProducer()
