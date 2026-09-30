from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
import uuid


class AuthorizedCardCreate(BaseModel):
    uid: str = Field(..., pattern=r"^[0-9A-F]{8,32}$")  # hex UID
    label: Optional[str] = None
    note: Optional[str] = None


class AuthorizedCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    uid: str
    label: Optional[str]
    added_by: str
    added_at: datetime
    active: bool
    note: Optional[str]


class AuthorizedCardListResponse(BaseModel):
    cards: List[AuthorizedCardResponse]
    total: int
    page: int
    page_size: int