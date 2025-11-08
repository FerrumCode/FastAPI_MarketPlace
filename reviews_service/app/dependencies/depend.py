from typing import Any, Dict
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.service.reviews import get_review_by_id as svc_get_review_by_id
from env import SECRET_KEY, ALGORITHM


bearer_scheme = HTTPBearer()


def authentication_get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "id": payload.get("id"),
            "name": payload.get("sub"),
            "role_id": payload.get("role_id"),
            "role_name": payload.get("role_name"),
            "permissions": payload.get("permissions", []),
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


def permission_required(required_permission: str):
    def _checker(user=Depends(authentication_get_current_user)):
        perms = user.get("permissions") or []
        if required_permission not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission}' required"
            )
        return True
    return _checker


async def user_owner_access_checker(
    review_id: str,
    current_user: Dict[str, Any] = Depends(authentication_get_current_user),
) -> None:
    role_name = (current_user.get("role_name") or "").strip().lower()
    if role_name != "user":
        return

    try:
        current_user_uuid = (
            current_user["id"]
            if isinstance(current_user["id"], UUID)
            else UUID(str(current_user["id"]))
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user id in token",
        )

    review = await svc_get_review_by_id(review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    review_user_id_raw = getattr(review, "user_id", None) or review.get("user_id")
    if review_user_id_raw is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Review has no owner")

    try:
        review_user_uuid = review_user_id_raw if isinstance(review_user_id_raw, UUID) else UUID(str(review_user_id_raw))
    except Exception:
        if str(review_user_id_raw) != str(current_user_uuid):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not allowed to access this review (owner only, role 'user')",
            )
        return

    if review_user_uuid != current_user_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this review (owner only, role 'user')",
        )
