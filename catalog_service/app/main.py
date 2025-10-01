import uvicorn
from fastapi import FastAPI
from app.routers import categories, products
from app.core.redis import init_redis, close_redis
from app.core.kafka import init_kafka, close_kafka

app = FastAPI(title="Catalog Service")


@app.on_event("startup")
async def startup():
    await init_redis(app)
    await init_kafka()


@app.on_event("shutdown")
async def shutdown():
    await close_redis()
    await close_kafka()


app.include_router(categories.router)
app.include_router(products.router)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
