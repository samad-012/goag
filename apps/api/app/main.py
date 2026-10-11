from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import admin, attendance, dashboard, email, inventory, me, production

settings = get_settings()
app = FastAPI(title="GOAG API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)
app.include_router(me.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(production.router, prefix="/api/v1")
app.include_router(attendance.router, prefix="/api/v1")
app.include_router(email.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")


@app.get("/healthz", tags=["health"])
def healthz() -> dict[str, str]:
    return {"status": "ok"}
