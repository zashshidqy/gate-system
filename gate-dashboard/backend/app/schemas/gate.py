from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict


class GateStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    state: str
    pos: int
    front_cm: int
    vehicle: bool
    lcd1: str
    lcd2: str
    masters: List[str]
    exit_cm: int
    rfid_ver: str
    last_uid: Optional[str] = None
    last_auth: Optional[str] = None
    count: int


class UnitStatus(BaseModel):
    unit: Literal["ENTRY", "EXIT"]
    status: Optional[GateStatus] = None
    connected: bool = False
    last_update: Optional[datetime] = None


class GateEvent(BaseModel):
    type: Literal["GATE_STATUS", "GATE_LOG", "CARD_ADDED", "CARD_REMOVED", "CARDS_CLEARED", "TICKET_VALIDATED"]
    unit: Optional[Literal["ENTRY", "EXIT"]] = None
    payload: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)