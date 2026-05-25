from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.core.database import init_db
from apps.locker_codes.models import LockerCode  # noqa: F401 — registers table
from apps.locker_codes.routers import router as locker_codes_router

app = FastAPI(
    title="Locker Simulation API",
    description="Hệ thống mô phỏng tủ locker — quản lý mã QR AA/BB và xác thực quét mã",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(locker_codes_router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "healthy", "service": "locker-simulation-api", "version": "1.0.0"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": exc.status_code, "message": exc.detail, "data": None},
    )
