import asyncio
import json
from typing import Any, Dict

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import GroupCoordinatorNotAvailableError, KafkaError
from loguru import logger
from prometheus_client import Counter

from env import KAFKA_BROKER, KAFKA_ORDER_TOPIC, KAFKA_CONSUMER_GROUP_ID, SERVICE_NAME
from app.tasks.orders import process_order_created


KAFKA_CONSUMER_START_TOTAL = Counter(
    "kafka_consumer_start_total",
    "Kafka consumer start attempts",
    ["service", "status"],
)

KAFKA_CONSUMER_MESSAGES_TOTAL = Counter(
    "kafka_consumer_messages_total",
    "Kafka messages processed by consumer",
    ["service", "topic", "event_type", "result"],
)

KAFKA_CONSUMER_ERRORS_TOTAL = Counter(
    "kafka_consumer_errors_total",
    "Kafka consumer errors in main loop",
    ["service", "error_type"],
)


async def _consume_once() -> None:
    consumer = AIOKafkaConsumer(
        KAFKA_ORDER_TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        group_id=KAFKA_CONSUMER_GROUP_ID,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        enable_auto_commit=True,
        auto_offset_reset="earliest",
    )

    KAFKA_CONSUMER_START_TOTAL.labels(
        service=SERVICE_NAME,
        status="attempt",
    ).inc()

    try:
        await consumer.start()
        logger.info(
            "Kafka consumer started. broker={broker}, topic={topic}, group_id={group_id}",
            broker=KAFKA_BROKER,
            topic=KAFKA_ORDER_TOPIC,
            group_id=KAFKA_CONSUMER_GROUP_ID,
        )
        KAFKA_CONSUMER_START_TOTAL.labels(
            service=SERVICE_NAME,
            status="success",
        ).inc()

        async for msg in consumer:
            payload: Dict[str, Any] = msg.value
            event_type = payload.get("event")

            logger.info(
                "Kafka message received. topic={topic}, partition={partition}, offset={offset}, event_type={event_type}, payload={payload}",
                topic=msg.topic,
                partition=msg.partition,
                offset=msg.offset,
                event_type=event_type,
                payload=payload,
            )

            if event_type == "ORDER_CREATED":
                order_id = payload.get("order_id")
                logger.info(
                    "Submitting Celery task orders.process_order_created for order_id={order_id}",
                    order_id=order_id,
                )
                process_order_created.delay(payload)
                KAFKA_CONSUMER_MESSAGES_TOTAL.labels(
                    service=SERVICE_NAME,
                    topic=msg.topic,
                    event_type=event_type or "UNKNOWN",
                    result="processed",
                ).inc()
            else:
                logger.info(
                    "Ignoring Kafka event type={event_type}",
                    event_type=event_type,
                )
                KAFKA_CONSUMER_MESSAGES_TOTAL.labels(
                    service=SERVICE_NAME,
                    topic=msg.topic,
                    event_type=event_type or "UNKNOWN",
                    result="ignored",
                ).inc()

    finally:
        try:
            await consumer.stop()
            logger.info("Kafka consumer stopped")
        except Exception as exc:
            logger.warning(
                "Error while stopping Kafka consumer: {exc}",
                exc=exc,
            )
            KAFKA_CONSUMER_ERRORS_TOTAL.labels(
                service=SERVICE_NAME,
                error_type="stop_error",
            ).inc()


async def _run_consumer_forever() -> None:
    await asyncio.sleep(5)

    while True:
        try:
            await _consume_once()
        except GroupCoordinatorNotAvailableError as exc:
            logger.warning(
                "Kafka group coordinator not available yet: {exc}. Will retry in 5 seconds...",
                exc=exc,
            )
            KAFKA_CONSUMER_ERRORS_TOTAL.labels(
                service=SERVICE_NAME,
                error_type="group_coordinator_not_available",
            ).inc()
            await asyncio.sleep(5)
        except KafkaError as exc:
            logger.exception(
                "KafkaError in consumer loop: {exc}. Will retry in 5 seconds...",
                exc=exc,
            )
            KAFKA_CONSUMER_ERRORS_TOTAL.labels(
                service=SERVICE_NAME,
                error_type="kafka_error",
            ).inc()
            await asyncio.sleep(5)
        except Exception as exc:
            logger.exception(
                "Unexpected error in Kafka consumer loop: {exc}. Will retry in 5 seconds...",
                exc=exc,
            )
            KAFKA_CONSUMER_ERRORS_TOTAL.labels(
                service=SERVICE_NAME,
                error_type="unexpected_error",
            ).inc()
            await asyncio.sleep(5)


def main() -> None:
    try:
        logger.info(
            "Starting Kafka consumer main loop. broker={broker}, topic={topic}, group_id={group_id}",
            broker=KAFKA_BROKER,
            topic=KAFKA_ORDER_TOPIC,
            group_id=KAFKA_CONSUMER_GROUP_ID,
        )
        asyncio.run(_run_consumer_forever())
    except KeyboardInterrupt:
        logger.info("Kafka consumer interrupted by user")


if __name__ == "__main__":
    main()
