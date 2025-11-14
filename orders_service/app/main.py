import uvicorn
from fastapi import FastAPI

from app.core.kafka import kafka_producer
from app.routers import orders as orders_router
from app.routers import orders_items_crud as order_items_router

app = FastAPI(
    title="Orders Service",
    swagger_ui_parameters={"persistAuthorization": True},
)


@app.on_event("startup")
async def startup():
    await kafka_producer.start()


@app.on_event("shutdown")
async def shutdown():
    await kafka_producer.stop()


app.include_router(orders_router.router)
app.include_router(order_items_router.router)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
