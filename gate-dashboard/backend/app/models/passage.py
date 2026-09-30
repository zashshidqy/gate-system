import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from ..database import Base


class Passage(Base):
    __tablename__ = "passages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    direction = Column(String(16), nullable=False)  # ENTRY / EXIT
    method = Column(String(16), nullable=False)  # RFID / ANPR / MANUAL / QR
    uid = Column(String(64), nullable=True)
    plate = Column(String(32), nullable=True)
    allowed = Column(Boolean, nullable=False)
    image_path = Column(Text, nullable=True)
    note = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_passages_direction_ts", "direction", "ts"),
        Index("ix_passages_method", "method"),
    )