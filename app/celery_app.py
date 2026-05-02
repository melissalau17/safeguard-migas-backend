"""
Celery background tasks.
Handles periodic sensor polling and scheduled drift checks.

Start worker:
    celery -A app.celery_app worker --loglevel=info
    celery -A app.celery_app beat --loglevel=info   # for periodic tasks
"""
from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "safeguard_migas",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jakarta",
    enable_utc=True,
    beat_schedule={
        # Run drift check every 5 minutes
        "drift-check": {
            "task": "app.celery_app.run_drift_check",
            "schedule": 300.0,
        },
        # Cleanup resolved alerts older than 30 days
        "cleanup-old-alerts": {
            "task": "app.celery_app.cleanup_old_alerts",
            "schedule": crontab(hour=2, minute=0),  # 2 AM daily
        },
    },
)


@celery_app.task(name="app.celery_app.run_drift_check")
def run_drift_check():
    """Periodic drift computation — runs independently of API requests."""
    import asyncio
    from app.database import AsyncSessionLocal
    from app.services.ml_service import ml_service
    from app.models.db_models import SensorReading, DriftRecord
    from sqlalchemy import select, desc
    from datetime import datetime
    import numpy as np

    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(SensorReading).order_by(desc(SensorReading.timestamp)).limit(500)
            )
            readings = result.scalars().all()
            if len(readings) < 10:
                return

            live_data = []
            for r in readings:
                row = [getattr(r, f"xmeas_{i}", 0.0) or 0.0 for i in range(1, 42)]
                live_data.append(row)
            live_window = np.array(live_data, dtype=np.float32)

            drift_results = ml_service.compute_drift(live_window)
            now = datetime.utcnow()
            for d in drift_results:
                rec = DriftRecord(
                    variable_name=d["variable_name"],
                    ks_statistic=d["ks_statistic"],
                    ks_pvalue=d["ks_pvalue"],
                    psi_score=d["psi_score"],
                    drift_level=d["drift_level"],
                    checked_at=now,
                )
                db.add(rec)
            await db.commit()

    asyncio.run(_run())
    return "Drift check complete"


@celery_app.task(name="app.celery_app.cleanup_old_alerts")
def cleanup_old_alerts():
    """Delete resolved alerts older than 30 days to keep DB lean."""
    import asyncio
    from app.database import AsyncSessionLocal
    from app.models.db_models import Alert, AlertStatus
    from sqlalchemy import delete
    from datetime import datetime, timedelta

    async def _run():
        cutoff = datetime.utcnow() - timedelta(days=30)
        async with AsyncSessionLocal() as db:
            await db.execute(
                delete(Alert).where(
                    Alert.status == AlertStatus.resolved,
                    Alert.resolved_at < cutoff,
                )
            )
            await db.commit()

    asyncio.run(_run())
    return "Old alerts cleaned up"
