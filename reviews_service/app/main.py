from contextlib import asynccontextmanager
import sys
from loguru import logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.core.kafka import kafka_producer
from app.db import connect, disconnect
from app.routers.reviews import router as reviews_router
from app.routers.metrics import router as metrics_router
from app.middleware.logging import LoggingMiddleware
from app.middleware.metrics import MetricsMiddleware


logger.remove()
logger.add(
    sys.stdout,
    format='{{"timestamp": "{time:YYYY-MM-DDTHH:mm:ssZ}", '
           '"level": "{level}", '
           '"service": "review", '
           '"message": "{message}"}}',
    level="INFO",
    serialize=True,
)



@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect()
    try:
        await kafka_producer.start()
    except Exception as e:
        logger.warning("Kafka producer not started: %s", e)
    yield

    await kafka_producer.stop()
    await disconnect()

app = FastAPI(title="Reviews Service", version="0.1.0", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)



@app.get("/health")
async def health():
    return {"status": "ok"}


app.add_middleware(LoggingMiddleware)
app.add_middleware(MetricsMiddleware)

app.include_router(metrics_router)
app.include_router(reviews_router)