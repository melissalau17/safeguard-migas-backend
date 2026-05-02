from fastapi import APIRouter, Depends
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


@router.get("/status", response_model=DriftSummaryResponse)
async def get_drift_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_supervisor),
):
    """Compute live drift vs training baseline using the last 500 readings."""
    # Fetch recent sensor readings
    result = await db.execute(
        select(SensorReading).order_by(desc(SensorReading.timestamp)).limit(500)
    )
    readings = result.scalars().all()

    if not readings or len(readings) < 10:
        # Return last computed drift from DB
        return await _get_cached_drift(db)

    # Build live window
    live_data = []
    for r in readings:
        row = [getattr(r, f"xmeas_{i}", 0.0) or 0.0 for i in range(1, 42)]
        live_data.append(row)
    live_window = np.array(live_data, dtype=np.float32)

    # Compute drift
    drift_results = ml_service.compute_drift(live_window)

    # Persist to DB
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

    variables = [DriftVariableStatus(**d) for d in drift_results]
    high = sum(1 for v in variables if v.drift_level == "high")
    medium = sum(1 for v in variables if v.drift_level == "medium")
    normal = len(variables) - high - medium

    return DriftSummaryResponse(
        variables=variables,
        total_high=high,
        total_medium=medium,
        total_normal=normal,
        retraining_recommended=high >= 3,
        last_retrain_days_ago=12,
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
    high = sum(1 for v in variables if v.drift_level == "high")
    medium = sum(1 for v in variables if v.drift_level == "medium")
    return DriftSummaryResponse(
        variables=variables,
        total_high=high,
        total_medium=medium,
        total_normal=len(variables) - high - medium,
        retraining_recommended=high >= 3,
        last_retrain_days_ago=None,
        checked_at=datetime.utcnow(),
    )
