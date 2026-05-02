from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
from datetime import datetime
from app.database import get_db
from app.models.db_models import User, Alert, SensorReading, AlertSeverity, AlertStatus
from app.models.schemas import SensorPayload, PredictionResponse, FaultProbability
from app.services.auth_service import get_current_user
from app.services.ml_service import ml_service
from app.services.notification_service import notification_service

router = APIRouter(prefix="/predict", tags=["ML Prediction"])


@router.post("", response_model=PredictionResponse)
async def predict(
    payload: SensorPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit 52 TEP sensor readings (41 XMEAS + 11 XMV).
    Returns fault classification, confidence, and contributing variables.
    """
    result = ml_service.predict(payload.xmeas, payload.xmv)

    # Persist sensor reading
    reading = SensorReading(unit=payload.unit)
    for i, v in enumerate(payload.xmeas, start=1):
        setattr(reading, f"xmeas_{i}", v)
    for i, v in enumerate(payload.xmv, start=1):
        setattr(reading, f"xmv_{i}", v)
    db.add(reading)
    await db.flush()

    # Create alert if anomaly detected
    alert_id = None
    if result["predicted_class"] != "Normal":
        alert = Alert(
            fault_class=result["predicted_class"],
            fault_label=result["predicted_label"],
            unit=payload.unit,
            confidence=result["confidence"],
            uncertainty=result["uncertainty"],
            severity=result["severity"],
            status=AlertStatus.active,
            description=_build_description(result),
            top_variables=json.dumps(result["top_variables"]),
            sensor_reading_id=reading.id,
        )
        db.add(alert)
        await db.flush()
        alert_id = alert.id

        # Push notification to all operators in this unit
        await _notify_operators(db, alert, payload.unit)

    return PredictionResponse(
        predicted_class=result["predicted_class"],
        predicted_label=result["predicted_label"],
        confidence=result["confidence"],
        uncertainty=result["uncertainty"],
        severity=result["severity"],
        probabilities=[FaultProbability(**p) for p in result["probabilities"]],
        top_variables=result["top_variables"],
        alert_id=alert_id,
        timestamp=datetime.utcnow(),
    )


def _build_description(result: dict) -> str:
    top = result["top_variables"]
    if not top:
        return "Anomali terdeteksi oleh model."
    top_var = top[0]
    return (
        f"{top_var['name']} menyimpang {top_var['sigma_deviation']:+.1f}σ dari normal "
        f"(nilai: {top_var['value']} {top_var['unit']}, normal: {top_var['normal_range']})."
    )


async def _notify_operators(db: AsyncSession, alert: Alert, unit: str):
    result = await db.execute(
        select(User).where(User.unit == unit, User.fcm_token.is_not(None))
    )
    users = result.scalars().all()
    tokens = [u.fcm_token for u in users if u.fcm_token]
    if tokens:
        severity_label = "🔴 CRITICAL" if alert.severity == AlertSeverity.critical else "⚠️ WARNING"
        await notification_service.broadcast_alert(
            tokens,
            title=f"{severity_label}: {alert.fault_label}",
            body=f"{alert.unit} • Confidence: {alert.confidence:.0%} • {alert.uncertainty} uncertainty",
            data={"alert_id": str(alert.id), "fault_class": alert.fault_class},
        )
