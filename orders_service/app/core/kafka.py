import json
from typing import Any, Optional

from aiokafka import AIOKafkaProducer
from loguru import logger
from prometheus_client import Counter

from env import KAFKA_BROKER, SERVICE_NAME

KAFKA_PRODUCER_START_TOTAL = Counter(
    "orders_kafka_producer_start_total",
    "Kafka producer start events",
    ["service", "result"],
)

KAFKA_PRODUCER_STOP_TOTAL = Counter(
    "orders_kafka_producer_stop_total",
    "Kafka producer stop events",
    ["service", "result"],
)

KAFKA_PRODUCER_MESSAGES_TOTAL = Counter(
    "orders_kafka_producer_messages_total",
    "Kafka producer send events",
    ["service", "result"],
)


class KafkaProducer:
    def __init__(self):
        self._producer: Optional[AIOKafkaProducer] = None

    async def start(self):
        KAFKA_PRODUCER_START_TOTAL.labels(
            service=SERVICE_NAME,
            result="attempt",
        ).inc()
        logger.info("Kafka producer start requested")
        if self._producer is None:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode(
                    "utf-8"
                ),
            )
            await self._producer.start()
            logger.info("Kafka producer started")
            KAFKA_PRODUCER_START_TOTAL.labels(
                service=SERVICE_NAME,
                result="success",
            ).inc()

    async def stop(self):
        KAFKA_PRODUCER_STOP_TOTAL.labels(
            service=SERVICE_NAME,
            result="attempt",
        ).inc()
        logger.info("Kafka producer stop requested")
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")
            KAFKA_PRODUCER_STOP_TOTAL.labels(
                service=SERVICE_NAME,
                result="success",
            ).inc()

    async def send(self, topic: str, value: Any, key: str | None = None):
        KAFKA_PRODUCER_MESSAGES_TOTAL.labels(
            service=SERVICE_NAME,
            result="attempt",
        ).inc()
        logger.info(
            "Sending Kafka message to topic='{topic}' with key='{key}'",
            topic=topic,
            key=key,
        )
        if not self._producer:
            logger.warning("Kafka producer not initialized; skip send")
            KAFKA_PRODUCER_MESSAGES_TOTAL.labels(
                service=SERVICE_NAME,
                result="not_initialized",
            ).inc()
            return
        try:
            await self._producer.send_and_wait(
                topic,
                value=value,
                key=(key.encode() if key else None),
            )
            logger.info(
                "Kafka message sent to topic='{topic}' with key='{key}'",
                topic=topic,
                key=key,
            )
            KAFKA_PRODUCER_MESSAGES_TOTAL.labels(
                service=SERVICE_NAME,
                result="success",
            ).inc()
        except Exception as e:
            logger.exception(
                "Failed to send Kafka message to topic='{topic}' with key='{key}': {error}",
                topic=topic,
                key=key,
                error=str(e),
            )
            KAFKA_PRODUCER_MESSAGES_TOTAL.labels(
                service=SERVICE_NAME,
                result="error",
            ).inc()


kafka_producer = KafkaProducer()


async def send_kafka_event(topic: str, payload: dict) -> None:
    logger.info(
        "Sending Kafka event via helper to topic='{topic}'",
        topic=topic,
    )
    await kafka_producer.send(topic, payload)
