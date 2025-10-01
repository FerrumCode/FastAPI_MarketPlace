import json
import asyncio
from aiokafka import AIOKafkaProducer
import os

producer: AIOKafkaProducer | None = None

async def init_kafka(retries=10, delay=5):
    global producer
    for i in range(retries):
        try:
            producer = AIOKafkaProducer(
                bootstrap_servers="kafka:9092",
                value_serializer=lambda v: json.dumps(v).encode("utf-8")
            )
            await producer.start()
            print("Kafka producer started")
            return
        except Exception as e:
            print(f"Kafka not ready, retry {i+1}/{retries}: {e}")
            await asyncio.sleep(delay)
    raise RuntimeError("Kafka producer could not be started")


async def close_kafka():
    global producer
    if producer:
        await producer.stop()


async def send_kafka_event(topic: str, event: dict):
    if not producer:
        raise RuntimeError("Kafka producer is not initialized")
    await producer.send_and_wait(topic, event)
