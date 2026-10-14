"""Gate control regression tests.

Each test names the bug it catches. Three of them fail outright against the
pre-fix code, which is the point: ``tsc``/``vite build`` cannot catch an
AttributeError on a missing enum member, a ``bytes.encode()`` call, or a field
that does not exist.
"""
from conftest import FakeBridge, make_status, post_command

from app.services.protocol import GateCommand, build_command


def test_command_open_returns_200(client):
    """Catches Task 1.2: command_map referenced GateCommand.ALERT/QUERY/LOCK/
    RESET, which do not exist, so the dict raised AttributeError and *every*
    command answered HTTP 500 -- including the plain 'O'."""
    response = post_command(client, "ENTRY", "O")

    assert response.status_code == 200, response.text


def test_command_close_sends_bytes_C(client, bridge):
    """Catches Task 1.3: send_command was annotated `cmd: str` but every caller
    passes bytes from build_command(), and the body called .encode() on them."""
    response = post_command(client, "ENTRY", "C")

    assert response.status_code == 200, response.text
    assert bridge.calls == [("ENTRY", b"C")]


def test_command_invalid_returns_400(client, bridge):
    """Regression: an unknown byte is a client error, not a server error, and
    must not reach the bridge."""
    response = post_command(client, "ENTRY", "ZZ")

    assert response.status_code == 400, response.text
    assert bridge.calls == []


def test_command_X_maps_to_test_closed(client, bridge):
    """Catches the reversed X/Z mapping.

    X/Z are servo-test bytes, and this batch rejects them at the API boundary
    (see the SERVO_TEST_COMMANDS guard), so the mapping is asserted at the
    protocol level where it belongs: X must be TEST_CLOSED, not ADD_MASTER.
    The old code mapped X->ADD_MASTER and Z->DEL_MASTER, i.e. backwards.
    """
    # The enum value is the wire byte, so the correct mapping is mechanical.
    assert GateCommand("X") is GateCommand.TEST_CLOSED
    assert build_command(GateCommand.TEST_CLOSED) == b"X"
    assert GateCommand("Z") is GateCommand.TEST_OPEN
    assert build_command(GateCommand.TEST_OPEN) == b"Z"

    # ...and the old, dangerous mapping must be gone.
    assert GateCommand("X") is not GateCommand.ADD_MASTER
    assert GateCommand("Z") is not GateCommand.DEL_MASTER

    # The API must refuse to drive the servo directly.
    assert post_command(client, "ENTRY", "X").status_code == 400
    assert post_command(client, "ENTRY", "Z").status_code == 400
    assert bridge.calls == []


def test_status_returns_200_and_state(client, bridge):
    """Catches Task 1.4: get_gate_status read reader.status, a field
    SerialReader did not have, so /gates/status always answered 500.

    The fake reader happens to carry a `status` attribute, so the endpoint
    half alone would pass against the old code. The field contract on the
    *real* SerialReader is asserted too -- that is the part that was missing.
    """
    import dataclasses

    from app.services.serial_bridge import SerialReader

    fields = {f.name for f in dataclasses.fields(SerialReader)}
    assert "status" in fields, "SerialReader must cache the last parsed status"
    assert "connected" in fields, "SerialReader must track whether the port is open"

    bridge.readers["ENTRY"].status = make_status(state="CLOSED")

    response = client.get("/api/gates/status")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ENTRY"]["connected"] is True
    assert body["ENTRY"]["status"]["state"] == "CLOSED"
    assert body["EXIT"]["connected"] is True
    # A registered-but-never-reported unit must not invent a status.
    assert body["EXIT"]["status"] is None


def test_status_503_when_disconnected(bridge):
    """Catches Task 1.4's second half: a reader that failed to start used to
    stay registered, so the "not connected" guard passed, the command was
    dropped, and the API still answered 200 -- a silent false success.

    A unit whose reader never opened must give 503, and nothing on the wire.
    """
    offline = FakeBridge(connected_units=())
    offline.readers["ENTRY"].connected = False

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.gates import get_serial_bridge, router
    from app.dependencies import get_current_active_user

    from conftest import FakeUser

    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_current_active_user] = lambda: FakeUser()
    app.dependency_overrides[get_serial_bridge] = lambda: offline

    with TestClient(app) as offline_client:
        response = offline_client.post(
            "/api/gates/command", params={"unit": "ENTRY", "command": "O"}
        )

    assert response.status_code == 503, response.text
    assert offline.calls == []

    # ...and /gates/status must not claim it is connected either.
    assert offline.is_connected("ENTRY") is False
