"""Dashboard aggregated data API"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ..database import get_db
from ..models.passage import Passage
from ..models.ticket import TicketToken, TicketUsage, TicketType
from ..models.rfid_card import AuthorizedCard
from ..models.user import User, UserRole
from ..dependencies import get_current_active_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview")
def get_overview(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Get dashboard overview statistics."""
    since = datetime.utcnow() - timedelta(hours=hours)

    # Passage stats
    passage_query = db.query(Passage).filter(Passage.ts >= since)
    total_passages = passage_query.count()
    allowed_passages = passage_query.filter(Passage.allowed.is_(True)).count()

    # By direction
    by_direction = dict(
        passage_query.with_entities(Passage.direction, func.count(Passage.id))
        .group_by(Passage.direction)
        .all()
    )

    # By method
    by_method = dict(
        passage_query.with_entities(Passage.method, func.count(Passage.id))
        .group_by(Passage.method)
        .all()
    )

    # Hourly breakdown
    hourly = (
        passage_query.with_entities(
            func.strftime("%Y-%m-%d %H:00", Passage.ts).label("hour"),
            func.count(Passage.id).label("count"),
        )
        .group_by("hour")
        .order_by("hour")
        .all()
    )
    hourly_data = [{"hour": h, "count": c} for h, c in hourly]

    # Ticket stats
    active_tickets = db.query(TicketToken).filter(
        TicketToken.revoked.is_(False),
        TicketToken.valid_until >= datetime.utcnow(),
    ).count()

    tickets_by_type = dict(
        db.query(TicketToken.type, func.count(TicketToken.id))
        .filter(TicketToken.revoked.is_(False))
        .group_by(TicketToken.type)
        .all()
    )

    # RFID stats
    active_cards = db.query(AuthorizedCard).filter(AuthorizedCard.active.is_(True)).count()

    # Recent passages (last 10)
    recent = (
        db.query(Passage)
        .order_by(Passage.ts.desc())
        .limit(10)
        .all()
    )

    return {
        "period_hours": hours,
        "passages": {
            "total": total_passages,
            "allowed": allowed_passages,
            "denied": total_passages - allowed_passages,
            "by_direction": by_direction,
            "by_method": by_method,
            "hourly": hourly_data,
        },
        "tickets": {
            "active": active_tickets,
            "by_type": tickets_by_type,
        },
        "rfid": {
            "active_cards": active_cards,
        },
        "recent_passages": [
            {
                "id": p.id,
                "ts": p.ts.isoformat(),
                "direction": p.direction,
                "method": p.method,
                "uid": p.uid,
                "plate": p.plate,
                "allowed": p.allowed,
            }
            for p in recent
        ],
    }


@router.get("/tickets/expiring")
def get_expiring_tickets(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Get tickets expiring within specified days."""
    until = datetime.utcnow() + timedelta(days=days)
    tickets = (
        db.query(TicketToken)
        .filter(
            TicketToken.revoked.is_(False),
            TicketToken.valid_until <= until,
            TicketToken.valid_until >= datetime.utcnow(),
        )
        .order_by(TicketToken.valid_until.asc())
        .limit(50)
        .all()
    )

    return [
        {
            "id": str(t.id),
            "code": t.code,
            "type": t.type,
            "valid_until": t.valid_until.isoformat(),
            "used_count": t.used_count,
            "max_uses": t.max_uses,
        }
        for t in tickets
    ]


@router.get("/rfid/recent-additions")
def get_recent_rfid_additions(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Get recently added RFID cards."""
    cards = (
        db.query(AuthorizedCard)
        .order_by(AuthorizedCard.added_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": str(c.id),
            "uid": c.uid,
            "label": c.label,
            "added_by": c.added_by,
            "added_at": c.added_at.isoformat(),
            "active": c.active,
        }
        for c in cards
    ]