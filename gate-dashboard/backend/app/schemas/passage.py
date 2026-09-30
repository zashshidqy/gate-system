from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict
import uuid


class PassageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ts: datetime
    direction: Literal["ENTRY", "EXIT"]
    method: Literal["RFID", "ANPR", "MANUAL", "QR"]
    uid: Optional[str]
    plate: Optional[str]
    allowed: bool
    image_path: Optional[str]
    note: Optional[str]


class PassageListResponse(BaseModel):
    passages: List[PassageResponse]
    total: int
    page: int
    page_size: int


class PassageFilter(BaseModel):
    direction: Optional[Literal["ENTRY", "EXIT"]] = None
    method: Optional[Literal["RFID", "ANPR", "MANUAL", "QR"]] = None
    allowed: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)