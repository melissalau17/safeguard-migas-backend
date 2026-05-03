"""
Sensor Simulator — Realistic Mode
──────────────────────────────────
Generate data sensor TEP yang gradual dan realistis,
bukan random setiap saat. Model akan lebih yakin
karena pola fault jelas berbeda dari normal.
"""

import asyncio
import numpy as np
import random
import json
import time
from datetime import datetime
from app.services.ml_service import ml_service

# Nilai real dari data training (faultNumber == 0)
MEANS = [0.2504, 3663.827, 4508.7334, 9.3467, 26.9018, 42.3378, 2705.055,
         75.0019, 120.4001, 0.3371, 80.1062, 50.002, 2633.7854, 25.1598,
         50.0003, 3102.2441, 22.952, 65.799, 232.1122, 341.428, 94.6002,
         77.2938, 32.1879, 8.8926, 26.3833, 6.882, 18.7756, 1.6568,
         32.9595, 13.8223, 23.9777, 1.2566, 18.5787, 2.2633, 4.8436,
         2.2982, 0.0179, 0.8356, 0.0986, 53.7218, 43.826,
         63.0488, 53.9725, 24.636, 61.297, 22.2162, 40.056,
         38.1058, 46.5347, 47.9456, 41.1033, 18.1097]

STDS = [0.0309, 33.9383, 39.3346, 0.086, 0.2115, 0.2183, 7.538,
        0.5419, 0.0381, 0.0125, 0.2388, 1.0105, 7.8769, 1.0145,
        1.0174, 6.5318, 0.6174, 0.4254, 10.3638, 1.6507, 0.1323,
        0.2613, 0.2909, 0.1038, 0.3157, 0.1079, 0.2937, 0.0256,
        0.3366, 0.1082, 0.3861, 0.1019, 0.3361, 0.0266, 0.0662,
        0.0533, 0.01, 0.0185, 0.0101, 0.5036, 0.5021,
        0.5811, 0.4699, 3.039, 1.2464, 0.5304, 1.527,
        2.9737, 2.3546, 2.7155, 0.5419, 1.4653]

MINS = [0.1224, 3516.7, 4348.3, 8.976, 26.07, 41.394, 2674.4,
        72.936, 120.32, 0.287, 79.027, 46.163, 2601.7, 20.878,
        45.899, 3074.7, 20.336, 64.043, 187.98, 334.22, 94.017,
        76.141, 30.97, 8.4937, 24.954, 6.426, 17.527, 1.5614,
        31.367, 13.407, 22.419, 0.8237, 17.235, 2.1504, 4.5453,
        2.0958, -0.0212, 0.7592, 0.0606, 51.846, 41.768,
        60.58, 52.168, 12.083, 56.239, 19.872, 33.947,
        26.809, 37.043, 36.76, 38.809, 12.432]

MAXS = [0.3917, 3800.9, 4665.9, 9.7236, 27.734, 43.229, 2737.7,
        77.071, 120.48, 0.3948, 81.083, 53.849, 2667.8, 29.386,
        54.281, 3131.3, 25.337, 67.524, 273.57, 347.89, 95.198,
        78.396, 33.395, 9.2936, 27.627, 7.3006, 19.973, 1.757,
        34.452, 14.309, 25.582, 1.6531, 20.105, 2.369, 5.1092,
        2.5182, 0.0549, 0.9275, 0.1372, 55.773, 45.979,
        65.543, 56.118, 38.227, 66.443, 24.405, 47.498,
        49.428, 56.443, 59.616, 43.93, 24.237]

N_VARS = len(MEANS)  # 52

# Fault signatures — variabel mana yang terpengaruh dan seberapa
FAULT_SIGNATURES = {
    1:  {3: 2.5, 0: -1.5},
    2:  {23: 3.0, 24: -2.0},
    3:  {2: 2.0, 8: 1.5},
    4:  {20: 3.5, 8: 2.0, 6: 1.5},
    5:  {21: 3.0, 11: -1.5},
    6:  {0: -4.0, 5: -2.0},
    7:  {6: 3.0, 12: 2.5, 7: -1.5},
    11: {4: -3.0, 5: -2.5, 19: -1.5},
    14: {20: 4.0, 8: 3.0},
}

# State simulator
_state = {
    "current_values": None,
    "fault_mode": 0,
    "fault_progress": 0.0,
    "fault_timer": 0,
    "normal_timer": 0,
    "phase": "normal",
}
_last_result = None


def _init_state():
    """Inisialisasi nilai sensor di titik operasi normal."""
    values = [round(float(np.random.normal(MEANS[i], max(STDS[i], 0.001) * 0.5)), 6)
              for i in range(N_VARS)]
    return values[:41], values[41:]


def _step_values(xmeas, xmv, fault_mode, fault_progress):
    """Update nilai sensor satu langkah — smooth transition."""
    all_vals = xmeas + xmv
    new_vals = []

    for i in range(N_VARS):
        mean = MEANS[i]
        std  = max(STDS[i], 0.001)

        # Mean reversion
        drift = (mean - all_vals[i]) * 0.03

        # Noise kecil berdasarkan std real
        noise = np.random.normal(0, std * 0.15)

        # Fault signature
        fault_drift = 0.0
        if fault_mode > 0 and fault_mode in FAULT_SIGNATURES:
            sig = FAULT_SIGNATURES[fault_mode]
            if i in sig:
                fault_drift = sig[i] * std * 3.0 * fault_progress

        new_vals.append(round(float(all_vals[i] + drift + noise + fault_drift), 6))

    return new_vals[:41], new_vals[41:]


async def run_simulator(interval_seconds: int = 5):
    global _last_result, _state

    from app.database import AsyncSessionLocal
    from app.models.db_models import Alert, AlertStatus, SensorReading
    from sqlalchemy import select

    print("🤖 Sensor simulator started (realistic mode)")

    xmeas, xmv = _init_state()
    _state["current_values"] = (xmeas, xmv)
    _state["fault_timer"]    = 0
    _state["normal_timer"]   = 0
    _state["phase"]          = "normal"

    while True:
        try:
            xmeas, xmv = _state["current_values"]
            phase       = _state["phase"]

            # ── State machine ──────────────────────────────
            if phase == "normal":
                _state["normal_timer"] += interval_seconds
                if _state["normal_timer"] >= 90:
                    _state["normal_timer"] = 0
                    _state["fault_mode"] = random.choices(
                        [0] + list(FAULT_SIGNATURES.keys()),
                        weights=[40] + [6] * len(FAULT_SIGNATURES)
                    )[0]
                    if _state["fault_mode"] > 0:
                        _state["phase"]          = "developing"
                        _state["fault_progress"] = 0.0
                        print(f"⚠️  Developing Fault{_state['fault_mode']}...")

            elif phase == "developing":
                _state["fault_progress"] = min(
                    1.0, _state["fault_progress"] + interval_seconds / 30
                )
                if _state["fault_progress"] >= 1.0:
                    _state["phase"] = "fault"
                    print(f"🚨 Full Fault{_state['fault_mode']} active!")

            elif phase == "fault":
                _state["fault_timer"] += interval_seconds
                if _state["fault_timer"] >= 60:
                    _state["fault_timer"] = 0
                    _state["phase"]       = "recovering"
                    print(f"🔧 Recovering from Fault{_state['fault_mode']}...")

            elif phase == "recovering":
                _state["fault_progress"] = max(
                    0.0, _state["fault_progress"] - interval_seconds / 20
                )
                if _state["fault_progress"] <= 0.0:
                    _state["phase"]      = "normal"
                    _state["fault_mode"] = 0
                    print("✅ System back to normal")
            # ── End state machine ──────────────────────────

            # Update nilai sensor
            xmeas, xmv = _step_values(
                xmeas, xmv,
                _state["fault_mode"],
                _state["fault_progress"],
            )
            _state["current_values"] = (xmeas, xmv)

            # Predict + track latency
            t0         = time.perf_counter()
            result     = ml_service.predict(xmeas, xmv)
            latency_ms = (time.perf_counter() - t0) * 1000

            from app.routers.metrics import record_latency
            record_latency(latency_ms)

            _last_result = {
                "timestamp":      datetime.utcnow().isoformat(),
                "prediction":     result,
                "latency_ms":     round(latency_ms, 1),
                "phase":          phase,
                "fault_mode":     _state["fault_mode"],
                "fault_progress": round(_state["fault_progress"], 2),
            }

            # ── Simpan sensor reading ke DB ────────────────
            async with AsyncSessionLocal() as db:
                reading = SensorReading(
                    timestamp = datetime.utcnow(),
                    unit      = "R-201",
                    **{f"xmeas_{i+1}": float(xmeas[i]) for i in range(41)},
                    **{f"xmv_{i+1}":   float(xmv[i])   for i in range(11)},
                )
                db.add(reading)
                await db.commit()
            # ── End simpan sensor reading ──────────────────

            # ── Simpan alert ke DB kalau fault terdeteksi ──
            if result["predicted_class"] != "Normal" and result["confidence"] >= 0.45:
                async with AsyncSessionLocal() as db:
                    existing = await db.execute(
                        select(Alert).where(
                            Alert.fault_class == result["predicted_class"],
                            Alert.status == AlertStatus.active,
                        )
                    )
                    if not existing.scalar_one_or_none():
                        alert = Alert(
                            fault_class   = result["predicted_class"],
                            fault_label   = result["predicted_label"],
                            severity      = result["severity"],
                            confidence    = result["confidence"],
                            unit          = "R-201",
                            status        = AlertStatus.active,
                            top_variables = json.dumps(result["top_variables"]),
                            detected_at   = datetime.utcnow(),
                        )
                        db.add(alert)
                        await db.commit()
                        print(f"🚨 Alert: {result['predicted_class']} "
                              f"({result['confidence']:.0%}) phase={phase}")
            # ── End simpan alert ───────────────────────────

        except Exception as e:
            print(f"❌ Simulator error: {e}")

        await asyncio.sleep(interval_seconds)


def get_latest() -> dict:
    return _last_result