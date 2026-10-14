# Ticket ↔ IoT Sensor Integration Documentation

## ✅ Integration Complete

The ticket system now successfully reads and captures sensor data from the IoT gates in real-time.

---

## 🎯 What Was Achieved

**Before:** Ticket validation only checked token validity (expiry, revocation, usage count) but didn't capture any physical sensor data from the gates.

**After:** Every ticket validation now captures a complete snapshot of the gate's sensor readings at the exact moment of validation.

---

## 📊 Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    Vehicle Approaches Gate                    │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                ESP32 Sensors (Real-time)                      │
│                                                               │
│  • Front ultrasonic: 50cm (vehicle detected)                 │
│  • Exit ultrasonic: 180cm                                    │
│  • Vehicle presence: TRUE                                    │
│  • Gate state: IDLE                                          │
│  • Servo position: 0° (closed)                               │
│  • RFID reader: Active                                       │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ Serial 115200 baud
                            │ ST|IDLE|0|50|1|...
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│              Backend (Serial Bridge + Protocol)               │
│                                                               │
│  Parses sensor data into structured format                   │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
                    User scans QR ticket
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│           Ticket Validation (Ticket Engine)                   │
│                                                               │
│  1. Validates ticket (expiry, revoked, usage)                │
│  2. Gets current sensor data from gate                       │
│  3. Records validation + sensor snapshot                     │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                   Database (ticket_usages)                    │
│                                                               │
│  Stores:                                                     │
│  • Token ID                                                  │
│  • Gate ID (ENTRY/EXIT)                                     │
│  • Timestamp                                                 │
│  • Allowed (true/false)                                     │
│  • Validation method (QR_SCAN, RFID_LINK, MANUAL)          │
│  • sensor_data_json (complete sensor snapshot) ← NEW!       │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔧 Changes Made

### 1. Database Schema

**New Field Added:**
```sql
ALTER TABLE ticket_usages 
ADD COLUMN sensor_data_json TEXT;
```

This field stores a JSON snapshot of all sensor readings at validation time.

### 2. New Service: `SensorDataProvider`

**File:** `app/services/sensor_provider.py`

Bridges the IoT sensor data from the serial bridge to the ticket system.

**Methods:**
- `get_sensor_data(gate)` - Gets complete sensor snapshot from a gate
- `is_vehicle_present(gate)` - Quick check if vehicle is detected
- `get_distance_readings(gate)` - Gets ultrasonic sensor readings
- `get_gate_state(gate)` - Gets current gate state

**Example Usage:**
```python
from app.services.sensor_provider import SensorDataProvider

provider = SensorDataProvider(serial_bridge)
sensor_data = provider.get_sensor_data("ENTRY")

# Returns:
{
    "state": "IDLE",
    "pos": 0,
    "front_cm": 50,
    "exit_cm": 180,
    "vehicle": True,
    "rfid_ver": "V2.1.0",
    "last_uid": "04E12345AB67",
    "last_auth": "GRANTED",
    "count": 128,
    "lcd1": "Selamat Datang",
    "lcd2": "Tap Kartu",
    "masters": ["04E12345AB67", "A1B2C3D4E5F6"]
}
```

### 3. Updated: `TicketEngine`

**File:** `app/services/ticket_engine.py`

Now accepts sensor data during validation:

```python
def validate(
    self,
    token_code: str,
    gate: str,
    method: ValidationMethod,
    sensor_data: Optional[Dict[str, Any]] = None,  # ← NEW parameter
) -> ValidationResult:
    # ... validation logic ...
    
    # Store sensor data with usage record
    usage = TicketUsage(
        # ... existing fields ...
        sensor_data_json=json.dumps(sensor_data) if sensor_data else None,
    )
```

### 4. Updated: Ticket Validation API

**File:** `app/api/tickets.py`

Now automatically captures sensor data when validating:

```python
@router.post("/validate", response_model=TicketValidationResponse)
def validate_ticket(request: TicketValidationRequest, ...):
    # Get real-time sensor data from gate
    sensor_data = None
    try:
        from ..api.gates import serial_bridge
        if serial_bridge:
            sensor_provider = SensorDataProvider(serial_bridge)
            sensor_data = sensor_provider.get_sensor_data(request.gate)
    except Exception as e:
        logger.warning(f"Failed to get sensor data: {e}")
    
    # Validate with sensor data
    result = engine.validate(
        request.token_code,
        request.gate,
        ValidationMethod(request.method),
        sensor_data=sensor_data  # ← Sensor data included
    )
```

### 5. Updated: Models and Schemas

**Models (`app/models/ticket.py`):**
```python
class TicketUsage(Base):
    # ... existing fields ...
    sensor_data_json = Column(Text, nullable=True)
    
    @property
    def parsed_sensor_data(self):
        """Parse sensor_data_json as dict."""
        if self.sensor_data_json:
            return json.loads(self.sensor_data_json)
        return {}
```

**Schemas (`app/schemas/ticket.py`):**
```python
class TicketUsageResponse(BaseModel):
    # ... existing fields ...
    parsed_sensor_data: Optional[dict[str, Any]] = None  # ← NEW
```

---

## 📝 Sensor Data Captured

When a ticket is validated, the following sensor readings are captured:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `state` | string | Gate state | "IDLE", "OPENING", "OPEN", "CLOSING" |
| `pos` | int | Servo position (degrees) | 0 (closed) to 90 (open) |
| `front_cm` | int | Front ultrasonic distance (cm) | 50 = vehicle present, 245 = clear |
| `exit_cm` | int | Exit ultrasonic distance (cm) | 180 = normal |
| `vehicle` | bool | Vehicle presence sensor | true/false |
| `rfid_ver` | string | RFID module version | "V2.1.0" |
| `last_uid` | string | Last scanned RFID UID | "04E12345AB67" |
| `last_auth` | string | Last authorization result | "GRANTED", "DENIED" |
| `count` | int | Status update counter | Increments with each update |
| `lcd1` | string | LCD display line 1 | "Selamat Datang" |
| `lcd2` | string | LCD display line 2 | "Tap Kartu" |
| `masters` | array | Master RFID cards | ["04E12345AB67", ...] |

---

## 🧪 Testing

### Tests Created

**File:** `tests/test_ticket_sensor_integration.py`

**Test Coverage:**
1. ✅ Sensor provider reads gate data correctly
2. ✅ Vehicle detection works
3. ✅ Ticket engine stores sensor data in database
4. ✅ Ticket validation works without sensor data (offline mode)

**Run Tests:**
```bash
cd gate-dashboard/backend
source .venv/bin/activate
python -m pytest tests/test_ticket_sensor_integration.py -v
```

**Results:** 4/4 tests passed ✅

---

## 🎯 Use Cases

### 1. **Proof of Vehicle Presence**

When a ticket is validated, you can verify that a vehicle was actually present:

```python
usage = db.query(TicketUsage).filter(...).first()
sensor_data = usage.parsed_sensor_data

if sensor_data and sensor_data["vehicle"]:
    print("✅ Vehicle was confirmed present at validation")
    print(f"   Distance: {sensor_data['front_cm']}cm from gate")
else:
    print("⚠️ No vehicle detected during validation")
```

### 2. **Fraud Detection**

Detect suspicious patterns:

```python
# Check if ticket was validated without a vehicle present
if usage.allowed and not sensor_data.get("vehicle"):
    flag_for_review("Ticket validated without vehicle present")

# Check if multiple tickets validated too quickly (same counter)
if previous_usage.sensor_data["count"] == current_usage.sensor_data["count"]:
    flag_for_review("Suspiciously fast validation sequence")
```

### 3. **Analytics & Reporting**

Generate insights from sensor data:

```python
# Average vehicle approach distance
avg_distance = db.query(
    func.avg(
        func.json_extract(TicketUsage.sensor_data_json, '$.front_cm')
    )
).filter(
    TicketUsage.gate_id == "ENTRY",
    TicketUsage.allowed == True
).scalar()

# Peak usage times with vehicle counts
# Gate state distribution during validations
# etc.
```

### 4. **Troubleshooting**

Diagnose gate or sensor issues:

```python
# Find validations where gate was stuck
stuck_gates = db.query(TicketUsage).filter(
    func.json_extract(TicketUsage.sensor_data_json, '$.state') == 'OPENING',
    TicketUsage.timestamp < datetime.now() - timedelta(minutes=5)
).all()

# Find validations with sensor reading anomalies
anomalies = db.query(TicketUsage).filter(
    func.json_extract(TicketUsage.sensor_data_json, '$.front_cm') < 10
).all()  # Too close - possible sensor fault
```

---

## 📡 API Examples

### Validate Ticket (Auto-captures sensors)

**Request:**
```http
POST /api/tickets/validate
Authorization: Bearer <token>
Content-Type: application/json

{
  "token_code": "GATE-ABC123",
  "gate": "ENTRY",
  "method": "QR_SCAN"
}
```

**Response:**
```json
{
  "allowed": true,
  "reason": null,
  "token": {
    "id": "...",
    "code": "GATE-ABC123",
    "type": "SINGLE_ENTRY",
    "used_count": 1,
    "max_uses": 1
  },
  "usage_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Get Ticket Usage History (with sensor data)

**Request:**
```http
GET /api/tickets/<token_id>/usages
Authorization: Bearer <token>
```

**Response:**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "token_id": "...",
      "gate_id": "ENTRY",
      "direction": "IN",
      "timestamp": "2026-10-12T06:15:30.123Z",
      "allowed": true,
      "method": "QR_SCAN",
      "parsed_sensor_data": {
        "state": "IDLE",
        "pos": 0,
        "front_cm": 50,
        "exit_cm": 180,
        "vehicle": true,
        "rfid_ver": "V2.1.0",
        "last_uid": null,
        "last_auth": null,
        "count": 142,
        "lcd1": "Scan QR Code",
        "lcd2": "or Tap Card",
        "masters": ["04E12345AB67"]
      }
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 50
}
```

---

## 🔒 Graceful Degradation

The system works even when sensor data is unavailable:

**Scenarios:**
1. **Gates offline** - Ticket validation still works, sensor_data_json is null
2. **Serial connection lost** - System logs warning, continues validation
3. **Malformed sensor data** - Logged and skipped, doesn't block validation

This ensures the ticket system remains operational even if IoT hardware fails.

---

## 🚀 Migration

**Database migration created:**
```bash
alembic/versions/022261e1c847_add_sensor_data_to_ticket_usages.py
```

**Apply migration:**
```bash
cd gate-dashboard/backend
source .venv/bin/activate
alembic upgrade head
```

**Existing data:** Existing ticket_usages records will have `sensor_data_json = null`, which is expected.

---

## 📊 Summary

### ✅ What Works Now

1. **Real-time sensor capture** - Every ticket validation captures live sensor data
2. **Complete snapshot** - All 12+ sensor fields stored as JSON
3. **Vehicle verification** - Confirms vehicle presence during validation
4. **Historical analysis** - Query sensor data from past validations
5. **Graceful fallback** - System works even if sensors unavailable
6. **Fully tested** - 4/4 integration tests passing

### 🎯 Benefits

- **Fraud prevention** - Detect tickets validated without vehicles
- **Audit trail** - Complete record of physical conditions during validation
- **Analytics** - Analyze traffic patterns, sensor performance
- **Troubleshooting** - Diagnose gate/sensor issues from historical data
- **Compliance** - Prove vehicles were present during entry/exit

### 📈 Next Steps (Optional Enhancements)

1. **Dashboard UI** - Display sensor data in ticket history view
2. **Alerts** - Notify staff of suspicious validations (no vehicle, stuck gate)
3. **Reports** - Generate analytics dashboards from sensor data
4. **ANPR Integration** - Cross-reference with license plate capture
5. **ML Analysis** - Detect patterns and anomalies

---

## 🧪 Verification

To verify the integration is working:

1. **Run tests:**
   ```bash
   pytest tests/test_ticket_sensor_integration.py -v
   ```

2. **Check database:**
   ```bash
   sqlite3 gate.db
   sqlite> SELECT sensor_data_json FROM ticket_usages LIMIT 1;
   ```

3. **Validate a ticket** (with gates connected):
   - Ensure gates are connected and sending sensor data
   - Validate a ticket via API
   - Check the usage record has sensor_data_json populated

---

**Integration Status:** ✅ **COMPLETE AND VERIFIED**

All ticket validations now capture real-time IoT sensor data!
