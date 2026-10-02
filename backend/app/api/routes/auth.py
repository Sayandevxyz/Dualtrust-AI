"""Auth routes — demo login + JWT."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from jose import jwt
from passlib.context import CryptContext

from app.database import get_db
from app.models import User
from app.schemas.api_schemas import LoginRequest, TokenResponse
from app.config import settings

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_token(user_id: str, email: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "email": email, "role": role, "exp": expire},
        settings.JWT_SECRET, algorithm="HS256"
    )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    # In DEMO_MODE, accept demo@dualtrust.ai / demo1234
    if settings.DEMO_MODE:
        if req.email == "demo@dualtrust.ai" and req.password == "demo1234":
            return TokenResponse(
                access_token=create_token("demo-user", req.email, "reviewer"),
                user_name="Demo Reviewer",
                role="reviewer",
            )

    user = db.query(User).filter(User.email == req.email).first()
    if not user or not pwd_context.verify(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return TokenResponse(
        access_token=create_token(user.id, user.email, user.role),
        user_name=user.name,
        role=user.role,
    )


@router.get("/me")
def me():
    if settings.DEMO_MODE:
        return {"name": "Demo Reviewer", "email": "demo@dualtrust.ai", "role": "reviewer"}
    return {"message": "Not in demo mode"}
