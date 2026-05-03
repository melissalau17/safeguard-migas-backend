from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.db_models import UserRole, AlertSeverity, AlertStatus


# ── Auth ─────────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    employee_id: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    name: str
    employee_id: str
    unit: Optional[str] = None

class UserCreate(BaseModel):
    employee_id: str
    name: str
    password: str
    role: UserRole = UserRole.operator
    unit: Optional[str] = None
    shift: Optional[str] = None

class UserOut(BaseModel):
    id: int
    employee_id: str
    name: str
    role: UserRole
    unit: Optional[str]
    shift: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


# ── Sensor / Predict ──────────────────────────────────────────────────────────
class SensorPayload(BaseModel):
    """52 TEP variables: 41 XMEAS + 11 XMV"""
    xmeas: List[float] = Field(..., min_length=41, max_length=41, description="41 process measurements")
    xmv: List[float] = Field(..., min_length=11, max_length=11, description="11 manipulated variables")
    unit: str = Field(default="R-201")
    timestamp: Optional[datetime] = None

class FaultProbability(BaseModel):
    fault_class: str
    label: str
    probability: float

class PredictionResponse(BaseModel):
    predicted_class: str
    predicted_label: str
    confidence: float
    uncertainty: str          # rendah / sedang / tinggi
    severity: AlertSeverity
    probabilities: List[FaultProbability]
    top_variables: List[Dict[str, Any]]
    alert_id: Optional[int] = None
    timestamp: datetime


# ── Dashboard ─────────────────────────────────────────────────────────────────
class GlobalRiskSummary(BaseModel):
    status: str               # NORMAL / WARNING / CRITICAL
    confidence: float
    active_anomaly_count: int
    detected_minutes_ago: Optional[int]

class DashboardResponse(BaseModel):
    global_risk: GlobalRiskSummary
    top_faults: List[FaultProbability]
    top_variables: List[Dict[str, Any]]
    active_alerts: List["AlertOut"]


# ── Alerts ────────────────────────────────────────────────────────────────────
class AlertOut(BaseModel):
    id: int
    fault_class: str
    fault_label: str
    unit: str
    confidence: float
    uncertainty: str
    severity: AlertSeverity
    status: AlertStatus
    description: Optional[str]
    top_variables: Optional[str]
    detected_at: datetime
    resolved_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    assigned_user: Optional[UserOut]

    class Config:
        from_attributes = True

class AlertActionRequest(BaseModel):
    note: Optional[str] = None

class AssignAlertRequest(BaseModel):
    user_id: int
    note: Optional[str] = None
class BroadcastAlertRequest(BaseModel):
    message: str
    severity: str = "info"   # info / warning / critical

# ── Drift ─────────────────────────────────────────────────────────────────────
class DriftVariableStatus(BaseModel):
    variable_name: str
    ks_statistic: float
    ks_pvalue: float
    psi_score: float
    drift_level: str          # high / medium / none

class DriftSummaryResponse(BaseModel):
    variables: List[DriftVariableStatus]
    total_high: int
    total_medium: int
    total_normal: int
    retraining_recommended: bool
    last_retrain_days_ago: Optional[int]
    checked_at: datetime


# ── History ───────────────────────────────────────────────────────────────────
class HistoryResponse(BaseModel):
    alerts: List[AlertOut]
    stats: Dict[str, Any]
