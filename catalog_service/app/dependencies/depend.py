import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from loguru import logger
from prometheus_client import Counter

from env import SECRET_KEY, ALGORITHM, SERVICE_NAME

bearer_scheme = HTTPBearer()

JWT_ACCESS_VALIDATION_TOTAL = Counter(
    "catalog_auth_jwt_access_validation_total",
    "Access JWT validation events",
    ["service", "result"],
)

PERMISSION_CHECKS_TOTAL = Counter(
    "catalog_auth_permission_checks_total",
    "Permission checks based on JWT",
    ["service", "permission", "result"],
)


def authentication_get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):
    token = credentials.credentials
    logger.debug("Authenticating user from access token (catalog service)")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user = {
            "id": payload.get("id"),
            "name": payload.get("sub"),
            "role_id": payload.get("role_id"),
            "role_name": payload.get("role_name"),
            "permissions": payload.get("permissions", []),
        }

        logger.info(
            "User authenticated: id={id}, name={name}, role_id={role_id}, role_name={role_name}",
            id=user["id"],
            name=user["name"],
            role_id=user["role_id"],
            role_name=user["role_name"],
        )

        JWT_ACCESS_VALIDATION_TOTAL.labels(
            service=SERVICE_NAME,
            result="success",
        ).inc()

        return user

    except jwt.ExpiredSignatureError:
        logger.warning("Access token expired (catalog service)")
        JWT_ACCESS_VALIDATION_TOTAL.labels(
            service=SERVICE_NAME,
            result="expired",
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        logger.warning("Invalid access token received (catalog service)")
        JWT_ACCESS_VALIDATION_TOTAL.labels(
            service=SERVICE_NAME,
            result="invalid",
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


def permission_required(required_permission: str):
    def _checker(user = Depends(authentication_get_current_user)):
        perms = user.get("permissions") or []
        user_id = user.get("id")
        user_name = user.get("name")

        if required_permission not in perms:
            logger.warning(
                "Permission check failed: user_id={user_id}, user_name={user_name}, "
                "required_permission='{perm}', user_permissions={perms}",
                user_id=user_id,
                user_name=user_name,
                perm=required_permission,
                perms=perms,
            )
            PERMISSION_CHECKS_TOTAL.labels(
                service=SERVICE_NAME,
                permission=required_permission,
                result="denied",
            ).inc()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission}' required"
            )

        logger.debug(
            "Permission check passed: user_id={user_id}, user_name={user_name}, permission='{perm}'",
            user_id=user_id,
            user_name=user_name,
            perm=required_permission,
        )
        PERMISSION_CHECKS_TOTAL.labels(
            service=SERVICE_NAME,
            permission=required_permission,
            result="granted",
        ).inc()
        return True

    return _checker
