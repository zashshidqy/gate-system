import enum
import uuid
import json
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Boolean,
    ForeignKey,
    Enum as SQLEnum,
    Text,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from ..database import Base


class TicketType(str, enum.Enum):
    SINGLE_ENTRY = "SINGLE_ENTRY"
    MULTI_DAY = "MULTI_DAY"
    VIP = "VIP"
    STAFF = "STAFF"


class ValidationMethod(str, enum.Enum):
    QR_SCAN = "QR_SCAN"
    RFID_LINK = "RFID_LINK"
    MANUAL = "MANUAL"
    ANPR = "ANPR"


class TicketToken(Base):
    __tablename__ = "ticket_tokens"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(32), unique=True, nullable=False, index=True)
    qr_payload = Column(Text, nullable=False)
    type = Column(SQLEnum(TicketType), nullable=False, default=TicketType.SINGLE_ENTRY)
    valid_from = Column(DateTime, nullable=False, default=datetime.utcnow)
    valid_until = Column(DateTime, nullable=False)
    max_uses = Column(Integer, nullable=False, default=1)
    used_count = Column(Integer, nullable=False, default=0)
    issued_by = Column(String(64), nullable=False)
    issued_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    revoked = Column(Boolean, nullable=False, default=False)
    metadata_json = Column(Text, nullable=True)  # JSON string for extra data

    @property
    def parsed_metadata(self):
        """Parse metadata_json as dict."""
        import json
        if self.metadata_json:
            try:
                return json.loads(self.metadata_json)
            except json.JSONDecodeError:
                return {}
        return {}

    usages = relationship("TicketUsage", back_populates="token", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_ticket_tokens_valid_until", "valid_until"),
        Index("ix_ticket_tokens_revoked", "revoked"),
    )


class TicketUsage(Base):
    __tablename__ = "ticket_usages"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_id = Column(PG_UUID(as_uuid=True), ForeignKey("ticket_tokens.id", ondelete="CASCADE"), nullable=False, index=True)
    gate_id = Column(String(16), nullable=False)  # "ENTRY" / "EXIT"
    direction = Column(String(8), nullable=False)  # "IN" / "OUT"
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    allowed = Column(Boolean, nullable=False)
    method = Column(SQLEnum(ValidationMethod), nullable=False)
    note = Column(Text, nullable=True)
    
    # Sensor data captured at validation time
    sensor_data_json = Column(Text, nullable=True)  # JSON snapshot of gate sensors
    
    @property
    def parsed_sensor_data(self):
        """Parse sensor_data_json as dict."""
        if self.sensor_data_json:
            try:
                return json.loads(self.sensor_data_json)
            except json.JSONDecodeError:
                return {}
        return {}

    token = relationship("TicketToken", back_populates="usages")

    __table_args__ = (
        Index("ix_ticket_usages_gate_timestamp", "gate_id", "timestamp"),
    )


class TicketType(str, enum.Enum):
    SINGLE_ENTRY = "SINGLE_ENTRY"
    MULTI_DAY = "MULTI_DAY"
    VIP = "VIP"
    STAFF = "STAFF"


class ValidationMethod(str, enum.Enum):
    QR_SCAN = "QR_SCAN"
    RFID_LINK = "RFID_LINK"
    MANUAL = "MANUAL"
    ANPR = "ANPR"