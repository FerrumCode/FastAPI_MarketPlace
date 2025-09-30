from fastapi import APIRouter, Depends, status, HTTPException, Body
from sqlalchemy import select, insert
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
import jwt
import redis.asyncio as redis
from fastapi import Query


# from app.db_depends import get_db
# from app.core.redis import get_redis

# from env import SECRET_KEY, ALGORITHM

router = APIRouter(prefix='/products', tags=['Products'])


@router.get("/")
async def get_all_products():
    return {"detail": "Hello world"}


@router.get("/{id}")
async def get_product(id: int):
    return {"detail": "Hello world"}


@router.post("/")
async def create_product():
    return {"detail": "Hello world"}


@router.put("/{id}")
async def update_product(id: int):
    return {"detail": "Hello world"}


@router.delete("/{id}")
async def delete_product(id: int):
    return {"detail": "Hello world"}