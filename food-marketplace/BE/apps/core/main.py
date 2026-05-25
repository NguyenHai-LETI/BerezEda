from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os

from apps.core.config import API_PREFIX, UPLOAD_DIR
from apps.core.database import init_db
from apps.core.error_middleware import ErrorHandlerMiddleware
from apps.core.middleware import AuthMiddleware
from apps.core.schemas import ErrorResponse

# Import all models (table creation)
from apps.core.models import *  # noqa

# Routers
from apps.auth.routers import router as auth_router
from apps.internal.routers import router as internal_router
from apps.users.routers import router as users_router
from apps.shops.routers import router as shops_router
from apps.products.routers import router as products_router
from apps.lockers.routers import router as lockers_router
from apps.combos.routers import router as combos_router
from apps.orders.routers import router as orders_router
from apps.payments.routers import router as payments_router, webhook_router as payments_webhook_router
from apps.devices.routers import router as devices_router
from apps.notifications.routers import router as notifications_router
from apps.reviews.routers import router as reviews_router
from apps.favorites.routers import router as favorites_router
from apps.sales_management.routers import router as sales_router

from apps.scheduler.scheduler import scheduler, reschedule_all_on_startup
from apps.integrations.firebase_client import firebase_service

app = FastAPI(
    title="БережЕда API",
    description="Маркетплейс продуктов с доставкой через ячейки-холодильники",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Static files for uploads
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)

# Register routers
prefix = API_PREFIX
app.include_router(auth_router, prefix=f"{prefix}/auth")
app.include_router(users_router, prefix=f"{prefix}/users")
app.include_router(shops_router, prefix=f"{prefix}")
app.include_router(products_router, prefix=f"{prefix}")
app.include_router(lockers_router, prefix=f"{prefix}")
app.include_router(combos_router, prefix=f"{prefix}")
app.include_router(orders_router, prefix=f"{prefix}")
app.include_router(payments_router, prefix=f"{prefix}")
app.include_router(payments_webhook_router, prefix=f"{prefix}")
app.include_router(devices_router, prefix=f"{prefix}")
app.include_router(notifications_router, prefix=f"{prefix}")
app.include_router(reviews_router, prefix=f"{prefix}")
app.include_router(favorites_router, prefix=f"{prefix}")
app.include_router(sales_router, prefix=f"{prefix}")
app.include_router(internal_router, prefix=f"{prefix}")


@app.on_event("startup")
def on_startup():
    init_db()
    firebase_service.init()
    scheduler.start()
    reschedule_all_on_startup()


@app.on_event("shutdown")
def on_shutdown():
    if scheduler.running:
        scheduler.shutdown(wait=False)


@app.get("/health")
def health():
    return {"status": "healthy", "service": "berezh-eda-api", "version": "1.0.0"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": exc.status_code, "message": exc.detail, "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    msg = exc.errors()[0]["msg"] if exc.errors() else "Некорректные данные запроса"
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(status=400, message=msg, error_code="VALIDATION_ERROR", errors=exc.errors()).model_dump(),
    )
