from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import init_db
from app.services.ml_service import ml_service
from app.services.notification_service import notification_service
from app.routers import auth, predict, alerts, dashboard, drift, history


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────
    print("🚀 SafeGuard Migas Backend starting...")
    await init_db()
    ml_service.load()
    notification_service.init()
    print("✅ All services ready")
    yield
    # ── Shutdown ───────────────────────────────────────────
    print("🛑 Shutting down...")


app = FastAPI(
    title="SafeGuard Migas API",
    description="Backend middleware for TEP anomaly detection system",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Flutter app (update origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(predict.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)
app.include_router(drift.router)
app.include_router(history.router)


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "service": "SafeGuard Migas API", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "ml_model_loaded": ml_service._loaded,
        "environment": settings.APP_ENV,
    }
