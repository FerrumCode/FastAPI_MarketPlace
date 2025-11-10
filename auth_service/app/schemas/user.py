# from pydantic import BaseModel
#
#
# class CreateUser(BaseModel):
#     name: str
#     email: str
#     password: str


import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional


class UserBase(BaseModel):
    """Базовая схема пользователя"""
    name: str = Field(..., min_length=2, max_length=50, description="Имя пользователя")
    email: EmailStr = Field(..., description="Email адрес")


class CreateUser(UserBase):
    """Схема создания пользователя"""
    password: str = Field(..., min_length=8, description="Пароль (минимум 8 символов)")

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Валидация пароля"""
        if len(v) < 8:
            raise ValueError('Пароль должен содержать минимум 8 символов')
        if not any(char.isdigit() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        if not any(char.isupper() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not any(char.islower() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну строчную букву')
        return v


class UpdateUser(BaseModel):
    """Схема обновления пользователя"""
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        """Валидация пароля"""
        if v is None:
            return v
        if len(v) < 8:
            raise ValueError('Пароль должен содержать минимум 8 символов')
        if not any(char.isdigit() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        if not any(char.isupper() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not any(char.islower() for char in v):
            raise ValueError('Пароль должен содержать хотя бы одну строчную букву')
        return v


class UserRead(UserBase):
    """Схема чтения пользователя"""
    id: uuid.UUID
    role_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UserWithRole(UserRead):
    """Схема пользователя с ролью"""
    role_name: str

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    """Схема для входа"""
    username: str = Field(..., description="Имя пользователя или email")
    password: str = Field(..., description="Пароль")