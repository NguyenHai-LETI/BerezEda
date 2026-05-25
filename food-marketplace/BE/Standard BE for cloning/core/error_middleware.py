import logging
import traceback

import httpx
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from apps.core.utils import get_current_time

from .config import ENVIRONMENT, GOOGLE_CHAT_WEBHOOK_URL

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # Log the error with structured data for CloudWatch
            await self._log_error_to_cloudwatch(request, exc)

            # Send to Google Chat for staging and production environments
            if ENVIRONMENT.lower() in ["staging", "production"]:
                await self._send_error_to_google_chat(request, exc)

            # Return 500 response
            return Response(
                content="Internal Server Error",
                status_code=500,
                media_type="text/plain",
            )

    async def _log_error_to_cloudwatch(self, request: Request, exception: Exception):
        """Log structured error data to CloudWatch"""
        try:
            # Get request details
            client_ip = request.client.host if request.client else "Unknown"
            forwarded_for = request.headers.get("x-forwarded-for")
            if forwarded_for:
                client_ip = forwarded_for.split(",")[0].strip()

            # Create structured log data
            error_data = {
                "timestamp": get_current_time().isoformat(),
                "environment": ENVIRONMENT,
                "error_type": type(exception).__name__,
                "error_message": str(exception),
                "request_method": request.method,
                "request_url": str(request.url),
                "request_path": request.url.path,
                "client_ip": client_ip,
                "user_agent": request.headers.get("user-agent", "Unknown"),
                "status_code": 500,
                "traceback": traceback.format_exc(),
            }

            # Log with structured data that CloudWatch can parse
            logger.error(
                f"Unhandled 500 Error: {exception}",
                extra={
                    "error_data": error_data,
                    "request_id": getattr(request.state, "request_id", "unknown"),
                },
                exc_info=True,
            )

        except Exception as log_error:
            # Fallback to basic logging if structured logging fails
            logger.error(f"Failed to log structured error data: {log_error}")
            logger.error(f"Original exception: {exception}", exc_info=True)

    async def _send_error_to_google_chat(self, request: Request, exception: Exception):
        """Send error notification to Google Chat for staging environment"""
        try:
            # Prepare error details
            error_message = self._format_error_message(request, exception)

            # Send to Google Chat
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    GOOGLE_CHAT_WEBHOOK_URL, json={"text": error_message}, timeout=5.0
                )

                if response.status_code == 200:
                    logger.info("Error notification sent to Google Chat successfully")
                else:
                    logger.error(
                        f"Failed to send error notification to Google Chat: {response.status_code}"
                    )

        except Exception as chat_error:
            logger.error(f"Failed to send error to Google Chat: {chat_error}")

    def _format_error_message(self, request: Request, exception: Exception) -> str:
        """Format error message for Google Chat"""
        timestamp = get_current_time().strftime("%Y-%m-%d %H:%M:%S")

        # Get request details
        method = request.method
        url = str(request.url)
        user_agent = request.headers.get("user-agent", "Unknown")

        # Get client IP
        client_ip = request.client.host if request.client else "Unknown"

        # Get forwarded IP if behind proxy
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        # Format traceback
        error_traceback = "".join(
            traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
        )

        # Create formatted message
        message = f"""🚨 **500 Error in Staging Environment**

**Time:** {timestamp}
**Method:** {method}
**URL:** {url}
**Client IP:** {client_ip}
**User Agent:** {user_agent}

**Error:** {str(exception)}

**Traceback:**
```
{error_traceback}
```

**Environment:** {ENVIRONMENT}
"""

        return message
