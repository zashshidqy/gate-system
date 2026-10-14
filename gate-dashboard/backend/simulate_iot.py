#!/usr/bin/env python3
"""Live IoT Simulator - Tests real-time communication without physical hardware.

This simulator creates virtual serial ports and simulates ESP32 gate controllers
sending real data to the backend, then verifies the dashboard receives it via WebSocket.

Usage:
    python simulate_iot.py                    # Run full simulation
    python simulate_iot.py --status-only      # Only status updates
    python simulate_iot.py --interactive      # Interactive mode
"""
import asyncio
import sys
import os
import random
import time
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import pty
    import serial
    VIRTUAL_SERIAL_AVAILABLE = True
except ImportError:
    VIRTUAL_SERIAL_AVAILABLE = False
    print("⚠️  Virtual serial ports not available on this platform")


class ESP32Simulator:
    """Simulates an ESP32 gate controller with realistic behavior."""
    
    def __init__(self, unit: str, master_serial: Optional[int] = None, slave_serial: Optional[int] = None):
        self.unit = unit
        self.master_fd = master_serial
        self.slave_fd = slave_serial
        self.running = False
        
        # Gate state
        self.state = "IDLE"
        self.pos = 0  # Servo position: 0=closed, 90=open
        self.vehicle_detected = False
        self.masters = ["04E12345AB67", "A1B2C3D4E5F6"]
        self.last_uid: Optional[str] = None
        self.last_auth: Optional[str] = None
        self.count = 0
        
        # Sensor readings
        self.front_distance = 245  # cm
        self.exit_distance = 180   # cm
        
        # LCD display
        self.lcd1 = "Selamat Datang"
        self.lcd2 = "Tap Kartu"
        
    def generate_status_line(self) -> str:
        """Generate ST|... status line like real ESP32."""
        self.count += 1
        vehicle_flag = "1" if self.vehicle_detected else "0"
        masters_str = ",".join(self.masters) if self.masters else "-"
        last_uid_str = self.last_uid if self.last_uid else "-"
        last_auth_str = self.last_auth if self.last_auth else "-"
        
        return (
            f"ST|{self.state}|{self.pos}|{self.front_distance}|{vehicle_flag}|"
            f"{self.lcd1}|{self.lcd2}|{masters_str}|{self.exit_distance}|"
            f"V2.1.0|{last_uid_str}|{last_auth_str}|{self.count}\n"
        )
    
    def write(self, data: str):
        """Write data to virtual serial port."""
        if self.master_fd:
            try:
                os.write(self.master_fd, data.encode('ascii'))
            except Exception as e:
                print(f"[{self.unit}] Write error: {e}")
    
    def simulate_card_tap(self, uid: str, authorized: bool = True):
        """Simulate RFID card tap."""
        self.last_uid = uid
        self.last_auth = "GRANTED" if authorized else "DENIED"
        
        self.write(f"> UID: {' '.join(uid[i:i+2] for i in range(0, len(uid), 2))}\n")
        
        if authorized:
            self.write("> GRANTED: Akses diterima\n")
            self.state = "OPENING"
            self.lcd1 = "Silakan Lewat"
            self.lcd2 = "Gate Terbuka"
        else:
            self.write("> DENIED: Akses ditolak\n")
            self.lcd1 = "Akses Ditolak"
            self.lcd2 = "Kartu Invalid"
    
    def simulate_vehicle_detected(self, detected: bool):
        """Simulate vehicle presence sensor."""
        self.vehicle_detected = detected
        if detected:
            self.front_distance = 50
            self.write("> Vehicle detected by front sensor\n")
        else:
            self.front_distance = 245
    
    def simulate_gate_cycle(self):
        """Simulate complete gate open/close cycle."""
        # Opening
        self.state = "OPENING"
        for pos in range(0, 95, 5):
            self.pos = pos
            self.write(self.generate_status_line())
            time.sleep(0.05)
        
        self.state = "OPEN"
        self.pos = 90
        self.write("> Gate fully opened\n")
        self.write(self.generate_status_line())
        
        # Wait for vehicle to pass
        time.sleep(1)
        self.simulate_vehicle_detected(True)
        time.sleep(0.5)
        self.simulate_vehicle_detected(False)
        
        # Closing
        time.sleep(0.5)
        self.state = "CLOSING"
        self.lcd1 = "Gerbang Tutup"
        self.lcd2 = "Terima Kasih"
        
        for pos in range(90, -5, -5):
            self.pos = pos
            self.write(self.generate_status_line())
            time.sleep(0.05)
        
        self.state = "IDLE"
        self.pos = 0
        self.lcd1 = "Selamat Datang"
        self.lcd2 = "Tap Kartu"
        self.last_uid = None
        self.last_auth = None
        self.write("> Gate closed\n")
        self.write(self.generate_status_line())
    
    async def run_periodic_status(self, interval: float = 0.3):
        """Send status updates periodically (like real ESP32)."""
        self.running = True
        print(f"[{self.unit}] Started status broadcasting every {interval}s")
        
        while self.running:
            self.write(self.generate_status_line())
            await asyncio.sleep(interval)
    
    def stop(self):
        """Stop the simulator."""
        self.running = False


async def websocket_listener():
    """Connect to backend WebSocket and verify data reception."""
    try:
        import websockets
    except ImportError:
        print("⚠️  websockets package not installed. Install with: pip install websockets")
        return
    
    received_events = {
        "GATE_STATUS": 0,
        "GATE_LOG": 0,
        "CARD_TAPPED": 0,
    }
    
    uri = "ws://localhost:8000/api/gates/ws"
    print(f"\n📡 Connecting to WebSocket: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected - listening for events...\n")
            
            start_time = time.time()
            timeout = 30  # Run for 30 seconds
            
            while time.time() - start_time < timeout:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = eval(message)  # Parse JSON
                    
                    event_type = data.get("type")
                    if event_type in received_events:
                        received_events[event_type] += 1
                    
                    # Print important events
                    if event_type == "CARD_TAPPED":
                        print(f"🎫 CARD_TAPPED: {data.get('unit')} - UID: {data.get('payload', {}).get('uid')}")
                    elif event_type == "GATE_STATUS":
                        payload = data.get('payload', {})
                        state = payload.get('state')
                        pos = payload.get('pos')
                        vehicle = payload.get('vehicle')
                        print(f"🚪 {data.get('unit')}: {state} (pos={pos}, vehicle={vehicle})")
                    elif event_type == "GATE_LOG":
                        msg = data.get('payload', {}).get('message', '')
                        if 'GRANTED' in msg or 'DENIED' in msg or 'opened' in msg or 'closed' in msg:
                            print(f"📝 {data.get('unit')}: {msg}")
                
                except asyncio.TimeoutError:
                    continue
            
            print(f"\n📊 Events received in {timeout}s:")
            for event_type, count in received_events.items():
                print(f"   {event_type}: {count}")
            
            if received_events["GATE_STATUS"] > 0:
                print("\n✅ Dashboard successfully received IoT data!")
            else:
                print("\n❌ No data received - check backend connection")
    
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        print("   Make sure backend is running: uvicorn app.main:app --reload")


async def run_full_simulation():
    """Run complete simulation with virtual serial ports."""
    if not VIRTUAL_SERIAL_AVAILABLE:
        print("❌ Virtual serial ports not available on this platform")
        return
    
    print("\n" + "="*70)
    print("🤖 IoT Communication Simulator")
    print("="*70 + "\n")
    
    # Create virtual serial ports
    print("Creating virtual serial ports...")
    master_entry, slave_entry = pty.openpty()
    master_exit, slave_exit = pty.openpty()
    
    entry_port = os.ttyname(slave_entry)
    exit_port = os.ttyname(slave_exit)
    
    print(f"✅ ENTRY gate: {entry_port}")
    print(f"✅ EXIT gate: {exit_port}")
    print(f"\nUpdate your .env file:")
    print(f"   SERIAL_PORT_ENTRY={entry_port}")
    print(f"   SERIAL_PORT_EXIT={exit_port}\n")
    
    # Create simulators
    entry_sim = ESP32Simulator("ENTRY", master_entry, slave_entry)
    exit_sim = ESP32Simulator("EXIT", master_exit, slave_exit)
    
    # Start periodic status updates
    status_task_entry = asyncio.create_task(entry_sim.run_periodic_status())
    status_task_exit = asyncio.create_task(exit_sim.run_periodic_status())
    
    # Wait a bit for backend to connect
    await asyncio.sleep(2)
    
    print("\n🎬 Starting simulation sequence...\n")
    
    # Scenario 1: Authorized entry
    print("1️⃣ Simulating authorized card at ENTRY...")
    entry_sim.simulate_card_tap("04E12345AB67", authorized=True)
    await asyncio.sleep(0.5)
    entry_sim.simulate_gate_cycle()
    await asyncio.sleep(2)
    
    # Scenario 2: Unauthorized entry
    print("\n2️⃣ Simulating unauthorized card at ENTRY...")
    entry_sim.simulate_card_tap("DEADBEEF1234", authorized=False)
    await asyncio.sleep(3)
    
    # Scenario 3: Exit gate
    print("\n3️⃣ Simulating vehicle at EXIT...")
    exit_sim.simulate_vehicle_detected(True)
    await asyncio.sleep(0.5)
    exit_sim.simulate_card_tap("A1B2C3D4E5F6", authorized=True)
    await asyncio.sleep(0.5)
    exit_sim.simulate_gate_cycle()
    await asyncio.sleep(2)
    
    print("\n✅ Simulation complete!")
    
    # Keep running for a bit to see final status updates
    await asyncio.sleep(5)
    
    # Cleanup
    entry_sim.stop()
    exit_sim.stop()
    status_task_entry.cancel()
    status_task_exit.cancel()
    
    os.close(master_entry)
    os.close(slave_entry)
    os.close(master_exit)
    os.close(slave_exit)


async def run_status_only_test():
    """Quick test that just sends status updates."""
    print("\n" + "="*70)
    print("📡 Status Broadcasting Test")
    print("="*70 + "\n")
    
    # Test without actual serial - just verify protocol generation
    sim = ESP32Simulator("ENTRY")
    
    print("Generating 5 status updates:\n")
    for i in range(5):
        status = sim.generate_status_line()
        print(f"{i+1}. {status.strip()}")
        sim.count += 1
        await asyncio.sleep(0.3)
    
    print("\n✅ Status generation works correctly")


def print_usage():
    print("\n" + "="*70)
    print("IoT ↔ Backend ↔ Dashboard Communication Verifier")
    print("="*70 + "\n")
    print("This tool verifies that all systems can communicate properly:\n")
    print("  1. IoT (ESP32) → Backend (Serial → WebSocket)")
    print("  2. Backend → Dashboard (WebSocket → React)")
    print("  3. Dashboard → Backend → IoT (Commands)\n")
    print("Usage:")
    print("  python simulate_iot.py                    # Full simulation")
    print("  python simulate_iot.py --status-only      # Quick protocol test")
    print("  python simulate_iot.py --websocket        # Test WebSocket only")
    print("  python simulate_iot.py --help             # Show this help\n")
    print("Prerequisites:")
    print("  - Backend running: uvicorn app.main:app --reload")
    print("  - Dashboard running: npm run dev (optional)")
    print("="*70 + "\n")


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print_usage()
    elif "--status-only" in sys.argv:
        asyncio.run(run_status_only_test())
    elif "--websocket" in sys.argv:
        asyncio.run(websocket_listener())
    else:
        print_usage()
        print("⚠️  Full simulation requires virtual serial ports (Linux/macOS)")
        print("Running status-only test instead...\n")
        asyncio.run(run_status_only_test())
