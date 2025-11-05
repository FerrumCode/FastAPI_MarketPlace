from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.logging import setup_logging
from app.core.kafka import kafka_producer
from app.db import connect, disconnect
from app.routers.reviews import router as reviews_router


setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect()
    try:
        await kafka_producer.start()
    except Exception as e:
        logger.warning("Kafka producer not started: %s", e)
    yield
    # Shutdown
    await kafka_producer.stop()
    await disconnect()

app = FastAPI(title="Reviews Service", version="0.1.0", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


# Метрики
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/health")
async def health():
    return {"status": "ok"}

app.include_router(reviews_router)