"""WebSocket connection manager"""
import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str = "default"):
        await websocket.accept()
        async with self._lock:
            if client_id not in self.active_connections:
                self.active_connections[client_id] = set()
            self.active_connections[client_id].add(websocket)
        logger.info(f"WebSocket connected: {client_id} (total: {self.total_connections})")

    async def disconnect(self, websocket: WebSocket, client_id: str = "default"):
        async with self._lock:
            if client_id in self.active_connections:
                self.active_connections[client_id].discard(websocket)
                if not self.active_connections[client_id]:
                    del self.active_connections[client_id]
        logger.info(f"WebSocket disconnected: {client_id} (total: {self.total_connections})")

    @property
    def total_connections(self) -> int:
        return sum(len(conns) for conns in self.active_connections.values())

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")

    async def broadcast(self, message: dict, client_id: str = None):
        """Broadcast message to all connections or specific client_id."""
        msg = json.dumps(message)
        if client_id:
            targets = self.active_connections.get(client_id, set())
        else:
            targets = set()
            for conns in self.active_connections.values():
                targets.update(conns)

        disconnected = []
        for ws in targets:
            try:
                await ws.send_text(msg)
            except Exception:
                disconnected.append(ws)

        # Clean up disconnected
        for ws in disconnected:
            for cid, conns in self.active_connections.items():
                conns.discard(ws)


# Global instance
ws_manager = ConnectionManager()