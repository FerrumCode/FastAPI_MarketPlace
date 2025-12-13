import json
import asyncio
from aiokafka import AIOKafkaProducer
import os
from loguru import logger
from prometheus_client import Counter, Gauge

SERVICE_NAME = "catalog_service"

KAFKA_OPS = Counter(
    "catalog_kafka_ops",
    "Kafka producer operations",
    ["service", "operation", "status"],
)

KAFKA_CONNECTION_STATUS = Gauge(
    "catalog_kafka_connection_status",
    "Kafka producer connection status (1=connected, 0=disconnected)",
    ["service"],
)

producer: AIOKafkaProducer | None = None


async def init_kafka(retries=10, delay=5):
    global producer
    logger.info(
        "Initializing Kafka producer for service={service}, retries={retries}, delay={delay}",
        service=SERVICE_NAME,
        retries=retries,
        delay=delay,
    )

    for i in range(retries):
        try:
            producer = AIOKafkaProducer(
                bootstrap_servers="kafka:9092",
                value_serializer=lambda v: json.dumps(v).encode("utf-8")
            )
            await producer.start()
            print("Kafka producer started")

            logger.info(
                "Kafka producer started successfully on attempt {attempt} for service={service}",
                attempt=i + 1,
                service=SERVICE_NAME,
            )

            KAFKA_CONNECTION_STATUS.labels(service=SERVICE_NAME).set(1)
            KAFKA_OPS.labels(
                service=SERVICE_NAME,
                operation="start",
                status="success",
            ).inc()

            return
        except Exception as e:
            print(f"Kafka not ready, retry {i+1}/{retries}: {e}")

            logger.warning(
                "Kafka not ready, retry {attempt}/{retries} for service={service}: {error}",
                attempt=i + 1,
                retries=retries,
                service=SERVICE_NAME,
                error=str(e),
            )

            KAFKA_CONNECTION_STATUS.labels(service=SERVICE_NAME).set(0)
            KAFKA_OPS.labels(
                service=SERVICE_NAME,
                operation="start",
                status="retry_error",
            ).inc()

            await asyncio.sleep(delay)

    logger.error(
        "Kafka producer could not be started after {retries} retries for service={service}",
        retries=retries,
        service=SERVICE_NAME,
    )

    KAFKA_OPS.labels(
        service=SERVICE_NAME,
        operation="start",
        status="failed",
    ).inc()

    raise RuntimeError("Kafka producer could not be started")


async def close_kafka():
    global producer
    if producer:
        await producer.stop()
        logger.info("Kafka producer stopped for service={service}", service=SERVICE_NAME)

        KAFKA_CONNECTION_STATUS.labels(service=SERVICE_NAME).set(0)
        KAFKA_OPS.labels(
            service=SERVICE_NAME,
            operation="close",
            status="success",
        ).inc()
    else:
        logger.info(
            "Attempt to close Kafka producer, but it is not initialized for service={service}",
            service=SERVICE_NAME,
        )
        KAFKA_OPS.labels(
            service=SERVICE_NAME,
            operation="close",
            status="noop",
        ).inc()


async def send_kafka_event(topic: str, event: dict):
    if not producer:
        logger.error(
            "Attempt to send Kafka event before producer initialization. service={service}, topic={topic}",
            service=SERVICE_NAME,
            topic=topic,
        )

        KAFKA_CONNECTION_STATUS.labels(service=SERVICE_NAME).set(0)
        KAFKA_OPS.labels(
            service=SERVICE_NAME,
            operation="send",
            status="not_initialized",
        ).inc()

        raise RuntimeError("Kafka producer is not initialized")

    logger.info(
        "Sending Kafka event. service={service}, topic={topic}",
        service=SERVICE_NAME,
        topic=topic,
    )

    await producer.send_and_wait(topic, event)

    KAFKA_OPS.labels(
        service=SERVICE_NAME,
        operation="send",
        status="success",
    ).inc()

    logger.info(
        "Kafka event sent successfully. service={service}, topic={topic}",
        service=SERVICE_NAME,
        topic=topic,
    )
