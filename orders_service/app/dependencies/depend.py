from typing import Any, Dict
from fastapi import HTTPException, Security
from starlette import status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt  # PyJWT

from app.core.config import settings

http_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Security(http_bearer),
) -> Dict[str, Any]:
    """
    Делает 2 вещи:
    1) Регистрирует в OpenAPI security-схему HTTP Bearer (кнопка Authorize появится сверху справа).
    2) Валидирует JWT локально по SECRET_KEY/ALGORITHM из .env и возвращает payload как dict.
    """
    token = creds.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require": ["exp"]},  # требуем exp
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if "id" not in payload:
        # в твоём токене есть: sub, id, role_id, exp — проверим хотя бы id
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token payload missing 'id'")

    return payload
