"""Async serial bridge for ESP32 communication"""
import asyncio
import serial_asyncio
import serial
import logging
from typing import Optional, Dict, Callable, Awaitable
import re
from dataclasses import dataclass

from app.config import get_settings
from app.services.protocol import parse_st, build_command, ParsedGateStatus, LogTag
from app.websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)


@dataclass(eq=False)
class SerialReader:
    """Manages a single serial connection to an ESP32 unit.

    ``eq=False`` keeps identity-based equality and hashing. A generated
    ``__eq__`` would also null out ``__hash__`` and try to compare asyncio
    primitives, which is never what a caller wants here.
    """

    unit: str  # "ENTRY" or "EXIT"
    port: str
    baudrate: int
    on_status: Callable[[str, ParsedGateStatus], Awaitable[None]]
    on_log: Callable[[str, str, LogTag], Awaitable[None]]
    on_card_tapped: Callable[[str, str], Awaitable[None]]

    # Latest status parsed from the device, mirrored here so /gates/status
    # can answer synchronously instead of rebuilding it from the socket.
    status: Optional[ParsedGateStatus] = None
    # True only while the port is actually open. A reader that failed to
    # start is never registered, so this is belt-and-braces.
    connected: bool = False

    _reader: Optional[asyncio.StreamReader] = None
    _writer: Optional[asyncio.StreamWriter] = None
    _task: Optional[asyncio.Task] = None
    _stop_event: asyncio.Event = None

    async def start(self):
        self._stop_event = asyncio.Event()
        try:
            self._reader, self._writer = await serial_asyncio.open_serial_connection(
                url=self.port, baudrate=self.baudrate
            )
            self.connected = True
            logger.info(f"[{self.unit}] Connected to {self.port}")
            self._task = asyncio.create_task(self._read_loop())
        except Exception as e:
            self.connected = False
            logger.error(f"[{self.unit}] Failed to connect to {self.port}: {e}")
            raise

    async def stop(self):
        self.connected = False
        if self._stop_event:
            self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
        logger.info(f"[{self.unit}] Disconnected")

    async def send_command(self, cmd: bytes):
        """Write one command byte to the open port.

        ``cmd`` is already bytes (see ``build_command``) — never encode here.
        A closed or missing port is logged rather than swallowed, so a
        dropped command is visible instead of silently reported as sent.
        """
        if self._writer and not self._writer.is_closing():
            self._writer.write(cmd + b"\n")
            await self._writer.drain()
        else:
            logger.warning(
                f"[{self.unit}] Dropped command {cmd!r}: serial port not open"
            )

    async def _read_loop(self):
        buffer = b""
        while not self._stop_event.is_set():
            try:
                data = await self._reader.read(512)
                if not data:
                    await asyncio.sleep(0.1)
                    continue

                buffer += data
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    txt = line.decode("ascii", errors="replace").strip()
                    await self._process_line(txt)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{self.unit}] Read error: {e}")
                await asyncio.sleep(1)

    async def _process_line(self, line: str):
        if line.startswith("ST|"):
            status = parse_st(line)
            if status:
                await self.on_status(self.unit, status)
                await self.on_log(self.unit, line, LogTag.INFO)
        elif line.startswith(">"):
            # Check for card tap events (UID read from RFID)
            card_uid = self._extract_uid_from_line(line)
            if card_uid:
                await self.on_card_tapped(self.unit, card_uid)

            tag = LogTag.INFO
            if any(kw in line for kw in ["DENIED", "gagal", "NO VEHICLE", "OBSTACLE", "UNAUTHORIZED"]):
                tag = LogTag.ERR
            elif "GRANTED" in line or "Master ditambahkan" in line or "Master dihapus" in line:
                tag = LogTag.OK
            elif "MODE" in line or "TUNGGU" in line:
                tag = LogTag.WARN
            await self.on_log(self.unit, line, tag)

    def _extract_uid_from_line(self, line: str) -> Optional[str]:
        """Extract UID hex string from ESP32 log lines.

        Matches patterns like:
          > Master ditambahkan: 04 E1 23 45 AB 67
          > Master dihapus: 04 E1 23 45 AB 67
          > UID: 04 E1 23 45 AB 67

        Returns the UID as a continuous uppercase hex string (e.g. "04E12345AB67"),
        or None if no UID pattern is found.
        """
        # Look for "XX XX XX XX" hex-byte patterns after a colon
        # The dumpUid format is: "04 E1 23 45 AB 67" (space-separated uppercase hex)
        # Match a colon followed by space-separated hex byte pairs
        match = re.search(r':((?:\s*[0-9A-Fa-f]{2})+)\s*$', line)
        if match:
            # Strip all spaces to get continuous hex string
            hex_bytes = match.group(1).replace(' ', '').upper()
            if len(hex_bytes) >= 4:  # At least 2 bytes
                return hex_bytes
        return None


class SerialBridge:
    """Manages serial connections for both ENTRY and EXIT units."""

    def __init__(self, ws_manager: ConnectionManager):
        self.ws_manager = ws_manager
        self.settings = get_settings()
        self.readers: Dict[str, SerialReader] = {}
        self._running = False

    async def start(self):
        if self._running:
            return
        self._running = True

        for unit, port in [("ENTRY", self.settings.SERIAL_PORT_ENTRY), ("EXIT", self.settings.SERIAL_PORT_EXIT)]:
            reader = SerialReader(
                unit=unit,
                port=port,
                baudrate=self.settings.SERIAL_BAUDRATE,
                on_status=self._on_status,
                on_log=self._on_log,
                on_card_tapped=self._on_card_tapped,
            )
            try:
                await reader.start()
            except Exception as e:
                logger.error(f"Failed to start {unit} reader: {e}")
                continue
            # Register only after start() succeeds: a reader that could not
            # open its port must not be reachable, or the "not connected"
            # guards pass and commands get dropped without an error.
            self.readers[unit] = reader

    def is_connected(self, unit: str) -> bool:
        """True only if ``unit`` has a reader whose port is actually open."""
        reader = self.readers.get(unit.upper())
        return bool(reader and reader.connected)

    async def stop(self):
        self._running = False
        for reader in self.readers.values():
            await reader.stop()
        self.readers.clear()

    async def send_command(self, unit: str, cmd: bytes):
        """Send an already-encoded command to a specific unit."""
        reader = self.readers.get(unit.upper())
        if reader is None or not reader.connected:
            logger.warning(
                f"Unit {unit} not connected; command {cmd!r} not sent"
            )
            return
        await reader.send_command(cmd)

    async def _on_status(self, unit: str, status: ParsedGateStatus):
        """Cache gate status, then broadcast it via WebSocket."""
        # Mirror the latest status on the reader first: /gates/status reads
        # it synchronously, so it must be current before we yield.
        reader = self.readers.get(unit)
        if reader is not None:
            reader.status = status
        await self.ws_manager.broadcast(
            {
                "type": "GATE_STATUS",
                "unit": unit,
                "payload": {
                    "state": status.state,
                    "pos": status.pos,
                    "front_cm": status.front_cm,
                    "vehicle": status.vehicle,
                    "lcd1": status.lcd1,
                    "lcd2": status.lcd2,
                    "masters": status.masters,
                    "exit_cm": status.exit_cm,
                    "rfid_ver": status.rfid_ver,
                    "last_uid": status.last_uid,
                    "last_auth": status.last_auth,
                    "count": status.count,
                },
            }
        )

    async def _on_log(self, unit: str, message: str, tag: LogTag):
        """Broadcast debug log via WebSocket."""
        await self.ws_manager.broadcast(
            {
                "type": "GATE_LOG",
                "unit": unit,
                "payload": {"message": message, "tag": tag.value},
            }
        )

    async def _on_card_tapped(self, unit: str, uid: str):
        """Broadcast card tap event via WebSocket."""
        logger.info(f"[{unit}] Card tapped: {uid}")
        await self.ws_manager.broadcast(
            {
                "type": "CARD_TAPPED",
                "unit": unit,
                "payload": {"uid": uid},
            }
        )