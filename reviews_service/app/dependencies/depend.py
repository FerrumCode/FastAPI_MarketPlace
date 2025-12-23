import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger
from prometheus_client import Counter
from env import SECRET_KEY, ALGORITHM, SERVICE_NAME
from app.core.metrics import AUTH_TOKEN_VALIDATION_TOTAL, AUTH_PERMISSION_CHECK_TOTAL



bearer_scheme = HTTPBearer()


def authentication_get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):
    token = credentials.credentials
    AUTH_TOKEN_VALIDATION_TOTAL.labels(service=SERVICE_NAME, result="attempt").inc()
    logger.info("Attempt to authenticate user via bearer token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.info(
            "Successfully authenticated user '{name}' with id={user_id}",
            name=payload.get("sub"),
            user_id=payload.get("id"),
        )
        AUTH_TOKEN_VALIDATION_TOTAL.labels(service=SERVICE_NAME, result="success").inc()
        return {
            "id": payload.get("id"),
            "name": payload.get("sub"),
            "role_id": payload.get("role_id"),
            "role_name": payload.get("role_name"),
            "permissions": payload.get("permissions", []),
        }
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired during authentication attempt")
        AUTH_TOKEN_VALIDATION_TOTAL.labels(service=SERVICE_NAME, result="expired").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        logger.error("Invalid token during authentication attempt")
        AUTH_TOKEN_VALIDATION_TOTAL.labels(service=SERVICE_NAME, result="invalid").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


def permission_required(required_permission: str):
    def _checker(user=Depends(authentication_get_current_user)):
        logger.info(
            "Checking permission '{permission}' for user_id={user_id}",
            permission=required_permission,
            user_id=user.get("id"),
        )
        perms = user.get("permissions") or []
        if required_permission not in perms:
            logger.warning(
                "Permission '{permission}' denied for user_id={user_id}",
                permission=required_permission,
                user_id=user.get("id"),
            )
            AUTH_PERMISSION_CHECK_TOTAL.labels(
                service=SERVICE_NAME,
                result="denied",
                permission=required_permission,
            ).inc()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission}' required"
            )
        AUTH_PERMISSION_CHECK_TOTAL.labels(
            service=SERVICE_NAME,
            result="granted",
            permission=required_permission,
        ).inc()
        logger.info(
            "Permission '{permission}' granted for user_id={user_id}",
            permission=required_permission,
            user_id=user.get("id"),
        )
        return True
    return _checker
