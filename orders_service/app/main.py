import uvicorn, sys
from fastapi import FastAPI
from loguru import logger

from app.core.kafka import kafka_producer
from app.routers import orders as orders_router
from app.routers import orders_items_crud as order_items_router
from app.routers import metrics as metrics_router
from app.middleware.logging import LoggingMiddleware
from app.middleware.metrics import MetricsMiddleware


logger.remove()
logger.add(
    sys.stdout,
    format='{{"timestamp": "{time:YYYY-MM-DDTHH:mm:ssZ}", '
           '"level": "{level}", '
           '"service": "orders", '
           '"message": "{message}"}}',
    level="INFO",
    serialize=True,
)


app = FastAPI(
    title="Orders Service",
    swagger_ui_parameters={"persistAuthorization": True},
)


@app.on_event("startup")
async def startup():
    logger.info("Application startup: initializing Kafka producer")
    await kafka_producer.start()
    logger.info("Application startup completed")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Application shutdown: stopping Kafka producer")
    await kafka_producer.stop()
    logger.info("Application shutdown completed")


app.add_middleware(LoggingMiddleware)
app.add_middleware(MetricsMiddleware)

app.include_router(metrics_router.router)
app.include_router(orders_router.router)
app.include_router(order_items_router.router)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
