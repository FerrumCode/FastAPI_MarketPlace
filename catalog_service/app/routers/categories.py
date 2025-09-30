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

router = APIRouter(prefix='/categories', tags=['Categories'])



@router.get("/")
async def get_all_categories():
    return {"detail": "Hello world"}


@router.post("/")
async def create_category():
    return {"detail": "Hello world"}


@router.put("/{id}")
async def update_category(id: int):
    return {"detail": "Hello world"}


@router.delete("/{id}")
async def delete_category(id: int):
    return {"detail": "Hello world"}