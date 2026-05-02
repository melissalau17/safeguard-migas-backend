from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from typing import Optional
from app.database import get_db
from app.models.db_models import User, Alert, AlertStatus
from app.models.schemas import HistoryResponse, AlertOut
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/history", tags=["History"])

PERIOD_MAP = {
    "today": timedelta(hours=24),
    "7days": timedelta(days=7),
    "30days": timedelta(days=30),
}


@router.get("", response_model=HistoryResponse)
async def get_history(
    period: str = Query("today", regex="^(today|7days|30days)$"),
    unit: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    since = datetime.utcnow() - PERIOD_MAP.get(period, timedelta(hours=24))

    q = (
        select(Alert)
        .options(selectinload(Alert.assigned_user))
        .where(Alert.detected_at >= since)
        .order_by(desc(Alert.detected_at))
    )

    # Scope operators to their own unit
    if current_user.role == "operator" and current_user.unit:
        q = q.where(Alert.unit == current_user.unit)
    elif unit:
        q = q.where(Alert.unit == unit)

    result = await db.execute(q)
    alerts = result.scalars().all()

    # Stats
    total = len(alerts)
    resolved = sum(1 for a in alerts if a.status == AlertStatus.resolved)
    durations = []
    for a in alerts:
        if a.resolved_at and a.detected_at:
            durations.append((a.resolved_at - a.detected_at).total_seconds() / 60)

    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0

    # Most active unit
    unit_counts: dict[str, int] = {}
    for a in alerts:
        unit_counts[a.unit] = unit_counts.get(a.unit, 0) + 1
    top_unit = max(unit_counts, key=unit_counts.get) if unit_counts else "-"

    return HistoryResponse(
        alerts=[AlertOut.model_validate(a) for a in alerts],
        stats={
            "total": total,
            "resolved": resolved,
            "active": total - resolved,
            "avg_duration_minutes": avg_duration,
            "top_unit": top_unit,
            "period": period,
        },
    )
