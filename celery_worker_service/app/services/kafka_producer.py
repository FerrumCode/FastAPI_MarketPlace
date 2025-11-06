import asyncio
import json
from aiokafka import AIOKafkaProducer
from ..config import settings
from ..logging_conf import setup_logging

log = setup_logging()

async def _send(topic: str, payload: dict):
    producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_broker, value_serializer=lambda v: json.dumps(v).encode())
    await producer.start()
    try:
        await producer.send_and_wait(topic, payload)
        log.info("kafka_produced", topic=topic, payload=payload)
    finally:
        await producer.stop()

def send_order_updated(order_id: str, status: str):
    payload = {"type": "ORDER_UPDATED", "order_id": order_id, "status": status}
    asyncio.run(_send(settings.kafka_topic_orders, payload))
