# reviews_service/app/core/kafka.py
import json
import logging
import os
from typing import Optional

from aiokafka import AIOKafkaProducer
from .config import settings

logger = logging.getLogger(__name__)


# Надёжно читаем конфиг с запасными значениями из ENV
KAFKA_BROKER = getattr(settings, "KAFKA_BROKER", os.getenv("KAFKA_BROKER", "kafka:9092"))
KAFKA_REVIEW_TOPIC = getattr(settings, "KAFKA_REVIEW_TOPIC", os.getenv("KAFKA_REVIEW_TOPIC", "review_events"))


class KafkaProducer:
    """
    Обёртка над AIOKafkaProducer:
    - start() не бросает исключения при недоступной Kafka (оставляет продьюсер None и пишет warning)
    - send_*() — no-op, если продьюсер не готов
    """

    def __init__(self) -> None:
        self._producer: Optional[AIOKafkaProducer] = None
        self._starting: bool = False


    async def start(self) -> None:
        if self._producer or self._starting:
            return
        self._starting = True
        try:
            producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BROKER)
            await producer.start()
            self._producer = producer
            logger.info("Kafka producer started (bootstrap=%s, topic=%s)", KAFKA_BROKER, KAFKA_REVIEW_TOPIC)
        except Exception as e:
            self._producer = None
            logger.warning("Kafka producer NOT started: %s (bootstrap=%s)", e, KAFKA_BROKER)
        finally:
            self._starting = False


    async def stop(self) -> None:
        if self._producer:
            try:
                await self._producer.stop()
                logger.info("Kafka producer stopped")
            except Exception as e:
                logger.warning("Kafka producer stop error: %s", e)
            finally:
                self._producer = None


    async def _send(self, payload: dict) -> None:
        if not self._producer:
            logger.debug("Kafka producer not ready; skipping send")
            return
        try:
            value = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            await self._producer.send_and_wait(KAFKA_REVIEW_TOPIC, value=value)
        except Exception as e:
            # Если отправка упала (например, брокер перегружался) — не валим сервис,
            # помечаем продьюсер как неготовый; следующая отправка попробует снова после start().
            logger.warning("Kafka send failed: %s", e)
            self._producer = None


    async def send_review_created(self, payload: dict) -> None:
        # Добавим тип события для единообразия
        await self._send({"event": "REVIEW_CREATED", **payload})


kafka_producer = KafkaProducer()
