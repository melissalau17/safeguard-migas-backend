# SafeGuard Migas — Backend Deployment Guide

## Architecture Overview

```
Flutter Mobile App
       │  HTTPS REST
       ▼
FastAPI Middleware (this backend)
  ├── /auth          JWT login & token management
  ├── /predict       52-var TEP → ensemble ML model → fault class
  ├── /alerts        CRUD + assign / escalate / acknowledge
  ├── /dashboard     Live aggregated risk summary
  ├── /drift         KS-stat + PSI vs training baseline
  └── /history       Anomaly log with period filters
       │
       ├── PostgreSQL  (alert history, users, sensor readings)
       ├── Redis       (Celery broker, sensor state cache)
       └── Firebase    (push notifications to Flutter)
```

---

## Step 1 — Export Your Trained Model

After running `tep_eda_preprocessing_training_final_with_ensemble.ipynb`:

```python
# At the END of your notebook, add this cell:
import joblib, numpy as np

joblib.dump(pipeline_or_model,  "ml/ensemble_model.pkl",  compress=3)
joblib.dump(scaler,             "ml/scaler.pkl",           compress=3)
joblib.dump(label_encoder,      "ml/label_encoder.pkl",    compress=3)
np.save("ml/training_baseline.npy", X_train)   # shape (N, 52)
print("Model exported ✅")
```

Or run the helper:
```bash
python ml/export_model.py   # creates a DEMO model if yours isn't configured yet
```

---

## Step 2 — Environment Setup

```bash
cp .env.example .env
# Edit .env:
#   DATABASE_URL  → your PostgreSQL connection string
#   SECRET_KEY    → generate with: python -c "import secrets; print(secrets.token_hex(32))"
#   FIREBASE_CREDENTIALS_PATH → path to your Firebase service account JSON
```

---

## Step 3A — Run Locally (Development)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL & Redis (easiest via Docker)
docker run -d --name pg -e POSTGRES_PASSWORD=yourpassword -e POSTGRES_DB=safeguard_migas -p 5432:5432 postgres:16-alpine
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Run DB migrations
alembic upgrade head              # or: python -c "import asyncio; from app.database import init_db; asyncio.run(init_db())"

# Seed demo users
python seed.py

# Start API
uvicorn app.main:app --reload --port 8000
```

API docs at: http://localhost:8000/docs

---

## Step 3B — Run with Docker Compose (Recommended)

```bash
# Build & start all services (API + PostgreSQL + Redis + Celery worker)
docker-compose up --build -d

# Run migrations inside container
docker-compose exec api alembic upgrade head

# Seed users
docker-compose exec api python seed.py

# View logs
docker-compose logs -f api
```

---

## Step 4 — Deploy to Production (Railway / Render / VPS)

### Option A: Railway (Easiest — ~5 min)
```bash
npm install -g @railway/cli
railway login
railway new safeguard-migas-api
railway add postgresql
railway add redis
railway up
railway vars set SECRET_KEY=your-secret-key
```

### Option B: Render
1. Connect GitHub repo at render.com
2. New Web Service → `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Add PostgreSQL & Redis as Add-ons
4. Set environment variables from .env.example

### Option C: VPS (DigitalOcean / Hetzner)
```bash
# On your VPS:
git clone <your-repo> /opt/safeguard
cd /opt/safeguard/safeguard_backend
docker-compose up --build -d

# Set up NGINX reverse proxy (optional, for HTTPS)
# Install certbot for SSL certificate
```

---

## Step 5 — Connect Flutter App

In `lib/services/api_service.dart`, replace:
```dart
static const String baseUrl = 'https://your-backend.example.com/api';
```
with your deployed URL, e.g.:
```dart
static const String baseUrl = 'https://safeguard-migas.up.railway.app/api';
```

---

## Step 6 — Firebase Push Notifications

1. Go to console.firebase.google.com → create project
2. Add Android app (package: `com.safeguard.migas`) → download `google-services.json` → put in `android/app/`
3. Add iOS app → download `GoogleService-Info.plist` → put in `ios/Runner/`
4. Download service account JSON → put in `ml/firebase_credentials.json`
5. In Flutter app, call `/auth/fcm-token` after login with the device FCM token

---

## API Endpoints Quick Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /auth/login | — | Login, returns JWT |
| GET | /auth/me | ✓ | Current user info |
| POST | /predict | ✓ | Submit 52 TEP readings, get fault prediction |
| GET | /dashboard/live | ✓ | Live risk summary |
| GET | /alerts | ✓ | List alerts (scoped by role) |
| POST | /alerts/{id}/acknowledge | ✓ | Acknowledge alert |
| POST | /alerts/{id}/resolve | ✓ | Resolve alert |
| POST | /alerts/{id}/escalate | Supervisor | Escalate alert |
| POST | /alerts/{id}/assign | Supervisor | Assign to operator |
| GET | /drift/status | Supervisor | Live drift statistics |
| GET | /history | ✓ | Anomaly history (today/7days/30days) |

---

## Integrating Your Notebook Model

The notebook uses a `VotingClassifier` / `StackingClassifier` ensemble.
The backend expects `model.predict_proba(X)` where X has shape `(1, 52)`.

If your notebook uses a **pipeline**:
```python
joblib.dump(full_pipeline, "ml/ensemble_model.pkl")  # scaler is inside — set SCALER_PATH=""
```

If your notebook has **separate scaler + model**:
```python
joblib.dump(scaler,  "ml/scaler.pkl")
joblib.dump(model,   "ml/ensemble_model.pkl")
```

The `MLService.predict()` in `app/services/ml_service.py` handles both cases automatically.
