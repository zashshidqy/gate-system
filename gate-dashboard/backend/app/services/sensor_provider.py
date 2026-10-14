"""Sensor data provider - bridges IoT sensors with ticket system"""
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class SensorDataProvider:
    """Provides real-time sensor data from gates for ticket validation."""
    
    def __init__(self, serial_bridge=None):
        self.serial_bridge = serial_bridge
    
    def get_sensor_data(self, gate: str) -> Optional[Dict[str, Any]]:
        """Get current sensor readings from a gate.
        
        Returns a dict with sensor data:
        - state: Gate state (IDLE, OPENING, OPEN, CLOSING)
        - pos: Servo position (0-90)
        - front_cm: Front sensor distance in cm
        - exit_cm: Exit sensor distance in cm
        - vehicle: Vehicle detected (bool)
        - rfid_ver: RFID module version
        - last_uid: Last scanned RFID UID
        - last_auth: Last authorization result
        - count: Status update counter
        - timestamp: When this data was captured
        """
        if not self.serial_bridge:
            logger.warning("No serial bridge available for sensor data")
            return None
        
        gate_upper = gate.upper()
        reader = self.serial_bridge.readers.get(gate_upper)
        
        if not reader or not reader.status:
            logger.warning(f"No sensor data available for {gate_upper}")
            return None
        
        status = reader.status
        
        # Convert parsed status to dict for JSON serialization
        sensor_data = {
            "state": status.state,
            "pos": status.pos,
            "front_cm": status.front_cm,
            "exit_cm": status.exit_cm,
            "vehicle": status.vehicle,
            "rfid_ver": status.rfid_ver,
            "last_uid": status.last_uid,
            "last_auth": status.last_auth,
            "count": status.count,
            "lcd1": status.lcd1,
            "lcd2": status.lcd2,
            "masters": status.masters,
        }
        
        logger.info(
            f"Captured sensor data for {gate_upper}: "
            f"state={status.state}, vehicle={status.vehicle}, "
            f"front={status.front_cm}cm, exit={status.exit_cm}cm"
        )
        
        return sensor_data
    
    def is_vehicle_present(self, gate: str) -> bool:
        """Check if a vehicle is currently detected at the gate."""
        sensor_data = self.get_sensor_data(gate)
        if sensor_data:
            return sensor_data.get("vehicle", False)
        return False
    
    def get_distance_readings(self, gate: str) -> Optional[Dict[str, int]]:
        """Get distance sensor readings."""
        sensor_data = self.get_sensor_data(gate)
        if sensor_data:
            return {
                "front_cm": sensor_data.get("front_cm"),
                "exit_cm": sensor_data.get("exit_cm"),
            }
        return None
    
    def get_gate_state(self, gate: str) -> Optional[str]:
        """Get current gate state (IDLE, OPENING, OPEN, CLOSING)."""
        sensor_data = self.get_sensor_data(gate)
        if sensor_data:
            return sensor_data.get("state")
        return None
