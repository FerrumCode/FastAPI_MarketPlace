import uvicorn
from fastapi import FastAPI
from app.routers import auth
from app.crud import users
from app.crud import roles
from app.crud import permissions

from app.middleware.jwt_middleware import JWTMiddleware
from app.core.redis import init_redis, close_redis

# Импорты автоинициализации БД
from app.db import engine, Base
#from app.init_roles import create_default_roles

app = FastAPI(title="Auth Service")


# Redis init
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    #Инициализируем Redis
    await init_redis(app)


@app.on_event("shutdown")
async def shutdown():
    await close_redis()


# Добавляем JWT middleware (публичные пути уже внутри middleware)
app.add_middleware(JWTMiddleware)

# Подключаем роутеры
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(permissions.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)