"""Test ticket system integration with IoT sensor data"""
import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.protocol import ParsedGateStatus
from app.services.sensor_provider import SensorDataProvider
from app.services.ticket_engine import TicketEngine, ValidationMethod
from app.models.ticket import TicketToken, TicketUsage, TicketType
from app.database import Base

# Create test database
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# ============================================================================
# TEST 1: Sensor Data Provider
# ============================================================================

@pytest.mark.asyncio
async def test_sensor_provider_reads_gate_data():
    """Verify sensor provider can extract data from serial bridge."""
    # Create mock serial bridge with sensor data
    mock_bridge = MagicMock()
    
    # Simulate ENTRY gate with vehicle present
    mock_reader = MagicMock()
    mock_reader.status = ParsedGateStatus(
        state="IDLE",
        pos=0,
        front_cm=50,  # Vehicle close
        vehicle=True,
        lcd1="Selamat Datang",
        lcd2="Tap Kartu",
        masters=["04E12345AB67"],
        exit_cm=180,
        rfid_ver="V2.1.0",
        last_uid="04E12345AB67",
        last_auth="GRANTED",
        count=42,
    )
    
    mock_bridge.readers = {"ENTRY": mock_reader}
    
    # Create sensor provider
    provider = SensorDataProvider(mock_bridge)
    
    # Get sensor data
    sensor_data = provider.get_sensor_data("ENTRY")
    
    assert sensor_data is not None
    assert sensor_data["state"] == "IDLE"
    assert sensor_data["vehicle"] is True
    assert sensor_data["front_cm"] == 50
    assert sensor_data["exit_cm"] == 180
    assert sensor_data["last_uid"] == "04E12345AB67"
    assert sensor_data["last_auth"] == "GRANTED"
    
    print("✓ Sensor provider correctly reads gate data")


@pytest.mark.asyncio
async def test_sensor_provider_vehicle_detection():
    """Verify sensor provider can detect vehicle presence."""
    mock_bridge = MagicMock()
    mock_reader = MagicMock()
    mock_reader.status = ParsedGateStatus(
        state="IDLE",
        pos=0,
        front_cm=50,
        vehicle=True,  # Vehicle present
        lcd1="Test",
        lcd2="Test",
        masters=[],
        exit_cm=180,
        rfid_ver="V2.1.0",
        last_uid=None,
        last_auth=None,
        count=1,
    )
    
    mock_bridge.readers = {"EXIT": mock_reader}
    provider = SensorDataProvider(mock_bridge)
    
    # Check vehicle detection
    assert provider.is_vehicle_present("EXIT") is True
    
    # Simulate vehicle leaving
    mock_reader.status.vehicle = False
    mock_reader.status.front_cm = 245
    
    assert provider.is_vehicle_present("EXIT") is False
    
    print("✓ Sensor provider detects vehicle presence correctly")


# ============================================================================
# TEST 2: Ticket Engine with Sensor Data
# ============================================================================

def test_ticket_engine_stores_sensor_data():
    """Verify ticket validation captures and stores sensor data."""
    # Setup test database
    Base.metadata.create_all(bind=test_engine)
    db = TestSessionLocal()
    
    try:
        # Create a test ticket
        now = datetime.utcnow()
        token = TicketToken(
            code="TEST-ABC123",
            qr_payload="{}",
            type=TicketType.SINGLE_ENTRY,
            valid_from=now,
            valid_until=now + timedelta(days=1),
            max_uses=1,
            issued_by="test_user",
        )
        db.add(token)
        db.commit()
        
        # Prepare sensor data (simulating real gate sensors)
        sensor_data = {
            "state": "IDLE",
            "pos": 0,
            "front_cm": 50,
            "exit_cm": 180,
            "vehicle": True,
            "rfid_ver": "V2.1.0",
            "last_uid": "04E12345AB67",
            "last_auth": "GRANTED",
            "count": 42,
            "lcd1": "Selamat Datang",
            "lcd2": "Tap Kartu",
            "masters": ["04E12345AB67"],
        }
        
        # Validate ticket with sensor data
        engine = TicketEngine(db)
        result = engine.validate(
            token_code="TEST-ABC123",
            gate="ENTRY",
            method=ValidationMethod.QR_SCAN,
            sensor_data=sensor_data
        )
        
        assert result.allowed is True
        assert result.usage_id is not None
        
        # Retrieve the usage record
        usage = db.query(TicketUsage).filter(TicketUsage.id == result.usage_id).first()
        
        assert usage is not None
        assert usage.gate_id == "ENTRY"
        assert usage.direction == "IN"
        assert usage.sensor_data_json is not None
        
        # Verify sensor data was stored correctly
        stored_data = usage.parsed_sensor_data
        assert stored_data["state"] == "IDLE"
        assert stored_data["vehicle"] is True
        assert stored_data["front_cm"] == 50
        assert stored_data["exit_cm"] == 180
        assert stored_data["last_uid"] == "04E12345AB67"
        
        print("✓ Ticket engine stores sensor data correctly")
        
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


def test_ticket_validation_without_sensor_data():
    """Verify ticket validation works even without sensor data."""
    Base.metadata.create_all(bind=test_engine)
    db = TestSessionLocal()
    
    try:
        now = datetime.utcnow()
        token = TicketToken(
            code="TEST-XYZ789",
            qr_payload="{}",
            type=TicketType.SINGLE_ENTRY,
            valid_from=now,
            valid_until=now + timedelta(days=1),
            max_uses=1,
            issued_by="test_user",
        )
        db.add(token)
        db.commit()
        
        # Validate without sensor data (offline mode)
        engine = TicketEngine(db)
        result = engine.validate(
            token_code="TEST-XYZ789",
            gate="ENTRY",
            method=ValidationMethod.MANUAL,
            sensor_data=None  # No sensor data
        )
        
        assert result.allowed is True
        
        # Verify usage was recorded without sensor data
        usage = db.query(TicketUsage).filter(TicketUsage.id == result.usage_id).first()
        assert usage is not None
        assert usage.sensor_data_json is None
        
        print("✓ Ticket validation works without sensor data (graceful degradation)")
        
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("Ticket ↔ IoT Sensor Integration Tests")
    print("="*70 + "\n")
    
    print("🔌 Testing Sensor Data Provider...")
    asyncio.run(test_sensor_provider_reads_gate_data())
    asyncio.run(test_sensor_provider_vehicle_detection())
    
    print("\n🎫 Testing Ticket Engine with Sensors...")
    test_ticket_engine_stores_sensor_data()
    test_ticket_validation_without_sensor_data()
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED - Tickets can read sensor data!")
    print("="*70 + "\n")
