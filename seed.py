"""
seed.py — populate the database with demo users for testing.
Run once after `alembic upgrade head`:

    python seed.py
"""
import asyncio
from app.database import AsyncSessionLocal, init_db
from app.models.db_models import User, UserRole
from app.services.auth_service import hash_password


DEMO_USERS = [
    {
        "employee_id": "OP-20241",
        "name": "Budi Santoso",
        "password": "operator123",
        "role": UserRole.operator,
        "unit": "R-201",
        "shift": "Pagi",
    },
    {
        "employee_id": "OP-20198",
        "name": "Rina Hartati",
        "password": "operator123",
        "role": UserRole.operator,
        "unit": "SEP-102",
        "shift": "Pagi",
    },
    {
        "employee_id": "OP-20205",
        "name": "Dodi Kurniawan",
        "password": "operator123",
        "role": UserRole.operator,
        "unit": "COMP-301",
        "shift": "Pagi",
    },
    {
        "employee_id": "OP-20217",
        "name": "Sari Puspita",
        "password": "operator123",
        "role": UserRole.operator,
        "unit": "STR-401",
        "shift": "Pagi",
    },
    {
        "employee_id": "SV-10043",
        "name": "Andi Wijaya",
        "password": "supervisor123",
        "role": UserRole.supervisor,
        "unit": None,
        "shift": "Pagi",
    },
]


async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        for u in DEMO_USERS:
            user = User(
                employee_id=u["employee_id"],
                name=u["name"],
                hashed_password=hash_password(u["password"]),
                role=u["role"],
                unit=u.get("unit"),
                shift=u.get("shift"),
            )
            db.add(user)
        await db.commit()
        print(f"✅ Seeded {len(DEMO_USERS)} users.")
        print()
        print("Demo credentials:")
        for u in DEMO_USERS:
            print(f"  {u['employee_id']} / {u['password']}  ({u['role']})")


if __name__ == "__main__":
    asyncio.run(seed())
