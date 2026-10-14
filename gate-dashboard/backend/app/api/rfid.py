"""RFID authorized cards management API"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db
from ..models.rfid_card import AuthorizedCard
from ..schemas.rfid import (
    AuthorizedCardCreate,
    AuthorizedCardResponse,
    AuthorizedCardListResponse,
)
from ..schemas.common import MessageResponse, PaginatedResponse
from ..dependencies import get_current_active_user, require_admin
from ..services.serial_bridge import SerialBridge
from ..api.gates import get_serial_bridge

router = APIRouter(prefix="/rfid", tags=["RFID Cards"])


@router.post("", response_model=AuthorizedCardResponse, status_code=status.HTTP_201_CREATED)
def add_authorized_card(
    card_data: AuthorizedCardCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Add an authorized RFID card to database."""
    # Normalize UID to uppercase
    uid = card_data.uid.upper()

    if db.query(AuthorizedCard).filter(AuthorizedCard.uid == uid).first():
        raise HTTPException(status_code=400, detail="Card already registered")

    card = AuthorizedCard(
        uid=uid,
        label=card_data.label,
        added_by=current_user.username,
        note=card_data.note,
    )
    db.add(card)
    db.commit()
    db.refresh(card)

    # Broadcast event
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            from ..websocket.manager import ws_manager
            asyncio.create_task(
                ws_manager.broadcast(
                    {
                        "type": "CARD_ADDED",
                        "payload": AuthorizedCardResponse.model_validate(card).model_dump(),
                    }
                )
            )
    except RuntimeError:
        pass

    return AuthorizedCardResponse.model_validate(card)


@router.get("", response_model=PaginatedResponse[AuthorizedCardResponse])
def list_authorized_cards(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    active: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """List authorized RFID cards."""
    query = db.query(AuthorizedCard)

    if active is not None:
        query = query.filter(AuthorizedCard.active == active)
    if search:
        query = query.filter(
            or_(
                AuthorizedCard.uid.ilike(f"%{search}%"),
                AuthorizedCard.label.ilike(f"%{search}%"),
                AuthorizedCard.added_by.ilike(f"%{search}%"),
            )
        )

    total = query.count()
    cards = (
        query.order_by(AuthorizedCard.added_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedResponse.create(
        items=[AuthorizedCardResponse.model_validate(c) for c in cards],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{card_id}", response_model=AuthorizedCardResponse)
def get_authorized_card(
    card_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Get an authorized card by ID."""
    card = db.query(AuthorizedCard).filter(AuthorizedCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return AuthorizedCardResponse.model_validate(card)


@router.patch("/{card_id}", response_model=AuthorizedCardResponse)
def update_authorized_card(
    card_id: uuid.UUID,
    active: Optional[bool] = None,
    label: Optional[str] = None,
    note: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Update an authorized card."""
    card = db.query(AuthorizedCard).filter(AuthorizedCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    if active is not None:
        card.active = active
    if label is not None:
        card.label = label
    if note is not None:
        card.note = note

    db.commit()
    db.refresh(card)
    return AuthorizedCardResponse.model_validate(card)


@router.delete("/{card_id}", response_model=MessageResponse)
def delete_authorized_card(
    card_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Delete an authorized card from database."""
    card = db.query(AuthorizedCard).filter(AuthorizedCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    uid = card.uid
    db.delete(card)
    db.commit()

    # Broadcast event
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            from ..websocket.manager import ws_manager
            asyncio.create_task(
                ws_manager.broadcast(
                    {
                        "type": "CARD_REMOVED",
                        "payload": {"uid": uid},
                    }
                )
            )
    except RuntimeError:
        pass

    return MessageResponse(message="Card removed from database")


# Hardware sync endpoints
@router.post("/sync-to-hardware/{unit}", response_model=MessageResponse)
async def sync_cards_to_hardware(
    unit: str,
    bridge: SerialBridge = Depends(get_serial_bridge),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """
    Sync all active authorized cards to ESP32 hardware.
    This sends ADD_MASTER commands for each card.
    """
    unit_upper = unit.upper()
    if unit_upper not in ("ENTRY", "EXIT"):
        raise HTTPException(status_code=400, detail="Invalid unit. Use ENTRY or EXIT")

    cards = db.query(AuthorizedCard).filter(AuthorizedCard.active.is_(True)).all()
    if not cards:
        return MessageResponse(message="No active cards to sync")

    # For each card, we'd need to send ADD_MASTER and then the card UID
    # This is a simplified version - actual implementation depends on hardware protocol
    # The ESP32 expects: send 'A' command, then tap card within 15s
    # For remote sync, we'd need a different protocol or manual process
    
    return MessageResponse(
        message=f"Found {len(cards)} active cards. Use hardware buttons to add them manually, "
        f"or implement remote provisioning protocol."
    )


@router.get("/hardware/status/{unit}", response_model=MessageResponse)
async def get_hardware_master_list(
    unit: str,
    bridge: SerialBridge = Depends(get_serial_bridge),
    current_user=Depends(get_current_active_user),
):
    """Request master card list from hardware."""
    unit_upper = unit.upper()
    if unit_upper not in ("ENTRY", "EXIT"):
        raise HTTPException(status_code=400, detail="Invalid unit. Use ENTRY or EXIT")

    from ..services.protocol import build_command, GateCommand

    await bridge.send_command(unit_upper, build_command(GateCommand.LIST_MASTER))
    return MessageResponse(message=f"Master list requested from {unit_upper}. Check logs for response.")


@router.post("/register-tap/{unit}", response_model=MessageResponse)
async def register_card_by_tap(
    unit: str,
    bridge: SerialBridge = Depends(get_serial_bridge),
    current_user=Depends(get_current_active_user),
):
    """
    Enter RFID add-master mode on the specified unit.

    The ESP32 will listen for a card tap for 15 seconds. When a card is tapped,
    the backend detects it via serial and broadcasts a CARD_TAPPED WebSocket event
    with the tapped card's UID.
    """
    unit_upper = unit.upper()
    if unit_upper not in ("ENTRY", "EXIT"):
        raise HTTPException(status_code=400, detail="Invalid unit. Use ENTRY or EXIT")

    if not bridge.is_connected(unit_upper):
        raise HTTPException(status_code=503, detail=f"{unit_upper} not connected")

    from ..services.protocol import build_command, GateCommand

    await bridge.send_command(unit_upper, build_command(GateCommand.ADD_MASTER))
    return MessageResponse(
        message=f"Add-master mode activated on {unit_upper} for 15 seconds. Tap a card now."
    )