from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.db_models import User
from app.models.schemas import LoginRequest, TokenResponse, UserCreate, UserOut
from app.services.auth_service import (
    verify_password, hash_password, create_access_token, get_current_user
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.employee_id == payload.employee_id))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID Karyawan atau password salah"
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Akun tidak aktif")

    token = create_access_token({"sub": user.employee_id, "role": user.role})
    return TokenResponse(
        access_token=token,
        role=user.role,
        name=user.name,
        employee_id=user.employee_id,
        unit=user.unit,
    )


@router.post("/register", response_model=UserOut, status_code=201)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.employee_id == payload.employee_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="ID Karyawan sudah terdaftar")

    user = User(
        employee_id=payload.employee_id,
        name=payload.name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        unit=payload.unit,
        shift=payload.shift,
    )
    db.add(user)
    await db.flush()
    return user


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/fcm-token")
async def update_fcm_token(
    token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    current_user.fcm_token = token
    db.add(current_user)
    return {"message": "FCM token updated"}
