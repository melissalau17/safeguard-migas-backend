from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/safeguard_migas"
    REDIS_URL: str = "redis://localhost:6379/0"

    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    MODEL_PATH: str = "ml/ensemble_model.pkl"
    SCALER_PATH: str = "ml/scaler.pkl"
    LABEL_ENCODER_PATH: str = "ml/label_encoder.pkl"

    FIREBASE_CREDENTIALS_PATH: str = "ml/firebase_credentials.json"

    APP_ENV: str = "development"
    CORS_ORIGINS: str = '["http://localhost:3000"]'
    POLL_INTERVAL_SECONDS: int = 5
    DRIFT_CHECK_INTERVAL_SECONDS: int = 60

    # TEP: 41 XMEAS + 11 XMV = 52 variables
    N_SENSOR_VARS: int = 52
    FAULT_CLASSES: List[str] = [
        "Normal", "Fault1", "Fault2", "Fault3", "Fault4", "Fault5",
        "Fault6", "Fault7", "Fault8", "Fault9", "Fault10", "Fault11",
        "Fault12", "Fault13", "Fault14", "Fault15", "Fault16",
        "Fault17", "Fault18", "Fault19", "Fault20",
    ]

    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.CORS_ORIGINS)

    class Config:
        env_file = ".env"


settings = Settings()
