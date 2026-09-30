"""Async serial bridge for ESP32 communication"""
import asyncio
import serial_asyncio
import serial
import logging
from typing import Optional, Dict, Callable, Awaitable
from dataclasses import dataclass

from app.config import get_settings
from app.services.protocol import parse_st, build_command, ParsedGateStatus, LogTag
from app.websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)


@dataclass
class SerialReader:
    """Manages a single serial connection to an ESP32 unit."""
    unit: str  # "ENTRY" or "EXIT"
    port: str
    baudrate: int
    on_status: Callable[[str, ParsedGateStatus], Awaitable[None]]
    on_log: Callable[[str, str, LogTag], Awaitable[None]]

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
            logger.info(f"[{self.unit}] Connected to {self.port}")
            self._task = asyncio.create_task(self._read_loop())
        except Exception as e:
            logger.error(f"[{self.unit}] Failed to connect to {self.port}: {e}")
            raise

    async def stop(self):
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
        if self._writer and not self._writer.is_closing():
            self._writer.write(cmd + b"\n")
            await self._writer.drain()

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
            tag = LogTag.INFO
            if any(kw in line for kw in ["DENIED", "gagal", "NO VEHICLE", "OBSTACLE", "UNAUTHORIZED"]):
                tag = LogTag.ERR
            elif "GRANTED" in line or "Master ditambahkan" in line or "Master dihapus" in line:
                tag = LogTag.OK
            elif "MODE" in line or "TUNGGU" in line:
                tag = LogTag.WARN
            await self.on_log(self.unit, line, tag)


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
            )
            self.readers[unit] = reader
            try:
                await reader.start()
            except Exception as e:
                logger.error(f"Failed to start {unit} reader: {e}")

    async def stop(self):
        self._running = False
        for reader in self.readers.values():
            await reader.stop()
        self.readers.clear()

    async def send_command(self, unit: str, cmd: str):
        """Send a command to a specific unit."""
        reader = self.readers.get(unit.upper())
        if reader:
            await reader.send_command(cmd.encode("ascii"))
        else:
            logger.warning(f"Unit {unit} not connected")

    async def _on_status(self, unit: str, status: ParsedGateStatus):
        """Broadcast gate status via WebSocket."""
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