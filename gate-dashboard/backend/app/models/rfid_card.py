import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from ..database import Base


class AuthorizedCard(Base):
    __tablename__ = "authorized_cards"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uid = Column(String(32), unique=True, nullable=False, index=True)  # hex UID uppercase
    label = Column(String(64), nullable=True)  # human-readable name
    added_by = Column(String(64), nullable=False)
    added_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    active = Column(Boolean, nullable=False, default=True)
    note = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_authorized_cards_active", "active"),
    )