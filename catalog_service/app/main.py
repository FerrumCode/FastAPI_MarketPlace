import sys
import uvicorn
from fastapi import FastAPI
from fastapi.responses import Response
from loguru import logger
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.routers import categories, products, metrics
from app.core.redis import init_redis, close_redis
from app.core.kafka import init_kafka, close_kafka
from app.middleware.logging import LoggingMiddleware
from app.middleware.metrics import MetricsMiddleware


logger.remove()
logger.add(
    sys.stdout,
    format='{{"timestamp": "{time:YYYY-MM-DDTHH:mm:ssZ}", '
           '"level": "{level}", '
           '"service": "catalog", '
           '"message": "{message}"}}',
    level="INFO",
    serialize=True,
)

app = FastAPI(title="Catalog Service")


@app.on_event("startup")
async def startup():
    logger.info("Application startup: initializing Redis and Kafka")
    await init_redis(app)
    await init_kafka()
    logger.info("Application startup completed")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Application shutdown: closing Redis and Kafka")
    await close_redis()
    await close_kafka()
    logger.info("Application shutdown completed")



app.add_middleware(LoggingMiddleware)
app.add_middleware(MetricsMiddleware)

app.include_router(metrics.router)
app.include_router(categories.router)
app.include_router(products.router)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
