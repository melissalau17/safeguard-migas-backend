from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from app.database import get_db
from app.models.db_models import User, Alert, AlertStatus, AlertSeverity
from app.models.schemas import DashboardResponse, GlobalRiskSummary, FaultProbability, AlertOut
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/live", response_model=DashboardResponse)
async def get_live_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Active alerts in last 24h
    since = datetime.utcnow() - timedelta(hours=24)
    q = (
        select(Alert)
        .options(selectinload(Alert.assigned_user))
        .where(Alert.status == AlertStatus.active, Alert.detected_at >= since)
        .order_by(desc(Alert.detected_at))
    )
    # Scope operators to their unit
    if current_user.role == "operator" and current_user.unit:
        q = q.where(Alert.unit == current_user.unit)

    result = await db.execute(q)
    active_alerts = result.scalars().all()

    # Global risk
    if not active_alerts:
        risk_status = "NORMAL"
        confidence = 0.0
        detected_minutes = None
    else:
        top = active_alerts[0]
        confidence = top.confidence
        risk_status = "CRITICAL" if top.severity == AlertSeverity.critical else "WARNING"
        detected_minutes = int((datetime.utcnow() - top.detected_at).total_seconds() / 60)

    # Top fault probabilities (from active alerts)
    fault_probs = []
    seen = set()
    for a in active_alerts:
        if a.fault_class not in seen:
            fault_probs.append(FaultProbability(
                fault_class=a.fault_class,
                label=a.fault_label,
                probability=a.confidence,
            ))
            seen.add(a.fault_class)

    # Top variables from most recent alert
    top_vars = []
    if active_alerts:
        import json
        raw = active_alerts[0].top_variables
        if raw:
            try:
                top_vars = json.loads(raw)
            except Exception:
                pass

    return DashboardResponse(
        global_risk=GlobalRiskSummary(
            status=risk_status,
            confidence=confidence,
            active_anomaly_count=len(active_alerts),
            detected_minutes_ago=detected_minutes,
        ),
        top_faults=fault_probs[:3],
        top_variables=top_vars[:5],
        active_alerts=[AlertOut.model_validate(a) for a in active_alerts[:5]],
    )
