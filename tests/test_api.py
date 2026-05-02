"""
Basic API tests.
Run: pytest tests/ -v
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.anyio
async def test_login_invalid():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/auth/login", json={"employee_id": "bad", "password": "bad"})
    assert res.status_code == 401


@pytest.mark.anyio
async def test_predict_requires_auth():
    payload = {
        "xmeas": [0.0] * 41,
        "xmv": [0.0] * 11,
        "unit": "R-201"
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/predict", json=payload)
    assert res.status_code == 403  # No token


@pytest.mark.anyio
async def test_alerts_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/alerts")
    assert res.status_code == 403
