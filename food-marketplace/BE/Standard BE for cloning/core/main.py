from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer
from sqlmodel import Session

from apps.admin_sales_management.routers import router as admin_sales_management_router
from apps.auth.routers import router as auth_router
from apps.core.config import API_PREFIX
from apps.core.database import get_session
from apps.core.error_middleware import ErrorHandlerMiddleware
from apps.core.middleware import AuthMiddleware

# Import all models so SQLModel can resolve relationships
from apps.core.models import *  # noqa - This imports all models in correct order
from apps.core.schemas import ErrorResponse
from apps.devices.routers import devices_router
from apps.external_api.routers import router as external_router
from apps.favorites.routers import router as favorites_router
from apps.integrations.aws.routers import router as aws_router
from apps.lockers.routers import router as lockers_router
from apps.mynaportal.routers import router as mynaportal_router
from apps.notifications.routers import router as notifications_router
from apps.orders.routers import router as orders_router
from apps.orders.routers import webhook_router as order_webhook_router
from apps.products.routers import combos_router, product_master_router
from apps.purchase.router import callback_router as purchase_callback_router
from apps.purchase.router import router as purchase_router
from apps.qrcode.routers import router as qrcode_router
from apps.revenue_management.routers import router as revenue_management_router
from apps.reviews.routers import router as reviews_router
from apps.sales_management.routers import router as sales_management_router
from apps.shops.routers import router as shops_router
from apps.users.routers import router as users_router

app = FastAPI(
    title="Wakeatte API",
    description="API documentation for Wakeatte backend service.",
    version="1.0.0",
)

security = HTTPBearer()

# Add error handling middleware (should be first to catch all errors)
app.add_middleware(ErrorHandlerMiddleware)

# Allow all origins for testing; restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuthMiddleware)

app.include_router(auth_router, prefix=f"{API_PREFIX}/auth")

app.include_router(users_router, prefix=f"{API_PREFIX}/users")
app.include_router(purchase_router, prefix=f"{API_PREFIX}/purchase")

app.include_router(shops_router, prefix=f"{API_PREFIX}/shops")
app.include_router(combos_router, prefix=f"{API_PREFIX}/combos")
app.include_router(product_master_router, prefix=f"{API_PREFIX}/product-master")
app.include_router(orders_router, prefix=f"{API_PREFIX}/orders")
app.include_router(order_webhook_router, prefix=f"{API_PREFIX}/orders/webhooks")

app.include_router(favorites_router, prefix=API_PREFIX)
app.include_router(reviews_router, prefix=f"{API_PREFIX}/reviews")
app.include_router(revenue_management_router, prefix=f"{API_PREFIX}/revenue-management")
app.include_router(
    admin_sales_management_router, prefix=f"{API_PREFIX}/admin-sales-management"
)
app.include_router(sales_management_router, prefix=f"{API_PREFIX}/sales-management")
app.include_router(devices_router, prefix=f"{API_PREFIX}/devices")
app.include_router(lockers_router, prefix=f"{API_PREFIX}/lockers")
app.include_router(qrcode_router, prefix=f"{API_PREFIX}/qrcodes")

app.include_router(notifications_router, prefix=f"{API_PREFIX}/notifications")
app.include_router(purchase_callback_router, prefix=f"{API_PREFIX}/purchase-callbacks")
app.include_router(external_router, prefix=f"{API_PREFIX}/external")
app.include_router(mynaportal_router, prefix=API_PREFIX)
app.include_router(aws_router, prefix=API_PREFIX)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancer and monitoring"""
    return {
        "status": "healthy",
        "service": "wakeatte-api",
        "version": "1.0.0",
        "timestamp": "2025-10-21T00:00:00Z",
    }


# Test error endpoint for Google Chat notification testing
@app.get(f"{API_PREFIX}/test-error")
async def test_error_endpoint():
    """Test endpoint that triggers a 500 error for Google Chat notification testing."""
    # This will trigger an unhandled exception that should be caught by ErrorHandlerMiddleware
    raise Exception(
        "Test 500 error for Google Chat notification - this is intentional!"
    )


# Add mynumber callback route without prefix for direct access
@app.get("/mynumber", response_class=HTMLResponse)
async def mynumber_callback_direct(
    state: Optional[str] = Query(None),
    code: Optional[str] = Query(None),
    db: Session = Depends(get_session),
):
    """Direct mynumber callback route accessible at /mynumber"""
    from apps.integrations.branchio.deeplink import create_branchio_deeplink
    from apps.mynaportal.services import (
        generate_service_link_html,
        process_mynumber_callback,
    )

    try:
        message, deeplink = await process_mynumber_callback(db, state, code)
        html_content = generate_service_link_html(message, deeplink)
        return HTMLResponse(content=html_content, status_code=200)

    except Exception:
        # Fallback error message
        error_message = "システムエラーが発生しました。もう一度お試しください。"

        # Create error deeplink using Branch.io
        error_deeplink_data = {"data": {"message": error_message, "type": "mynumber"}}
        error_deeplink = create_branchio_deeplink(error_deeplink_data)

        error_html = generate_service_link_html(error_message, error_deeplink)
        return HTMLResponse(content=error_html, status_code=500)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            status=exc.status_code,
            message=exc.detail,
            error_code=exc.__class__.__name__.upper(),
            errors=None,
        ).model_dump(),
    )


@app.exception_handler(ValueError)
async def value_error_exception_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            status=400,
            message=str(exc),
            error_code="VALIDATION_ERROR",
            errors=[{"msg": str(exc), "type": "value_error"}],
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Extract the first error message from the errors list
    msg = exc.errors()[0]["msg"] if exc.errors() else "Invalid request data."

    # Convert errors to JSON serializable format
    serializable_errors = []
    for error in exc.errors():
        serializable_error = {
            "loc": list(error.get("loc", [])),
            "msg": str(error.get("msg", "")),
            "type": str(error.get("type", "")),
        }
        # Add input if it exists and is serializable
        if "input" in error:
            try:
                serializable_error["input"] = error["input"]
            except (TypeError, ValueError):
                serializable_error["input"] = str(error["input"])
        serializable_errors.append(serializable_error)

    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            status=400,
            message=msg,
            error_code="VALIDATION_ERROR",
            errors=serializable_errors,
        ).model_dump(),
    )
