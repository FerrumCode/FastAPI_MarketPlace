import sys

import uvicorn
from fastapi import FastAPI
from fastapi.responses import Response
from loguru import logger
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.routers import auth, users, roles, permissions
from app.middleware.jwt_middleware import JWTMiddleware
from app.middleware.logging import LoggingMiddleware
from app.core.redis import init_redis, close_redis
from app.db import engine, Base


logger.remove()
logger.add(
    sys.stdout,
    format='{{"timestamp": "{time:YYYY-MM-DDTHH:mm:ssZ}", '
           '"level": "{level}", '
           '"service": "auth", '
           '"message": "{message}"}}',
    level="INFO",
    serialize=True,
)

app = FastAPI(title="Auth Service")


@app.on_event("startup")
async def startup():
    logger.info("Application startup: initializing DB and Redis")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await init_redis(app)
    logger.info("Application startup completed")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Application shutdown: closing Redis")
    await close_redis()
    logger.info("Application shutdown completed")


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.add_middleware(JWTMiddleware)
app.add_middleware(LoggingMiddleware)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(permissions.router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
