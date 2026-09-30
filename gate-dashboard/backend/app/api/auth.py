"""Authentication API"""
from datetime import datetime, timedelta
import hashlib
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from jose import jwt

from ..database import get_db
from ..models.user import User, UserRole
from ..schemas.user import UserCreate, UserResponse, Token, LoginRequest
from ..schemas.common import MessageResponse
from ..config import get_settings
from ..dependencies import get_current_active_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

settings = get_settings()


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """Hash password with SHA-256 and salt. Returns (hash, salt)."""
    if salt is None:
        salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256((password + salt).encode())
    return hash_obj.hexdigest(), salt


def verify_password(plain_password: str, hashed_password: str, salt: str) -> bool:
    """Verify password against hash and salt."""
    hash_obj = hashlib.sha256((plain_password + salt).encode())
    return hash_obj.hexdigest() == hashed_password


def get_password_hash(password: str) -> str:
    """Hash password and return hash:salt format for storage."""
    hashed, salt = hash_password(password)
    return f"{hashed}:{salt}"


def parse_password_hash(stored: str) -> tuple[str, str]:
    """Parse stored hash:salt format."""
    parts = stored.split(":", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    # Legacy format (no salt) - fallback
    return stored, ""


@router.post("/login", response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    hashed, salt = parse_password_hash(user.hashed_password)
    if not verify_password(request.password, hashed, salt):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not user.active:
        raise HTTPException(status_code=403, detail="User account is disabled")

    user.last_login = datetime.utcnow()
    db.commit()

    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token, token_type="bearer", user=UserResponse.model_validate(user))


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if first user -> make admin
    user_count = db.query(User).count()
    role = UserRole.ADMIN if user_count == 0 else user_data.role

    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    if user_data.email and db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = get_password_hash(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed,
        full_name=user_data.full_name,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_active_user)):
    return UserResponse.model_validate(current_user)