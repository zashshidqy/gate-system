"""Protocol parsing and command building - ported from gate_dual_gui.py"""
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum


class GateCommand(str, Enum):
    """Command bytes understood by the ESP32 firmware.

    The enum *value* is the literal byte written to the serial port, so
    ``build_command`` is just ``value.encode("ascii")``. This lives here
    rather than in ``schemas`` because it is protocol, not an API payload.
    """

    OPEN = "O"
    CLOSE = "C"
    ADD_MASTER = "A"
    DEL_MASTER = "Q"
    LIST_MASTER = "L"
    RESET_ALL = "R"
    TEST_CLOSED = "X"
    TEST_OPEN = "Z"


@dataclass
class ParsedGateStatus:
    state: str
    pos: int
    front_cm: int
    vehicle: bool
    lcd1: str
    lcd2: str
    masters: List[str]
    exit_cm: int
    rfid_ver: str
    last_uid: Optional[str]
    last_auth: Optional[str]
    count: int


def parse_st(line: str) -> Optional[ParsedGateStatus]:
    """Parse ST|... status line from ESP32. Returns None if invalid."""
    if not line.startswith("ST|"):
        return None
    parts = line.split("|")
    if len(parts) < 13:
        return None

    def _int(idx: int, default: int = -1) -> int:
        try:
            return int(parts[idx])
        except (ValueError, IndexError):
            return default

    masters_raw = parts[7]
    masters = masters_raw.split(",") if masters_raw != "-" else []

    return ParsedGateStatus(
        state=parts[1],
        pos=_int(2),
        front_cm=_int(3),
        vehicle=parts[4] == "1",
        lcd1=parts[5],
        lcd2=parts[6],
        masters=masters,
        exit_cm=_int(8),
        rfid_ver=parts[9],
        last_uid=parts[10] if parts[10] != "-" else None,
        last_auth=parts[11] if parts[11] != "-" else None,
        count=_int(12),
    )


def build_command(cmd: GateCommand) -> bytes:
    """Build command byte to send to ESP32."""
    return cmd.value.encode("ascii")


# Debug log patterns
class LogTag(str, Enum):
    INFO = "info"
    OK = "ok"
    WARN = "warn"
    ERR = "err"