import uvicorn
from fastapi import FastAPI
from app.routers import categories
from app.routers import products


#from app.middleware.jwt_middleware import JWTMiddleware
#from app.core.redis import init_redis, close_redis

from app.db import engine, Base


app = FastAPI(title="Catalog Service")


# Redis init
@app.on_event("startup")
async def startup():
    pass
    # #Инициализируем Redis
    # await init_redis(app)


# @app.on_event("shutdown")
# async def shutdown():
#     await close_redis()


# Добавляем JWT middleware (публичные пути уже внутри middleware)
#pp.add_middleware(JWTMiddleware)


# app.include_router(categories.router)
app.include_router(categories.router)
app.include_router(products.router)



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)