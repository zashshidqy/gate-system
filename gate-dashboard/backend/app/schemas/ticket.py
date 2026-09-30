from datetime import datetime
from typing import Optional, List, Literal, Any
from pydantic import BaseModel, Field, ConfigDict
import uuid


class TicketTokenBase(BaseModel):
    type: Literal["SINGLE_ENTRY", "MULTI_DAY", "VIP", "STAFF"] = "SINGLE_ENTRY"
    valid_from: Optional[datetime] = None
    valid_until: datetime
    max_uses: int = Field(default=1, ge=1)
    metadata: Optional[dict[str, Any]] = None


class TicketTokenCreate(TicketTokenBase):
    pass


class TicketTokenUpdate(BaseModel):
    type: Optional[Literal["SINGLE_ENTRY", "MULTI_DAY", "VIP", "STAFF"]] = None
    valid_until: Optional[datetime] = None
    max_uses: Optional[int] = Field(default=None, ge=1)
    revoked: Optional[bool] = None
    metadata: Optional[dict[str, Any]] = None


class TicketTokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    qr_payload: str
    type: Literal["SINGLE_ENTRY", "MULTI_DAY", "VIP", "STAFF"]
    valid_from: Optional[datetime]
    valid_until: datetime
    max_uses: int
    used_count: int
    issued_by: str
    issued_at: datetime
    revoked: bool
    parsed_metadata: Optional[dict[str, Any]] = None


class TicketTokenListResponse(BaseModel):
    tokens: List[TicketTokenResponse]
    total: int
    page: int
    page_size: int


class TicketValidationRequest(BaseModel):
    token_code: str
    gate: Literal["ENTRY", "EXIT"]
    method: Literal["QR_SCAN", "RFID_LINK", "MANUAL", "ANPR"] = "QR_SCAN"


class TicketValidationResponse(BaseModel):
    allowed: bool
    reason: Optional[str] = None
    token: Optional[TicketTokenResponse] = None
    usage_id: Optional[uuid.UUID] = None


class TicketUsageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    token_id: uuid.UUID
    gate_id: str
    direction: str
    timestamp: datetime
    allowed: bool
    method: str
    note: Optional[str] = None


class QRCodeResponse(BaseModel):
    token_code: str
    qr_data: str  # base64 encoded PNG
    qr_payload: str  # JSON string for QR content