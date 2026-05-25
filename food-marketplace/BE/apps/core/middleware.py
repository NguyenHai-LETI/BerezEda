from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from sqlmodel import select
from starlette.middleware.base import BaseHTTPMiddleware

from apps.auth.models.revoked_token import RevokedToken
from apps.auth.services import decode_access_token
from apps.core.database import get_session
from apps.core.logging import logger
from apps.users.models import User

from .config import API_PREFIX
from .constants import (
    ALLOWED_GLOBAL_UNAUTHENTICATED_PATHS,
    ALLOWED_UNAUTHENTICATED_PATHS,
    ALLOWED_UNAUTHENTICATED_PREFIXES,
)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        if method == "OPTIONS":
            return await call_next(request)

        # Static files — no auth required
        if path.startswith("/uploads/"):
            return await call_next(request)

        if path in ALLOWED_GLOBAL_UNAUTHENTICATED_PATHS:
            if method == ALLOWED_GLOBAL_UNAUTHENTICATED_PATHS[path]:
                return await call_next(request)

        # Exact match
        for pattern_path, allowed_method in ALLOWED_UNAUTHENTICATED_PATHS.items():
            full_path = API_PREFIX + pattern_path
            if path == full_path and method == allowed_method:
                return await call_next(request)

        # Prefix match (for dynamic routes like /combos/{id}, /shops/{id})
        # Any path segment that requires authentication, even under public prefixes
        _AUTH_REQUIRED_SEGMENTS = frozenset({"my", "owner", "favorites", "import-csv", "units"})
        for prefix_path, allowed_method in ALLOWED_UNAUTHENTICATED_PREFIXES:
            full_prefix = API_PREFIX + prefix_path
            if path.startswith(full_prefix) and method == allowed_method:
                remainder = path[len(full_prefix):]
                segments = [s for s in remainder.split("/") if s]
                if not any(seg in _AUTH_REQUIRED_SEGMENTS for seg in segments):
                    # Optional auth: if a Bearer token is present, try to authenticate
                    # and set request.state.user so protected sub-routes still work.
                    # If no token or token is invalid, silently continue as anonymous.
                    auth_header = request.headers.get("Authorization")
                    if auth_header and auth_header.startswith("Bearer "):
                        try:
                            tok = auth_header.split(" ", 1)[1]
                            user_data = decode_access_token(tok)
                            jti = user_data.get("jti")
                            user_id = user_data.get("sub")
                            db = next(get_session())
                            try:
                                revoked = (
                                    db.exec(select(RevokedToken).where(RevokedToken.jti == jti)).first()
                                    if jti else None
                                )
                                if not revoked:
                                    u = db.exec(
                                        select(User).where(User.id == user_id, User.is_active == True)
                                    ).first()
                                    if u:
                                        request.state.user = u
                            finally:
                                db.close()
                        except Exception:
                            pass
                    return await call_next(request)

        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(
                    status_code=401, detail="Authorization header required"
                )

            token = auth_header.split(" ", 1)[1]
            user_data = decode_access_token(token)
            jti = user_data.get("jti")
            user_id = user_data.get("sub")

            db = next(get_session())
            try:
                if jti:
                    revoked = db.exec(
                        select(RevokedToken).where(RevokedToken.jti == jti)
                    ).first()
                    if revoked:
                        raise HTTPException(status_code=401, detail="Token revoked")

                user = db.exec(
                    select(User).where(User.id == user_id, User.is_active == True)
                ).first()

                if not user:
                    logger.warning(
                        "Authentication failed: invalid token or inactive user sub=%s",
                        user_id,
                    )
                    raise HTTPException(
                        status_code=401, detail="Token is invalid or user inactive"
                    )
                request.state.user = user
            finally:
                db.close()

        except HTTPException as exc:
            logger.warning("Authentication failed for %s: %s", path, exc.detail)
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "status": exc.status_code,
                    "message": exc.detail,
                    "data": None,
                },
            )
        except Exception as e:
            logger.error("Authentication error for %s: %s", path, str(e))
            return JSONResponse(
                status_code=401,
                content={
                    "status": 401,
                    "message": "Authentication failed",
                    "data": None,
                },
            )

        response = await call_next(request)
        return response
