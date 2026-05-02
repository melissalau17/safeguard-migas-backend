from sqlalchemy import String, Float, Integer, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.database import Base


class UserRole(str, enum.Enum):
    operator = "operator"
    supervisor = "supervisor"
    admin = "admin"


class AlertSeverity(str, enum.Enum):
    critical = "critical"
    warning = "warning"
    info = "info"


class AlertStatus(str, enum.Enum):
    active = "active"
    acknowledged = "acknowledged"
    resolved = "resolved"
    escalated = "escalated"


# ── Users ────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.operator)
    unit: Mapped[str] = mapped_column(String(50), nullable=True)
    shift: Mapped[str] = mapped_column(String(20), nullable=True)
    fcm_token: Mapped[str] = mapped_column(String(255), nullable=True)  # Firebase push token
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="assigned_user")


# ── Sensor Readings ───────────────────────────────────────────────────────────
class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    # TEP: 41 XMEAS process measurements
    xmeas_1: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_2: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_3: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_4: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_5: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_6: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_7: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_8: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_9: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_10: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_11: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_12: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_13: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_14: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_15: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_16: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_17: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_18: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_19: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_20: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_21: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_22: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_23: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_24: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_25: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_26: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_27: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_28: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_29: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_30: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_31: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_32: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_33: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_34: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_35: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_36: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_37: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_38: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_39: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_40: Mapped[float] = mapped_column(Float, nullable=True)
    xmeas_41: Mapped[float] = mapped_column(Float, nullable=True)

    # TEP: 11 XMV manipulated variables
    xmv_1: Mapped[float] = mapped_column(Float, nullable=True)
    xmv_2: Mapped[float] = mapped_column(Float, nullable=True)
    xmv_3: Mapped[float] = mapped_column(Float, nullable=True)
    xmv_4: Mapped[float] = mapped_column(Float, nullable=True)
    xmv_5: Mapped[float] = mapped_column(Float, nullable=True)
    xmv_6: Mapped[float] = mapped_column(Float, nullable=True)
    xmv_7: Mapped[float] = mapped_column(Float, nullable=True)
    xmv_8: Mapped[float] = mapped_column(Float, nullable=True)
    xmv_9: Mapped[float] = mapped_column(Float, nullable=True)
    xmv_10: Mapped[float] = mapped_column(Float, nullable=True)
    xmv_11: Mapped[float] = mapped_column(Float, nullable=True)


# ── Predictions / Alerts ─────────────────────────────────────────────────────
class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fault_class: Mapped[str] = mapped_column(String(30), nullable=False)   # e.g. "Fault4"
    fault_label: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "Reactor Cooling High"
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    uncertainty: Mapped[str] = mapped_column(String(20), nullable=False)   # rendah/sedang/tinggi
    severity: Mapped[AlertSeverity] = mapped_column(SAEnum(AlertSeverity), nullable=False)
    status: Mapped[AlertStatus] = mapped_column(SAEnum(AlertStatus), default=AlertStatus.active)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Top contributing variables (stored as JSON string)
    top_variables: Mapped[str] = mapped_column(Text, nullable=True)

    detected_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    assigned_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_user: Mapped["User"] = relationship("User", back_populates="alerts")

    sensor_reading_id: Mapped[int] = mapped_column(Integer, ForeignKey("sensor_readings.id"), nullable=True)


# ── Drift Records ─────────────────────────────────────────────────────────────
class DriftRecord(Base):
    __tablename__ = "drift_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    variable_name: Mapped[str] = mapped_column(String(50), nullable=False)
    ks_statistic: Mapped[float] = mapped_column(Float, nullable=False)
    ks_pvalue: Mapped[float] = mapped_column(Float, nullable=False)
    psi_score: Mapped[float] = mapped_column(Float, nullable=False)
    drift_level: Mapped[str] = mapped_column(String(10), nullable=False)  # high/medium/none
    checked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
