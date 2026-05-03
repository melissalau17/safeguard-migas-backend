from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from app.config import settings
from app.database import init_db
from app.services.ml_service import ml_service
from app.services.notification_service import notification_service
from app.services.sensor_simulator import run_simulator
from app.routers import auth, predict, alerts, dashboard, drift, history, metrics

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────
    print("🚀 SafeGuard Migas Backend starting...")
    await init_db()
    ml_service.load()
    notification_service.init()
    # Jalankan simulator sebagai background task
    asyncio.create_task(run_simulator(interval_seconds=5))
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(predict.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)
app.include_router(drift.router)
app.include_router(history.router)
app.include_router(metrics.router)


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