from pydantic import BaseModel


class CreateProduct(BaseModel):
    name: str
    description: str
    price: int
    image_url: str
    stock: int
    category: int


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