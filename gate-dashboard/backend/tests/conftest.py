"""Test fixtures for the gate-control suite.

No hardware and no database are involved: the serial bridge is replaced with a
recorder, and auth is overridden. ``JWT_SECRET`` is set *before* ``app`` is
imported because ``app/config.py`` reads it at import time (``Settings`` has no
default) and ``app/dependencies.py`` calls ``get_settings()`` at module level.

Run from ``gate-dashboard/backend`` so the CWD-relative ``env_file=".env"``
resolves and ``app`` is importable.
"""
import os

# Must precede any `app.*` import.
os.environ.setdefault("JWT_SECRET", "test-secret-not-used-for-real-auth-0123456789")

from typing import Any, Dict, List, Optional, Tuple  # noqa: E402

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api import gates as gates_module  # noqa: E402
from app.api.gates import router as gates_router  # noqa: E402
from app.api.gates import get_serial_bridge  # noqa: E402
from app.dependencies import get_current_active_user  # noqa: E402
from app.services.protocol import ParsedGateStatus  # noqa: E402


class FakeReader:
    """Stands in for ``SerialReader``; records what would hit the wire."""

    def __init__(self, unit: str, connected: bool = True) -> None:
        self.unit = unit
        self.connected = connected
        self.status: Optional[ParsedGateStatus] = None
        self.sent: List[bytes] = []

    async def send_command(self, cmd: bytes) -> None:
        if not self.connected:
            return
        self.sent.append(cmd)


class FakeBridge:
    """Stands in for ``SerialBridge`` with the *fixed* send_command contract.

    Mirrors ``SerialBridge.send_command(unit, cmd: bytes)`` and
    ``is_connected(unit)`` so the endpoint code under test is exercised
    unchanged.
    """

    def __init__(self, connected_units: Tuple[str, ...] = ("ENTRY", "EXIT")) -> None:
        self.readers: Dict[str, FakeReader] = {
            unit: FakeReader(unit, connected=unit in connected_units)
            for unit in ("ENTRY", "EXIT")
        }
        self.calls: List[Tuple[str, bytes]] = []

    def is_connected(self, unit: str) -> bool:
        reader = self.readers.get(unit.upper())
        return bool(reader and reader.connected)

    async def send_command(self, unit: str, cmd: bytes) -> None:
        reader = self.readers.get(unit.upper())
        if reader is None or not reader.connected:
            return
        reader.sent.append(cmd)
        self.calls.append((unit.upper(), cmd))


class FakeUser:
    username = "tester"
    active = True


@pytest.fixture
def bridge() -> FakeBridge:
    """A bridge with both units connected."""
    return FakeBridge(connected_units=("ENTRY", "EXIT"))


@pytest.fixture
def client(bridge: FakeBridge) -> TestClient:
    """TestClient over a minimal app carrying only the gates router.

    A minimal app is deliberate: it avoids the ``app.main`` lifespan, so
    ``init_db()`` and the real serial ports are never touched.
    """
    app = FastAPI()
    app.include_router(gates_router, prefix="/api")
    app.dependency_overrides[get_current_active_user] = lambda: FakeUser()
    app.dependency_overrides[get_serial_bridge] = lambda: bridge

    # Belt-and-braces: the module-level handle some code paths still read.
    gates_module.serial_bridge = bridge

    with TestClient(app) as test_client:
        yield test_client


def make_status(state: str = "CLOSED") -> ParsedGateStatus:
    """A minimal but fully populated status, as parse_st() would return."""
    return ParsedGateStatus(
        state=state,
        pos=0,
        front_cm=120,
        vehicle=False,
        lcd1="SIAP",
        lcd2="SCAN KARTU",
        masters=["AA:BB:CC:DD:EE:FF"],
        exit_cm=0,
        rfid_ver="1.0",
        last_uid=None,
        last_auth=None,
        count=7,
    )


def post_command(client: TestClient, unit: str, command: str, **kw: Any) -> Any:
    """Small helper so each test reads as one intent."""
    return client.post("/api/gates/command", params={"unit": unit, "command": command}, **kw)
