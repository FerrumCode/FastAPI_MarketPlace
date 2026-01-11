import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from env import SECRET_KEY, ALGORITHM, SERVICE_NAME

from app.db_depends import get_db
from app.service.orders import get_order as svc_get_order
from app.core.metrics import AUTH_TOKEN_VALIDATION_TOTAL, PERMISSION_CHECK_TOTAL


bearer_scheme = HTTPBearer()


def authentication_get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    AUTH_TOKEN_VALIDATION_TOTAL.labels(
        service=SERVICE_NAME,
        result="attempt",
    ).inc()
    token = credentials.credentials
    logger.info("Validating access token for current user")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.info(
            "Access token successfully validated for user_id='{user_id}', name='{name}'",
            user_id=payload.get("id"),
            name=payload.get("sub"),
        )
        AUTH_TOKEN_VALIDATION_TOTAL.labels(
            service=SERVICE_NAME,
            result="success",
        ).inc()
        return {
            "id": payload.get("id"),
            "name": payload.get("sub"),
            "role_id": payload.get("role_id"),
            "role_name": payload.get("role_name"),
            "permissions": payload.get("permissions", []),
        }
    except jwt.ExpiredSignatureError:
        logger.warning("Access token expired during validation")
        AUTH_TOKEN_VALIDATION_TOTAL.labels(
            service=SERVICE_NAME,
            result="expired",
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        logger.error("Invalid access token during validation")
        AUTH_TOKEN_VALIDATION_TOTAL.labels(
            service=SERVICE_NAME,
            result="invalid",
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


def permission_required(required_permission: str):
    def _checker(user=Depends(authentication_get_current_user)):
        perms = user.get("permissions") or []
        logger.info(
            "Checking permission '{required_permission}' for user_id='{user_id}'. Permissions={perms}",
            required_permission=required_permission,
            user_id=user.get("id"),
            perms=perms,
        )
        if required_permission not in perms:
            logger.warning(
                "Permission '{required_permission}' denied for user_id='{user_id}'",
                required_permission=required_permission,
                user_id=user.get("id"),
            )
            PERMISSION_CHECK_TOTAL.labels(
                service=SERVICE_NAME,
                permission=required_permission,
                result="denied",
            ).inc()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission}' required",
            )
        logger.info(
            "Permission '{required_permission}' granted for user_id='{user_id}'",
            required_permission=required_permission,
            user_id=user.get("id"),
        )
        PERMISSION_CHECK_TOTAL.labels(
            service=SERVICE_NAME,
            permission=required_permission,
            result="granted",
        ).inc()
        return True

    return _checker
