from pydantic import BaseModel


class CreateUser(BaseModel):
    name: str
    email: str
    password: str


class CreateRole(BaseModel):
    name: str
    description: str


class CreatePermission(BaseModel):
    code: str
    description: str | None = None