import jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from datetime import datetime, timezone
from loguru import logger
from env import SECRET_KEY, ALGORITHM


class JWTMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        public_paths = ["/auth", "/docs", "/openapi.json", "/redoc", "/favicon.ico"]
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)

        logger.info(
            "Checking JWT for request. path='{path}', client='{client}'",
            path=request.url.path,
            client=request.client.host if request.client else None,
        )

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning(
                "Attempt to access without a valid Authorization header. path='{path}'",
                path=request.url.path,
            )
            return JSONResponse({"detail": "Missing or invalid token"}, status_code=401)

        token = auth_header.split(" ")[1]

        redis = getattr(request.app.state, "redis", None)
        if redis:
            if await redis.get(f"bl_{token}"):
                logger.warning(
                    "Attempt to access with a blacklisted JWT token. path='{path}'",
                    path=request.url.path,
                )
                return JSONResponse({"detail": "Token is blacklisted"}, status_code=401)

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                logger.warning(
                    "Attempt to access with an expired JWT token. path='{path}'",
                    path=request.url.path,
                )
                return JSONResponse({"detail": "Token expired"}, status_code=401)

            request.state.user = payload
            logger.info(
                "JWT token successfully validated. user_id={user_id}, path='{path}'",
                user_id=payload.get("id"),
                path=request.url.path,
            )

        except jwt.ExpiredSignatureError:
            logger.warning(
                "Attempt to access with an expired JWT token (ExpiredSignatureError). path='{path}'",
                path=request.url.path,
            )
            return JSONResponse({"detail": "Token expired"}, status_code=401)
        except jwt.InvalidTokenError:
            logger.error(
                "Attempt to access with an invalid JWT token. path='{path}'",
                path=request.url.path,
            )
            return JSONResponse({"detail": "Invalid token"}, status_code=401)

        return await call_next(request)
