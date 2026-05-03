from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import Optional
from app.database import get_db
from app.models.db_models import User, Alert, AlertStatus
from app.models.schemas import AlertOut, AlertActionRequest, AssignAlertRequest
from app.services.auth_service import get_current_user, require_supervisor
from app.models.schemas import AlertOut, AlertActionRequest, AssignAlertRequest, BroadcastAlertRequest
from app.services.notification_service import notification_service
router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=list[AlertOut])
async def get_alerts(
    status: Optional[AlertStatus] = None,
    unit: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get alerts. Operators see their unit only; supervisors see all."""
    q = select(Alert).options(selectinload(Alert.assigned_user)).order_by(desc(Alert.detected_at))

    # Operators are scoped to their unit
    if current_user.role == "operator" and current_user.unit:
        q = q.where(Alert.unit == current_user.unit)
    elif unit:
        q = q.where(Alert.unit == unit)

    if status:
        q = q.where(Alert.status == status)

    q = q.limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{alert_id}", response_model=AlertOut)
async def get_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Alert).options(selectinload(Alert.assigned_user)).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert tidak ditemukan")
    return alert


@router.post("/{alert_id}/acknowledge", response_model=AlertOut)
async def acknowledge_alert(
    alert_id: int,
    payload: AlertActionRequest = AlertActionRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alert = await _get_alert_or_404(alert_id, db)
    alert.status = AlertStatus.acknowledged
    alert.acknowledged_at = datetime.utcnow()
    db.add(alert)
    return alert


@router.post("/{alert_id}/resolve", response_model=AlertOut)
async def resolve_alert(
    alert_id: int,
    payload: AlertActionRequest = AlertActionRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alert = await _get_alert_or_404(alert_id, db)
    alert.status = AlertStatus.resolved
    alert.resolved_at = datetime.utcnow()
    db.add(alert)
    return alert


@router.post("/{alert_id}/escalate", response_model=AlertOut)
async def escalate_alert(
    alert_id: int,
    payload: AlertActionRequest = AlertActionRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_supervisor),
):
    alert = await _get_alert_or_404(alert_id, db)
    alert.status = AlertStatus.escalated
    db.add(alert)
    return alert


@router.post("/{alert_id}/assign", response_model=AlertOut)
async def assign_alert(
    alert_id: int,
    payload: AssignAlertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_supervisor),
):
    alert = await _get_alert_or_404(alert_id, db)
    user_result = await db.execute(select(User).where(User.id == payload.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    alert.assigned_user_id = payload.user_id
    db.add(alert)
    return alert

@router.post("/broadcast", status_code=204)
async def broadcast_alert_to_operators(
    payload: BroadcastAlertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_supervisor),
):
    """Supervisor mengirim pesan broadcast ke semua operator aktif."""
    result = await db.execute(
        select(User).where(
            User.role == "operator",
            User.is_active == True,
            User.fcm_token.is_not(None),
        )
    )
    operators = result.scalars().all()
    tokens = [u.fcm_token for u in operators]

    if tokens:
        await notification_service.broadcast_alert(
            tokens,
            title=f"📢 Broadcast dari {current_user.name}",
            body=payload.message,
            data={"type": "broadcast", "severity": payload.severity},
        )

async def _get_alert_or_404(alert_id: int, db: AsyncSession) -> Alert:
    result = await db.execute(
        select(Alert).options(selectinload(Alert.assigned_user)).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert tidak ditemukan")
    return alert
