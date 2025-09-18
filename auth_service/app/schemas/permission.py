from pydantic import BaseModel


class CreatePermission(BaseModel):
    code: str
    description: str | None = None