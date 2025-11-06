import asyncio
import json
from aiokafka import AIOKafkaConsumer
from prometheus_client import Counter, Gauge, start_http_server
from ..config import settings
from ..logging_conf import setup_logging
from ..celery_app import celery_app

log = setup_logging()

MSG_CONSUMED = Counter("kafka_messages_consumed_total", "Total consumed Kafka messages", ["topic"])
ORDER_CREATED = Counter("order_created_events_total", "ORDER_CREATED events")
LAST_OFFSET = Gauge("kafka_last_committed_offset", "Last committed offset", ["topic", "partition"])

async def run():
    start_http_server(9102)  # /metrics
    consumer = AIOKafkaConsumer(
        settings.kafka_topic_orders,
        bootstrap_servers=settings.kafka_broker,
        group_id=settings.kafka_group,
        value_deserializer=lambda v: json.loads(v.decode()),
        enable_auto_commit=True,
        auto_offset_reset="latest",
    )
    await consumer.start()
    try:
        log.info("kafka_consumer_started", topic=settings.kafka_topic_orders)
        async for msg in consumer:
            MSG_CONSUMED.labels(topic=msg.topic).inc()
            LAST_OFFSET.labels(topic=msg.topic, partition=str(msg.partition)).set(msg.offset)
            event = msg.value
            etype = event.get("type")
            if etype == "ORDER_CREATED":
                ORDER_CREATED.inc()
                order_id = event.get("order_id")
                log.info("order_created_received", order_id=order_id)
                celery_app.send_task("app.tasks.process_order_created", args=[order_id])
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(run())
