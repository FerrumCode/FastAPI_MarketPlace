import json
from typing import Optional

from aiokafka import AIOKafkaProducer
from env import KAFKA_BROKER, KAFKA_REVIEW_TOPIC, SERVICE_NAME
from loguru import logger
from prometheus_client import Counter


KAFKA_PRODUCER_START_TOTAL = Counter(
    "kafka_producer_start_total",
    "Kafka producer start events",
    ["service", "result"],
)

KAFKA_PRODUCER_STOP_TOTAL = Counter(
    "kafka_producer_stop_total",
    "Kafka producer stop events",
    ["service", "result"],
)

KAFKA_SEND_TOTAL = Counter(
    "kafka_send_total",
    "Kafka send events",
    ["service", "result"],
)


class KafkaProducer:
    def __init__(self) -> None:
        self._producer: Optional[AIOKafkaProducer] = None
        self._starting: bool = False

    async def start(self) -> None:
        if self._producer or self._starting:
            return
        self._starting = True
        KAFKA_PRODUCER_START_TOTAL.labels(service=SERVICE_NAME, result="attempt").inc()
        logger.info(
            "Attempting to start Kafka producer (bootstrap={bootstrap}, topic={topic})",
            bootstrap=KAFKA_BROKER,
            topic=KAFKA_REVIEW_TOPIC,
        )
        try:
            producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BROKER)
            await producer.start()
            self._producer = producer
            logger.info(
                "Kafka producer started (bootstrap={bootstrap}, topic={topic})",
                bootstrap=KAFKA_BROKER,
                topic=KAFKA_REVIEW_TOPIC,
            )
            KAFKA_PRODUCER_START_TOTAL.labels(service=SERVICE_NAME, result="success").inc()
        except Exception as e:
            self._producer = None
            logger.warning(
                "Kafka producer NOT started: {error} (bootstrap={bootstrap})",
                error=e,
                bootstrap=KAFKA_BROKER,
            )
            KAFKA_PRODUCER_START_TOTAL.labels(service=SERVICE_NAME, result="error").inc()
        finally:
            self._starting = False

    async def stop(self) -> None:
        if self._producer:
            KAFKA_PRODUCER_STOP_TOTAL.labels(service=SERVICE_NAME, result="attempt").inc()
            logger.info("Attempting to stop Kafka producer")
            try:
                await self._producer.stop()
                logger.info("Kafka producer stopped")
                KAFKA_PRODUCER_STOP_TOTAL.labels(service=SERVICE_NAME, result="success").inc()
            except Exception as e:
                logger.warning("Kafka producer stop error: {error}", error=e)
                KAFKA_PRODUCER_STOP_TOTAL.labels(service=SERVICE_NAME, result="error").inc()
            finally:
                self._producer = None

    async def _send(self, payload: dict) -> None:
        if not self._producer:
            logger.debug("Kafka producer not ready; skipping send")
            KAFKA_SEND_TOTAL.labels(service=SERVICE_NAME, result="not_ready").inc()
            return
        KAFKA_SEND_TOTAL.labels(service=SERVICE_NAME, result="attempt").inc()
        logger.debug(
            "Sending message to Kafka topic={topic} via producer",
            topic=KAFKA_REVIEW_TOPIC,
        )
        try:
            value = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            await self._producer.send_and_wait(KAFKA_REVIEW_TOPIC, value=value)
            logger.info(
                "Message sent to Kafka topic={topic}",
                topic=KAFKA_REVIEW_TOPIC,
            )
            KAFKA_SEND_TOTAL.labels(service=SERVICE_NAME, result="success").inc()
        except Exception as e:
            logger.warning("Kafka send failed: {error}", error=e)
            KAFKA_SEND_TOTAL.labels(service=SERVICE_NAME, result="error").inc()
            self._producer = None

    async def send_review_created(self, payload: dict) -> None:
        logger.info(
            "Preparing to send REVIEW_CREATED event to Kafka for product_id={product_id}, user_id={user_id}",
            product_id=payload.get("product_id"),
            user_id=payload.get("user_id"),
        )
        await self._send({"event": "REVIEW_CREATED", **payload})


kafka_producer = KafkaProducer()
