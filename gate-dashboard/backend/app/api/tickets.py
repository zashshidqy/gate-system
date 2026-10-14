"""Ticket token management API"""
import uuid
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from ..database import get_db
from ..models.ticket import TicketToken, TicketUsage, TicketType, ValidationMethod
from ..schemas.ticket import (
    TicketTokenCreate,
    TicketTokenUpdate,
    TicketTokenResponse,
    TicketTokenListResponse,
    TicketValidationRequest,
    TicketValidationResponse,
    TicketUsageResponse,
    QRCodeResponse,
)
from ..schemas.common import MessageResponse, PaginatedResponse
from ..services.ticket_engine import TicketEngine
from ..services.qr_generator import QRGenerator
from ..services.sensor_provider import SensorDataProvider
from ..dependencies import get_current_active_user, require_admin
from ..models.user import UserRole

router = APIRouter(prefix="/tickets", tags=["Tickets"])


def generate_token_code() -> str:
    """Generate a human-readable token code like GATE-7X9K2M."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # No confusing chars
    return "GATE-" + "".join(secrets.choice(alphabet) for _ in range(6))


@router.post("", response_model=TicketTokenResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    ticket_data: TicketTokenCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Create a new ticket token."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Validate date range
        if ticket_data.valid_until and ticket_data.valid_from:
            if ticket_data.valid_until < ticket_data.valid_from:
                raise HTTPException(status_code=400, detail="valid_until must be after valid_from")
        
        # Generate unique code
        for _ in range(10):
            code = generate_token_code()
            if not db.query(TicketToken).filter(TicketToken.code == code).first():
                break
        else:
            raise HTTPException(status_code=500, detail="Failed to generate unique code")

        now = datetime.utcnow()
        valid_from = ticket_data.valid_from or now

        # Build QR payload
        qr_payload = QRGenerator.build_payload(
            TicketTokenResponse(
                id=uuid.uuid4(),
                code=code,
                qr_payload="",
                type=ticket_data.type,
                valid_from=valid_from,
                valid_until=ticket_data.valid_until,
                max_uses=ticket_data.max_uses,
                used_count=0,
                issued_by=current_user.username,
                issued_at=now,
                revoked=False,
                metadata=ticket_data.metadata,
            )
        )

        token = TicketToken(
            code=code,
            qr_payload=qr_payload,
            type=ticket_data.type,
            valid_from=valid_from,
            valid_until=ticket_data.valid_until,
            max_uses=ticket_data.max_uses,
            issued_by=current_user.username,
            metadata_json=(
                __import__("json").dumps(ticket_data.metadata) if ticket_data.metadata else None
            ),
        )
        db.add(token)
        db.commit()
        db.refresh(token)

        # Broadcast event
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                from ..websocket.manager import ws_manager
                asyncio.create_task(
                    ws_manager.broadcast(
                        {
                            "type": "TICKET_CREATED",
                            "payload": TicketTokenResponse.model_validate(token).model_dump(),
                        }
                    )
                )
        except RuntimeError:
            pass

        return TicketTokenResponse.model_validate(token)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to create ticket")
        raise HTTPException(status_code=500, detail="Failed to create ticket") from e


@router.get("", response_model=PaginatedResponse[TicketTokenResponse])
def list_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[TicketType] = None,
    revoked: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """List ticket tokens with filters."""
    query = db.query(TicketToken)

    if type:
        query = query.filter(TicketToken.type == type)
    if revoked is not None:
        query = query.filter(TicketToken.revoked == revoked)
    if search:
        query = query.filter(
            or_(
                TicketToken.code.ilike(f"%{search}%"),
                TicketToken.issued_by.ilike(f"%{search}%"),
            )
        )

    total = query.count()
    tokens = (
        query.order_by(TicketToken.issued_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedResponse.create(
        items=[TicketTokenResponse.model_validate(t) for t in tokens],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{token_id}", response_model=TicketTokenResponse)
def get_ticket(
    token_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Get a single ticket token by ID."""
    token = db.query(TicketToken).filter(TicketToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return TicketTokenResponse.model_validate(token)


@router.get("/code/{token_code}", response_model=TicketTokenResponse)
def get_ticket_by_code(
    token_code: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Get a ticket token by code (for QR validation)."""
    token = db.query(TicketToken).filter(TicketToken.code == token_code).first()
    if not token:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return TicketTokenResponse.model_validate(token)


@router.patch("/{token_id}", response_model=TicketTokenResponse)
def update_ticket(
    token_id: uuid.UUID,
    update_data: TicketTokenUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Update a ticket token."""
    token = db.query(TicketToken).filter(TicketToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Ticket not found")

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        if field == "metadata" and value is not None:
            import json
            token.metadata_json = json.dumps(value)
        else:
            setattr(token, field, value)

    db.commit()
    db.refresh(token)

    # Broadcast event
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            from ..websocket.manager import ws_manager
            asyncio.create_task(
                ws_manager.broadcast(
                    {
                        "type": "TICKET_CREATED" if not update_data.revoked else "TICKET_REVOKED",
                        "payload": TicketTokenResponse.model_validate(token).model_dump(),
                    }
                )
            )
    except RuntimeError:
        pass

    return TicketTokenResponse.model_validate(token)


@router.delete("/{token_id}", response_model=MessageResponse)
def revoke_ticket(
    token_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Revoke (soft delete) a ticket token."""
    token = db.query(TicketToken).filter(TicketToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Ticket not found")

    token.revoked = True
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
                        "type": "TICKET_REVOKED",
                        "payload": TicketTokenResponse.model_validate(token).model_dump(),
                    }
                )
            )
    except RuntimeError:
        pass

    return MessageResponse(message="Ticket revoked")


@router.post("/validate", response_model=TicketValidationResponse)
def validate_ticket(
    request: TicketValidationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Validate a ticket token for entry/exit."""
    # Get sensor data from gate if available
    sensor_data = None
    try:
        from ..api.gates import serial_bridge
        if serial_bridge:
            sensor_provider = SensorDataProvider(serial_bridge)
            sensor_data = sensor_provider.get_sensor_data(request.gate)
    except Exception as e:
        logger.warning(f"Failed to get sensor data: {e}")
    
    engine = TicketEngine(db)
    result = engine.validate(
        request.token_code, 
        request.gate, 
        ValidationMethod(request.method),
        sensor_data=sensor_data
    )

    return TicketValidationResponse(
        allowed=result.allowed,
        reason=result.reason,
        token=TicketTokenResponse.model_validate(result.token) if result.token else None,
        usage_id=result.usage_id,
    )


@router.post("/validate-manual", response_model=TicketValidationResponse)
def validate_ticket_manual(
    token_code: str,
    gate: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Manual validation by guard (override)."""
    # Get sensor data from gate if available
    sensor_data = None
    try:
        from ..api.gates import serial_bridge
        if serial_bridge:
            sensor_provider = SensorDataProvider(serial_bridge)
            sensor_data = sensor_provider.get_sensor_data(gate)
    except Exception as e:
        logger.warning(f"Failed to get sensor data: {e}")
    
    engine = TicketEngine(db)
    result = engine.validate_manual(token_code, gate, sensor_data=sensor_data)

    return TicketValidationResponse(
        allowed=result.allowed,
        reason=result.reason,
        token=TicketTokenResponse.model_validate(result.token) if result.token else None,
        usage_id=result.usage_id,
    )


@router.get("/{token_id}/qr", response_model=QRCodeResponse)
def get_ticket_qr(
    token_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Get QR code for a ticket token."""
    token = db.query(TicketToken).filter(TicketToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Ticket not found")

    qr_payload, qr_base64 = QRGenerator.generate_for_token(TicketTokenResponse.model_validate(token))
    return QRCodeResponse(
        token_code=token.code,
        qr_data=qr_base64,
        qr_payload=qr_payload,
    )


@router.get("/{token_id}/usages", response_model=PaginatedResponse[TicketUsageResponse])
def get_ticket_usages(
    token_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Get usage history for a ticket token."""
    engine = TicketEngine(db)
    usages = engine.list_usages(token_id, limit=page_size * page)
    total = db.query(TicketUsage).filter(TicketUsage.token_id == token_id).count()

    return PaginatedResponse.create(
        items=[TicketUsageResponse.model_validate(u) for u in usages],
        total=total,
        page=page,
        page_size=page_size,
    )