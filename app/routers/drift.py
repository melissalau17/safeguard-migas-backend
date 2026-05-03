from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timedelta
import numpy as np
from app.database import get_db
from app.models.db_models import User, SensorReading, DriftRecord
from app.models.schemas import DriftSummaryResponse, DriftVariableStatus
from app.services.auth_service import get_current_user, require_supervisor
from app.services.ml_service import ml_service

router = APIRouter(prefix="/drift", tags=["Data Drift"])

PERIOD_MAP = {
    "live": (500, None),          # last 500 readings, no time filter
    "1h":   (500, timedelta(hours=1)),
    "24h":  (500, timedelta(hours=24)),
}


@router.get("/status", response_model=DriftSummaryResponse)
async def get_drift_status(
    period: str = Query("live", regex="^(live|1h|24h)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_supervisor),
):
    """Compute live drift vs training baseline."""
    limit, delta = PERIOD_MAP.get(period, (500, None))

    q = select(SensorReading).order_by(desc(SensorReading.timestamp)).limit(limit)
    if delta:
        since = datetime.utcnow() - delta
        q = q.where(SensorReading.timestamp >= since)

    result = await db.execute(q)
    readings = result.scalars().all()

    if not readings or len(readings) < 10:
        return await _get_cached_drift(db)

    # Build live window
    live_data = []
    for r in readings:
        row = [getattr(r, f"xmeas_{i}", 0.0) or 0.0 for i in range(1, 42)]
        live_data.append(row)
    live_window = np.array(live_data, dtype=np.float32)

    # Compute drift
    drift_results = ml_service.compute_drift(live_window)

    # Persist to DB (hanya untuk period live)
    if period == "live":
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

    now = datetime.utcnow()
    variables = [DriftVariableStatus(**d) for d in drift_results]
    high   = sum(1 for v in variables if v.drift_level == "high")
    medium = sum(1 for v in variables if v.drift_level == "medium")
    normal = len(variables) - high - medium

    # Get last retrain days
    last_retrain_days = await _get_last_retrain_days(db)

    return DriftSummaryResponse(
        variables=variables,
        total_high=high,
        total_medium=medium,
        total_normal=normal,
        retraining_recommended=high >= 3,
        last_retrain_days_ago=last_retrain_days,
        checked_at=now,
    )


async def _get_cached_drift(db: AsyncSession) -> DriftSummaryResponse:
    """Return the most recent cached drift records."""
    result = await db.execute(
        select(DriftRecord).order_by(desc(DriftRecord.checked_at)).limit(52)
    )
    records = result.scalars().all()
    variables = [
        DriftVariableStatus(
            variable_name=r.variable_name,
            ks_statistic=r.ks_statistic,
            ks_pvalue=r.ks_pvalue,
            psi_score=r.psi_score,
            drift_level=r.drift_level,
        )
        for r in records
    ]
    high   = sum(1 for v in variables if v.drift_level == "high")
    medium = sum(1 for v in variables if v.drift_level == "medium")
    normal = len(variables) - high - medium

    last_retrain_days = await _get_last_retrain_days(db)

    return DriftSummaryResponse(
        variables=variables,
        total_high=high,
        total_medium=medium,
        total_normal=normal,
        retraining_recommended=high >= 3,
        last_retrain_days_ago=last_retrain_days,
        checked_at=datetime.utcnow(),
    )


async def _get_last_retrain_days(db: AsyncSession) -> int | None:
    """Get how many days ago the last retrain happened from DriftRecord."""
    result = await db.execute(
        select(DriftRecord.checked_at)
        .order_by(DriftRecord.checked_at)
        .limit(1)
    )
    oldest = result.scalar_one_or_none()
    if oldest is None:
        return None
    delta = datetime.utcnow() - oldest
    return delta.days