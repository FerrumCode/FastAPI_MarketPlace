import asyncio
import json
import logging
from typing import Any, Dict

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import GroupCoordinatorNotAvailableError, KafkaError

from env import KAFKA_BROKER, KAFKA_ORDER_TOPIC, KAFKA_CONSUMER_GROUP_ID
from app.tasks.orders import process_order_created

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _consume_once() -> None:
    consumer = AIOKafkaConsumer(
        KAFKA_ORDER_TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        group_id=KAFKA_CONSUMER_GROUP_ID,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        enable_auto_commit=True,
        auto_offset_reset="earliest",
    )

    try:
        await consumer.start()
        logger.info(
            "Kafka consumer started. broker=%s, topic=%s, group_id=%s",
            KAFKA_BROKER,
            KAFKA_ORDER_TOPIC,
            KAFKA_CONSUMER_GROUP_ID,
        )

        async for msg in consumer:
            payload: Dict[str, Any] = msg.value
            event_type = payload.get("event")

            logger.info("Kafka message received from %s: %s", KAFKA_ORDER_TOPIC, payload)

            if event_type == "ORDER_CREATED":
                order_id = payload.get("order_id")
                logger.info(
                    "Submitting Celery task orders.process_order_created for order_id=%s",
                    order_id,
                )
                process_order_created.delay(payload)
            else:
                logger.info("Ignoring Kafka event type=%s", event_type)

    finally:
        try:
            await consumer.stop()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error while stopping Kafka consumer: %s", exc)


async def _run_consumer_forever() -> None:
    await asyncio.sleep(5)

    while True:
        try:
            await _consume_once()
        except GroupCoordinatorNotAvailableError as exc:
            logger.warning(
                "Kafka group coordinator not available yet: %s. "
                "Will retry in 5 seconds...",
                exc,
            )
            await asyncio.sleep(5)
        except KafkaError as exc:
            logger.exception(
                "KafkaError in consumer loop: %s. Will retry in 5 seconds...",
                exc,
            )
            await asyncio.sleep(5)
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Unexpected error in Kafka consumer loop: %s. "
                "Will retry in 5 seconds...",
                exc,
            )
            await asyncio.sleep(5)


def main() -> None:
    try:
        asyncio.run(_run_consumer_forever())
    except KeyboardInterrupt:
        logger.info("Kafka consumer interrupted by user")


if __name__ == "__main__":
    main()
