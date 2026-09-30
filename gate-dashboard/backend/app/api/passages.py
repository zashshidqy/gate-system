"""Passage history API"""
import csv
import io
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from ..database import get_db
from ..models.passage import Passage
from ..schemas.passage import PassageResponse, PassageListResponse, PassageFilter
from ..schemas.common import PaginatedResponse
from ..dependencies import get_current_active_user

router = APIRouter(prefix="/passages", tags=["Passages"])


@router.get("", response_model=PaginatedResponse[PassageResponse])
def list_passages(
    filter_params: PassageFilter = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """List passage records with filters."""
    query = db.query(Passage)

    if filter_params.direction:
        query = query.filter(Passage.direction == filter_params.direction)
    if filter_params.method:
        query = query.filter(Passage.method == filter_params.method)
    if filter_params.allowed is not None:
        query = query.filter(Passage.allowed == filter_params.allowed)
    if filter_params.date_from:
        query = query.filter(Passage.ts >= filter_params.date_from)
    if filter_params.date_to:
        query = query.filter(Passage.ts <= filter_params.date_to)
    if filter_params.search:
        search = f"%{filter_params.search}%"
        query = query.filter(
            or_(
                Passage.uid.ilike(search),
                Passage.plate.ilike(search),
                Passage.note.ilike(search),
            )
        )

    total = query.count()
    passages = (
        query.order_by(Passage.ts.desc())
        .offset((filter_params.page - 1) * filter_params.page_size)
        .limit(filter_params.page_size)
        .all()
    )

    return PaginatedResponse.create(
        items=[PassageResponse.model_validate(p) for p in passages],
        total=total,
        page=filter_params.page,
        page_size=filter_params.page_size,
    )


@router.get("/stats/summary")
def get_passage_stats(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Get summary statistics."""
    query = db.query(Passage)
    if date_from:
        query = query.filter(Passage.ts >= date_from)
    if date_to:
        query = query.filter(Passage.ts <= date_to)

    total = query.count()
    allowed = query.filter(Passage.allowed.is_(True)).count()
    denied = query.filter(Passage.allowed.is_(False)).count()

    by_direction = dict(
        query.with_entities(Passage.direction, func.count(Passage.id))
        .group_by(Passage.direction)
        .all()
    )
    by_method = dict(
        query.with_entities(Passage.method, func.count(Passage.id))
        .group_by(Passage.method)
        .all()
    )

    return {
        "total": total,
        "allowed": allowed,
        "denied": denied,
        "by_direction": by_direction,
        "by_method": by_method,
    }


@router.get("/export/csv")
def export_passages_csv(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    direction: Optional[str] = None,
    method: Optional[str] = None,
    allowed: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Export passages as CSV."""
    query = db.query(Passage).order_by(Passage.ts.desc())

    if date_from:
        query = query.filter(Passage.ts >= date_from)
    if date_to:
        query = query.filter(Passage.ts <= date_to)
    if direction:
        query = query.filter(Passage.direction == direction)
    if method:
        query = query.filter(Passage.method == method)
    if allowed is not None:
        query = query.filter(Passage.allowed == allowed)

    passages = query.limit(10000).all()  # Limit for performance

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Timestamp", "Direction", "Method", "UID", "Plate", "Allowed", "Image Path", "Note"])

    for p in passages:
        writer.writerow([
            p.id,
            p.ts.isoformat(),
            p.direction,
            p.method,
            p.uid or "",
            p.plate or "",
            "Yes" if p.allowed else "No",
            p.image_path or "",
            p.note or "",
        ])

    output.seek(0)
    filename = f"passages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )