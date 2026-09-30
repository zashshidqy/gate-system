"""Gate control and status API"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from typing import Optional
import logging

from ..database import get_db
from ..models.ticket import TicketToken
from ..schemas.gate import GateCommand, UnitStatus
from ..schemas.common import MessageResponse
from ..schemas.ticket import QRCodeResponse, TicketTokenResponse
from ..services.serial_bridge import SerialBridge
from ..services.qr_generator import QRGenerator
from ..services.protocol import build_command
from ..websocket.manager import ws_manager
from ..dependencies import get_current_active_user, require_admin
from ..config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/gates", tags=["Gates"])

# Serial bridge instance (initialized in main.py)
serial_bridge: Optional[SerialBridge] = None


def get_serial_bridge() -> SerialBridge:
    if serial_bridge is None:
        raise HTTPException(status_code=503, detail="Serial bridge not initialized")
    return serial_bridge


@router.get("/status", response_model=dict)
async def get_gate_status(bridge: SerialBridge = Depends(get_serial_bridge)):
    """Get current status of both gates."""
    try:
        return {
            "ENTRY": {
                "connected": "ENTRY" in bridge.readers,
                "status": bridge.readers.get("ENTRY").status if "ENTRY" in bridge.readers else None
            },
            "EXIT": {
                "connected": "EXIT" in bridge.readers,
                "status": bridge.readers.get("EXIT").status if "EXIT" in bridge.readers else None
            },
        }
    except Exception as e:
        logger.error(f"Error getting gate status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get gate status")


@router.post("/command", response_model=MessageResponse)
async def send_gate_command(
    unit: str = Query(..., description="Gate unit: ENTRY or EXIT"),
    command: str = Query(..., description="Command: O (open), C (close), A (alert), Q (query)"),
    bridge: SerialBridge = Depends(get_serial_bridge),
    current_user=Depends(get_current_active_user),
):
    """Send a command to a gate unit."""
    try:
        unit_upper = unit.upper()
        if unit_upper not in ("ENTRY", "EXIT"):
            raise HTTPException(status_code=400, detail="Invalid unit. Use ENTRY or EXIT")
        
        if unit_upper not in bridge.readers:
            raise HTTPException(status_code=503, detail=f"{unit_upper} gate not connected")

        # Map command string to GateCommand enum
        command_map = {
            "O": GateCommand.OPEN,
            "C": GateCommand.CLOSE,
            "A": GateCommand.ALERT,
            "Q": GateCommand.QUERY,
            "L": GateCommand.LOCK,
            "R": GateCommand.RESET,
            "X": GateCommand.ADD_MASTER,
            "Z": GateCommand.DEL_MASTER,
        }
        
        gate_cmd = command_map.get(command.upper())
        if not gate_cmd:
            raise HTTPException(status_code=400, detail=f"Invalid command: {command}")

        await bridge.send_command(unit_upper, build_command(gate_cmd))
        logger.info(f"Command {command} sent to {unit_upper} by {current_user.username}")
        return MessageResponse(message=f"Command {command} sent to {unit_upper}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending command: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send command: {str(e)}")


@router.post("/entry/open", response_model=MessageResponse)
async def open_entry(
    bridge: SerialBridge = Depends(get_serial_bridge),
    current_user=Depends(get_current_active_user)
):
    """Open the ENTRY gate."""
    try:
        if "ENTRY" not in bridge.readers:
            raise HTTPException(status_code=503, detail="ENTRY gate not connected")
        await bridge.send_command("ENTRY", build_command(GateCommand.OPEN))
        logger.info(f"Open command sent to ENTRY by {current_user.username}")
        return MessageResponse(message="Open command sent to ENTRY")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error opening ENTRY gate: {e}")
        raise HTTPException(status_code=500, detail="Failed to open gate")


@router.post("/entry/close", response_model=MessageResponse)
async def close_entry(
    bridge: SerialBridge = Depends(get_serial_bridge),
    current_user=Depends(get_current_active_user)
):
    """Close the ENTRY gate."""
    try:
        if "ENTRY" not in bridge.readers:
            raise HTTPException(status_code=503, detail="ENTRY gate not connected")
        await bridge.send_command("ENTRY", build_command(GateCommand.CLOSE))
        logger.info(f"Close command sent to ENTRY by {current_user.username}")
        return MessageResponse(message="Close command sent to ENTRY")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing ENTRY gate: {e}")
        raise HTTPException(status_code=500, detail="Failed to close gate")


@router.post("/exit/open", response_model=MessageResponse)
async def open_exit(
    bridge: SerialBridge = Depends(get_serial_bridge),
    current_user=Depends(get_current_active_user)
):
    """Open the EXIT gate."""
    try:
        if "EXIT" not in bridge.readers:
            raise HTTPException(status_code=503, detail="EXIT gate not connected")
        await bridge.send_command("EXIT", build_command(GateCommand.OPEN))
        logger.info(f"Open command sent to EXIT by {current_user.username}")
        return MessageResponse(message="Open command sent to EXIT")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error opening EXIT gate: {e}")
        raise HTTPException(status_code=500, detail="Failed to open gate")


@router.post("/exit/close", response_model=MessageResponse)
async def close_exit(
    bridge: SerialBridge = Depends(get_serial_bridge),
    current_user=Depends(get_current_active_user)
):
    """Close the EXIT gate."""
    try:
        if "EXIT" not in bridge.readers:
            raise HTTPException(status_code=503, detail="EXIT gate not connected")
        await bridge.send_command("EXIT", build_command(GateCommand.CLOSE))
        logger.info(f"Close command sent to EXIT by {current_user.username}")
        return MessageResponse(message="Close command sent to EXIT")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing EXIT gate: {e}")
        raise HTTPException(status_code=500, detail="Failed to close gate")


# RFID Master Card Management via Serial Commands
@router.post("/rfid/add-master", response_model=MessageResponse)
async def add_master_card(
    unit: str = Query(..., description="Gate unit: ENTRY or EXIT"),
    bridge: SerialBridge = Depends(get_serial_bridge),
    current_user=Depends(require_admin),
):
    """Enter add-master mode (15s window) on specified unit."""
    try:
        unit_upper = unit.upper()
        if unit_upper not in ("ENTRY", "EXIT"):
            raise HTTPException(status_code=400, detail="Invalid unit")
        if unit_upper not in bridge.readers:
            raise HTTPException(status_code=503, detail=f"{unit_upper} not connected")
        
        await bridge.send_command(unit_upper, build_command(GateCommand.ADD_MASTER))
        logger.info(f"Add-master mode activated on {unit_upper} by {current_user.username}")
        return MessageResponse(message=f"Add-master mode activated on {unit_upper} for 15 seconds")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in add-master: {e}")
        raise HTTPException(status_code=500, detail="Failed to activate add-master mode")


@router.post("/rfid/del-master", response_model=MessageResponse)
async def del_master_card(
    unit: str = Query(..., description="Gate unit: ENTRY or EXIT"),
    bridge: SerialBridge = Depends(get_serial_bridge),
    current_user=Depends(require_admin),
):
    """Enter delete-master mode (15s window) on specified unit."""
    try:
        unit_upper = unit.upper()
        if unit_upper not in ("ENTRY", "EXIT"):
            raise HTTPException(status_code=400, detail="Invalid unit")
        if unit_upper not in bridge.readers:
            raise HTTPException(status_code=503, detail=f"{unit_upper} not connected")
        
        await bridge.send_command(unit_upper, build_command(GateCommand.DEL_MASTER))
        logger.info(f"Delete-master mode activated on {unit_upper} by {current_user.username}")
        return MessageResponse(message=f"Delete-master mode activated on {unit_upper} for 15 seconds")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in del-master: {e}")
        raise HTTPException(status_code=500, detail="Failed to activate delete-master mode")


@router.post("/rfid/list-masters", response_model=MessageResponse)
async def list_masters(
    unit: str = Query(..., description="Gate unit: ENTRY or EXIT"),
    bridge: SerialBridge = Depends(get_serial_bridge),
    current_user=Depends(get_current_active_user),
):
    """Request master card list from unit."""
    try:
        unit_upper = unit.upper()
        if unit_upper not in ("ENTRY", "EXIT"):
            raise HTTPException(status_code=400, detail="Invalid unit")
        if unit_upper not in bridge.readers:
            raise HTTPException(status_code=503, detail=f"{unit_upper} not connected")
        
        await bridge.send_command(unit_upper, build_command(GateCommand.LIST_MASTER))
        logger.info(f"Master list requested from {unit_upper} by {current_user.username}")
        return MessageResponse(message=f"Master list requested from {unit_upper}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error requesting master list: {e}")
        raise HTTPException(status_code=500, detail="Failed to request master list")


@router.post("/rfid/reset-all", response_model=MessageResponse)
async def reset_all_masters(
    unit: str = Query(..., description="Gate unit: ENTRY or EXIT"),
    bridge: SerialBridge = Depends(get_serial_bridge),
    current_user=Depends(require_admin),
):
    """Clear all master cards on unit."""
    try:
        unit_upper = unit.upper()
        if unit_upper not in ("ENTRY", "EXIT"):
            raise HTTPException(status_code=400, detail="Invalid unit")
        if unit_upper not in bridge.readers:
            raise HTTPException(status_code=503, detail=f"{unit_upper} not connected")
        
        await bridge.send_command(unit_upper, build_command(GateCommand.RESET_ALL))
        logger.info(f"Reset all masters on {unit_upper} by {current_user.username}")
        return MessageResponse(message=f"All master cards cleared on {unit_upper}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting masters: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset master cards")


@router.websocket("/ws")
async def gate_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time gate status."""
    client_id = "gate_monitor"
    await ws_manager.connect(websocket, client_id)
    logger.info(f"Gate WebSocket client connected")
    try:
        while True:
            # Keep connection alive and handle incoming messages
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                # Could handle ping/pong or commands here
                if data == "ping":
                    await ws_manager.send_personal_message({"type": "pong"}, websocket)
            except TimeoutError:
                # Send keepalive ping every 60 seconds
                try:
                    await ws_manager.send_personal_message({"type": "keepalive"}, websocket)
                except Exception as e:
                    logger.debug(f"Keepalive failed: {e}")
                    break
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, client_id)
        logger.info(f"Gate WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await ws_manager.disconnect(websocket, client_id)


import asyncio
