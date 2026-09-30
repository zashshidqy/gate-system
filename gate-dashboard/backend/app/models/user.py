import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Enum as SQLEnum, Text, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from ..database import Base


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    GUARD = "GUARD"
    STAFF = "STAFF"


class User(Base):
    __tablename__ = "users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=True, index=True)
    hashed_password = Column(String(128), nullable=False)
    full_name = Column(String(128), nullable=True)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.STAFF)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    note = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_users_active_role", "active", "role"),
    )