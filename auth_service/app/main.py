import uvicorn
from fastapi import FastAPI
#from .routers import products
from app.routers import auth
from app.crud import users
from app.crud import roles
from app.crud import permissions

# Импорты автоинициализации БД
import asyncio
from app.db import engine, Base
from app.init_roles import create_default_roles

app = FastAPI(title="Auth Service")

# создаём таблицы и дефолтные роли при старте
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await create_default_roles()


#app.include_router(products.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(permissions.router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)