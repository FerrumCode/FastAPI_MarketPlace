import logging
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings


logger = logging.getLogger(__name__)
bearer = HTTPBearer(auto_error=False)


class User:
    def __init__(self, user_id: str, role: str = "user", email: str | None = None):
        self.id = user_id
        self.role = role
        self.email = email


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> User:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = creds.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub") or payload.get("user_id")
        role = payload.get("role", "user")
        email = payload.get("email")
        if not user_id:
            raise ValueError("No subject in token")
        return User(user_id=str(user_id), role=str(role), email=email)
    except Exception as e:
        logger.exception("JWT decode error: %s", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def require_role(user: User, roles: list[str]):
    if user.role not in roles:
        raise HTTPException(status_code=403, detail="Forbidden")

CurrentUser = Annotated[User, Depends(get_current_user)]
