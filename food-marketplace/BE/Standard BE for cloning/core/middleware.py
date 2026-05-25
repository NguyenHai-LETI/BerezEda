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
    EXCLUDED_FROM_WILDCARD_PATTERNS,
)


def _is_path_excluded(path: str, method: str) -> bool:
    """
    Check if a path is excluded from wildcard patterns.

    Args:
        path: Full path with API prefix (e.g., /v1/combos/ or /api/combos/)
        method: HTTP method

    Returns:
        True if path is excluded and requires authentication
    """
    # EXCLUDED_FROM_WILDCARD_PATTERNS keys are paths without API prefix
    # We need to check if the current path (with prefix) matches any excluded path
    for excluded_pattern, excluded_methods in EXCLUDED_FROM_WILDCARD_PATTERNS.items():
        # Build full excluded path with API prefix
        full_excluded_path = API_PREFIX + excluded_pattern

        # Normalize paths (remove trailing slashes for comparison)
        normalized_path = path.rstrip("/")
        normalized_excluded = full_excluded_path.rstrip("/")

        # Check exact match
        if normalized_path == normalized_excluded:
            if isinstance(excluded_methods, str):
                excluded_methods = [excluded_methods]
            if method in excluded_methods:
                return True

    return False


def _matches_wildcard_pattern(path: str, pattern: str, method: str) -> bool:
    """
    Check if path matches a wildcard pattern and is not excluded.

    Args:
        path: Full request path (e.g., /v1/combos/123)
        pattern: Pattern from ALLOWED_UNAUTHENTICATED_PATHS (e.g., /combos/*)
        method: HTTP method

    Returns:
        True if path matches pattern and is allowed (not excluded)
    """
    # Add API prefix to pattern for matching
    API_PREFIX + pattern

    # Handle patterns with /*/ in the middle (e.g., /shops/*/combos)
    if "/*/" in pattern:
        # Split pattern into prefix and suffix around /*
        pattern_prefix, pattern_suffix = pattern.split("/*/", 1)
        full_prefix = API_PREFIX + pattern_prefix
        full_suffix = "/" + pattern_suffix

        if path.startswith(full_prefix + "/") and path.endswith(full_suffix):
            # Extract the segment between prefix and suffix
            remaining = path[len(full_prefix) + 1 : -len(full_suffix)]
            # Allow if there's exactly one segment (no "/" in remaining)
            if remaining and "/" not in remaining:
                # Check if this exact path is excluded
                if _is_path_excluded(path, method):
                    return False
                return True
        return False

    # Handle patterns ending with /* (e.g., /combos/*)
    if pattern.endswith("/*"):
        base_pattern = pattern[:-2]  # Remove "/*"
        full_base = API_PREFIX + base_pattern

        if path.startswith(full_base + "/"):
            # Check if this exact path is excluded from wildcard patterns
            if _is_path_excluded(path, method):
                return False

            # Extract remaining path after base
            remaining_path = path[len(full_base) + 1 :]

            # Rule: allow 1 segment (do not allow nested paths)
            if remaining_path and "/" not in remaining_path:
                return True

    return False


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # Allow all OPTIONS requests for CORS preflight
        if method == "OPTIONS":
            return await call_next(request)

        # 1. Check global paths (no prefix required)
        # These paths are always allowed regardless of environment
        if (
            path in ALLOWED_GLOBAL_UNAUTHENTICATED_PATHS
            and method == ALLOWED_GLOBAL_UNAUTHENTICATED_PATHS[path]
        ):
            return await call_next(request)

        # 2. Check exact path matches with API prefix
        # These paths use API_PREFIX (staging: /api, production: /v1)
        for pattern_path, allowed_method in ALLOWED_UNAUTHENTICATED_PATHS.items():
            # Skip wildcard patterns for exact match check
            if "/*" in pattern_path:
                continue

            full_path = API_PREFIX + pattern_path
            if path == full_path and method == allowed_method:
                return await call_next(request)

        # 3. Check wildcard pattern matches with API prefix
        for pattern_path, allowed_method in ALLOWED_UNAUTHENTICATED_PATHS.items():
            if method != allowed_method:
                continue

            # Only process wildcard patterns
            if "/*" not in pattern_path:
                continue

            if _matches_wildcard_pattern(path, pattern_path, method):
                return await call_next(request)

        try:
            auth_header = request.headers.get("Authorization")

            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(
                    status_code=401, detail="Authorization header required"
                )

            token = auth_header.split(" ", 1)[1]
            user_data = decode_access_token(token)

            # Check blacklist by jti if present
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
                        f"Authentication failed: Invalid token or inactive user for token sub: {user_id}"
                    )
                    raise HTTPException(
                        status_code=401, detail="Token is invalid or user inactive"
                    )
                request.state.user = user
            finally:
                db.close()

        except HTTPException as exc:
            logger.warning(f"Authentication failed for {path}: {exc.detail}")
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "status": exc.status_code,
                    "message": exc.detail,
                    "data": None,
                },
            )
        except Exception as e:
            logger.error(f"Authentication error for {path}: {str(e)}")
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
