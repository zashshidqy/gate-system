"""Integration test for IoT ↔ Backend ↔ Dashboard communication.

This test verifies the complete data flow without physical hardware:
1. Mock ESP32 sends serial data
2. Backend parses and broadcasts via WebSocket
3. WebSocket clients receive structured events
4. Commands flow back from client → backend → device
"""
import pytest
import asyncio
import json
from typing import List, Dict
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.protocol import parse_st, build_command, GateCommand, ParsedGateStatus
from app.services.serial_bridge import SerialBridge, SerialReader
from app.websocket.manager import ConnectionManager


# ============================================================================
# TEST 1: Protocol Parsing (IoT → Backend)
# ============================================================================

def test_protocol_parse_status_entry():
    """Verify backend can parse ESP32 status messages."""
    # Realistic status line from ESP32 ENTRY gate
    line = "ST|IDLE|0|245|0|Selamat Datang|Tap Kartu|04E12345AB67,A1B2C3D4|180|V2.1.0|04E12345AB67|GRANTED|42"
    
    status = parse_st(line)
    
    assert status is not None
    assert status.state == "IDLE"
    assert status.pos == 0
    assert status.front_cm == 245
    assert status.vehicle is False
    assert status.lcd1 == "Selamat Datang"
    assert status.lcd2 == "Tap Kartu"
    assert status.masters == ["04E12345AB67", "A1B2C3D4"]
    assert status.exit_cm == 180
    assert status.rfid_ver == "V2.1.0"
    assert status.last_uid == "04E12345AB67"
    assert status.last_auth == "GRANTED"
    assert status.count == 42
    print("✓ Protocol parsing works correctly")


def test_protocol_parse_status_exit():
    """Verify backend can parse EXIT gate status."""
    line = "ST|OPEN|90|50|1|Silakan Lewat|Terima Kasih|-|25|V2.1.0|-|-|128"
    
    status = parse_st(line)
    
    assert status is not None
    assert status.state == "OPEN"
    assert status.pos == 90
    assert status.front_cm == 50
    assert status.vehicle is True
    assert status.masters == []
    assert status.last_uid is None
    assert status.last_auth is None
    print("✓ EXIT gate parsing works correctly")


def test_protocol_build_commands():
    """Verify backend can build commands for ESP32."""
    assert build_command(GateCommand.OPEN) == b"O"
    assert build_command(GateCommand.CLOSE) == b"C"
    assert build_command(GateCommand.ADD_MASTER) == b"A"
    assert build_command(GateCommand.DEL_MASTER) == b"Q"
    assert build_command(GateCommand.LIST_MASTER) == b"L"
    assert build_command(GateCommand.RESET_ALL) == b"R"
    print("✓ Command building works correctly")


# ============================================================================
# TEST 2: Serial Bridge (IoT ↔ Backend)
# ============================================================================

@pytest.mark.asyncio
async def test_serial_reader_processes_status():
    """Verify SerialReader correctly processes status updates."""
    received_status: List[ParsedGateStatus] = []
    received_logs: List[tuple] = []
    received_cards: List[tuple] = []
    
    async def on_status(unit: str, status: ParsedGateStatus):
        received_status.append((unit, status))
    
    async def on_log(unit: str, message: str, tag):
        received_logs.append((unit, message, tag))
    
    async def on_card_tapped(unit: str, uid: str):
        received_cards.append((unit, uid))
    
    reader = SerialReader(
        unit="ENTRY",
        port="/dev/ttyUSB0",
        baudrate=115200,
        on_status=on_status,
        on_log=on_log,
        on_card_tapped=on_card_tapped,
    )
    
    # Simulate receiving status line
    await reader._process_line("ST|IDLE|0|245|0|Welcome|Tap Card|04E1AB67|180|V2.1.0|-|-|10")
    
    assert len(received_status) == 1
    assert received_status[0][0] == "ENTRY"
    assert received_status[0][1].state == "IDLE"
    assert received_status[0][1].pos == 0
    
    assert len(received_logs) == 1
    assert received_logs[0][0] == "ENTRY"
    
    print("✓ SerialReader processes status correctly")


@pytest.mark.asyncio
async def test_serial_reader_extracts_card_uid():
    """Verify SerialReader can extract RFID UIDs from log lines."""
    received_cards: List[tuple] = []
    
    async def on_status(unit, status):
        pass
    
    async def on_log(unit, message, tag):
        pass
    
    async def on_card_tapped(unit: str, uid: str):
        received_cards.append((unit, uid))
    
    reader = SerialReader(
        unit="ENTRY",
        port="/dev/ttyUSB0",
        baudrate=115200,
        on_status=on_status,
        on_log=on_log,
        on_card_tapped=on_card_tapped,
    )
    
    # Test various UID formats
    await reader._process_line("> Master ditambahkan: 04 E1 23 45 AB 67")
    await reader._process_line("> UID: A1 B2 C3 D4")
    await reader._process_line("> Master dihapus: FF EE DD CC BB AA")
    
    assert len(received_cards) == 3
    assert received_cards[0] == ("ENTRY", "04E12345AB67")
    assert received_cards[1] == ("ENTRY", "A1B2C3D4")
    assert received_cards[2] == ("ENTRY", "FFEEDDCCBBAA")
    
    print("✓ RFID UID extraction works correctly")


# ============================================================================
# TEST 3: WebSocket Broadcasting (Backend → Dashboard)
# ============================================================================

@pytest.mark.asyncio
async def test_websocket_broadcast():
    """Verify WebSocket manager can broadcast to multiple clients."""
    ws_manager = ConnectionManager()
    
    # Mock WebSocket clients
    client1 = AsyncMock()
    client2 = AsyncMock()
    
    await ws_manager.connect(client1, "client1")
    await ws_manager.connect(client2, "client2")
    
    assert ws_manager.total_connections == 2
    
    # Broadcast a gate status event
    await ws_manager.broadcast({
        "type": "GATE_STATUS",
        "unit": "ENTRY",
        "payload": {
            "state": "IDLE",
            "pos": 0,
            "vehicle": False,
        }
    })
    
    # Verify both clients received the message
    client1.send_text.assert_called_once()
    client2.send_text.assert_called_once()
    
    # Verify message structure
    sent_data = json.loads(client1.send_text.call_args[0][0])
    assert sent_data["type"] == "GATE_STATUS"
    assert sent_data["unit"] == "ENTRY"
    assert sent_data["payload"]["state"] == "IDLE"
    
    await ws_manager.disconnect(client1, "client1")
    await ws_manager.disconnect(client2, "client2")
    
    print("✓ WebSocket broadcasting works correctly")


# ============================================================================
# TEST 4: End-to-End Data Flow
# ============================================================================

@pytest.mark.asyncio
async def test_end_to_end_status_flow():
    """Verify complete data flow: IoT → Backend → WebSocket."""
    ws_manager = ConnectionManager()
    
    # Mock WebSocket client (represents dashboard)
    dashboard_client = AsyncMock()
    await ws_manager.connect(dashboard_client, "dashboard")
    
    # Create serial bridge
    bridge = SerialBridge(ws_manager)
    
    # Simulate receiving status from ESP32
    await bridge._on_status("ENTRY", ParsedGateStatus(
        state="OPEN",
        pos=90,
        front_cm=50,
        vehicle=True,
        lcd1="Silakan Lewat",
        lcd2="Gate Terbuka",
        masters=["04E1AB67"],
        exit_cm=180,
        rfid_ver="V2.1.0",
        last_uid="04E1AB67",
        last_auth="GRANTED",
        count=55,
    ))
    
    # Verify dashboard received the event via WebSocket
    dashboard_client.send_text.assert_called_once()
    sent_data = json.loads(dashboard_client.send_text.call_args[0][0])
    
    assert sent_data["type"] == "GATE_STATUS"
    assert sent_data["unit"] == "ENTRY"
    assert sent_data["payload"]["state"] == "OPEN"
    assert sent_data["payload"]["pos"] == 90
    assert sent_data["payload"]["vehicle"] is True
    assert sent_data["payload"]["last_uid"] == "04E1AB67"
    assert sent_data["payload"]["last_auth"] == "GRANTED"
    
    print("✓ End-to-end data flow works correctly")


@pytest.mark.asyncio
async def test_end_to_end_card_tap_flow():
    """Verify card tap events flow to dashboard."""
    ws_manager = ConnectionManager()
    dashboard_client = AsyncMock()
    await ws_manager.connect(dashboard_client, "dashboard")
    
    bridge = SerialBridge(ws_manager)
    
    # Simulate card tap event
    await bridge._on_card_tapped("EXIT", "A1B2C3D4E5F6")
    
    # Verify dashboard received CARD_TAPPED event
    dashboard_client.send_text.assert_called_once()
    sent_data = json.loads(dashboard_client.send_text.call_args[0][0])
    
    assert sent_data["type"] == "CARD_TAPPED"
    assert sent_data["unit"] == "EXIT"
    assert sent_data["payload"]["uid"] == "A1B2C3D4E5F6"
    
    print("✓ Card tap event flow works correctly")


# ============================================================================
# TEST 5: Command Flow (Dashboard → Backend → IoT)
# ============================================================================

@pytest.mark.asyncio
async def test_command_flow_dashboard_to_iot():
    """Verify commands flow from dashboard to IoT device."""
    ws_manager = ConnectionManager()
    bridge = SerialBridge(ws_manager)
    
    # Mock serial reader with command sending capability
    mock_reader = MagicMock()
    mock_reader.connected = True
    mock_reader.send_command = AsyncMock()
    
    bridge.readers["ENTRY"] = mock_reader
    
    # Send OPEN command to ENTRY gate
    await bridge.send_command("ENTRY", build_command(GateCommand.OPEN))
    
    # Verify command was sent to the device
    mock_reader.send_command.assert_called_once_with(b"O")
    
    print("✓ Command flow (Dashboard → IoT) works correctly")


# ============================================================================
# HELPER: Mock IoT Data Generator
# ============================================================================

class MockESP32:
    """Simulates an ESP32 gate controller for testing."""
    
    def __init__(self, unit: str):
        self.unit = unit
        self.state = "IDLE"
        self.pos = 0
        self.vehicle = False
        self.masters = ["04E12345AB67"]
        self.count = 0
        
    def generate_status(self) -> str:
        """Generate realistic ST| status line."""
        self.count += 1
        vehicle_flag = "1" if self.vehicle else "0"
        masters_str = ",".join(self.masters) if self.masters else "-"
        
        return (
            f"ST|{self.state}|{self.pos}|245|{vehicle_flag}|"
            f"Selamat Datang|Tap Kartu|{masters_str}|180|V2.1.0|-|-|{self.count}"
        )
    
    def simulate_card_tap(self, uid: str) -> str:
        """Generate card tap log line."""
        return f"> UID: {uid}"
    
    def simulate_gate_open(self) -> List[str]:
        """Simulate gate opening sequence."""
        self.state = "OPEN"
        self.pos = 90
        return [
            "> GRANTED: Akses diterima",
            self.generate_status(),
        ]


def test_mock_esp32_generates_realistic_data():
    """Verify mock ESP32 generates parseable data."""
    mock = MockESP32("ENTRY")
    
    # Generate status
    status_line = mock.generate_status()
    parsed = parse_st(status_line)
    
    assert parsed is not None
    assert parsed.state == "IDLE"
    assert parsed.count == 1
    
    # Simulate opening
    logs = mock.simulate_gate_open()
    assert len(logs) == 2
    assert "GRANTED" in logs[0]
    
    parsed = parse_st(logs[1])
    assert parsed.state == "OPEN"
    assert parsed.pos == 90
    
    print("✓ Mock ESP32 generates realistic data")


# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("IoT ↔ Backend ↔ Dashboard Integration Test")
    print("="*70 + "\n")
    
    # Protocol tests
    print("📡 Testing Protocol Layer...")
    test_protocol_parse_status_entry()
    test_protocol_parse_status_exit()
    test_protocol_build_commands()
    
    # Async tests
    print("\n🔌 Testing Serial Communication...")
    asyncio.run(test_serial_reader_processes_status())
    asyncio.run(test_serial_reader_extracts_card_uid())
    
    print("\n🌐 Testing WebSocket Layer...")
    asyncio.run(test_websocket_broadcast())
    
    print("\n🔄 Testing End-to-End Flow...")
    asyncio.run(test_end_to_end_status_flow())
    asyncio.run(test_end_to_end_card_tap_flow())
    asyncio.run(test_command_flow_dashboard_to_iot())
    
    print("\n🤖 Testing Mock IoT Generator...")
    test_mock_esp32_generates_realistic_data()
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED - Systems can communicate!")
    print("="*70 + "\n")
