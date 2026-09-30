from datetime import datetime
from typing import Optional, List, Literal
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class GateCommand(str, Enum):
    OPEN = "O"
    CLOSE = "C"
    ADD_MASTER = "A"
    DEL_MASTER = "Q"
    LIST_MASTER = "L"
    RESET_ALL = "R"
    TEST_CLOSED = "X"
    TEST_OPEN = "Z"


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


class GateCommand(str, Enum):
    OPEN = "O"
    CLOSE = "C"
    ADD_MASTER = "A"
    DEL_MASTER = "Q"
    LIST_MASTER = "L"
    RESET_ALL = "R"
    TEST_CLOSED = "X"
    TEST_OPEN = "Z"


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