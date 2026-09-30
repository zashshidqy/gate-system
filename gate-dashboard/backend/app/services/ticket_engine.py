"""Ticket validation engine"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
import uuid

from ..models.ticket import TicketToken, TicketUsage, TicketType, ValidationMethod
from ..schemas.ticket import TicketValidationResponse, TicketTokenResponse


class ValidationResult:
    def __init__(
        self,
        allowed: bool,
        reason: Optional[str] = None,
        token: Optional[TicketToken] = None,
        usage_id: Optional[uuid.UUID] = None,
    ):
        self.allowed = allowed
        self.reason = reason
        self.token = token
        self.usage_id = usage_id


class TicketEngine:
    """Handles ticket validation logic."""

    def __init__(self, db: Session):
        self.db = db

    def validate(
        self,
        token_code: str,
        gate: str,
        method: ValidationMethod,
    ) -> ValidationResult:
        """Validate a ticket token for entry/exit."""
        now = datetime.utcnow()

        token = self.db.query(TicketToken).filter(TicketToken.code == token_code).first()
        if not token:
            return ValidationResult(allowed=False, reason="INVALID_TOKEN")

        if token.revoked:
            return ValidationResult(allowed=False, reason="REVOKED")

        if token.valid_from > now:
            return ValidationResult(allowed=False, reason="NOT_YET_VALID")

        if token.valid_until < now:
            return ValidationResult(allowed=False, reason="EXPIRED")

        if token.used_count >= token.max_uses:
            return ValidationResult(allowed=False, reason="EXHAUSTED")

        # For EXIT gate with SINGLE_ENTRY, check if entry was recorded
        if gate == "EXIT" and token.type == TicketType.SINGLE_ENTRY:
            entry_usage = (
                self.db.query(TicketUsage)
                .filter(
                    TicketUsage.token_id == token.id,
                    TicketUsage.direction == "IN",
                    TicketUsage.allowed.is_(True),
                )
                .first()
            )
            if not entry_usage:
                return ValidationResult(allowed=False, reason="NO_ENTRY_RECORD")

        # Record usage
        direction = "IN" if gate == "ENTRY" else "OUT"
        usage_id = uuid.uuid4()
        usage = TicketUsage(
            id=usage_id,
            token_id=token.id,
            gate_id=gate,
            direction=direction,
            timestamp=now,
            allowed=True,
            method=method,
        )

        token.used_count += 1
        self.db.add_all([usage, token])
        self.db.commit()
        self.db.refresh(token)

        return ValidationResult(
            allowed=True,
            token=token,
            usage_id=usage_id,
        )

    def validate_manual(self, token_code: str, gate: str) -> ValidationResult:
        """Manual validation (override) - used by guards."""
        return self.validate(token_code, gate, ValidationMethod.MANUAL)

    def get_token(self, token_code: str) -> Optional[TicketToken]:
        return self.db.query(TicketToken).filter(TicketToken.code == token_code).first()

    def get_token_by_id(self, token_id: uuid.UUID) -> Optional[TicketToken]:
        return self.db.query(TicketToken).filter(TicketToken.id == token_id).first()

    def list_usages(self, token_id: uuid.UUID, limit: int = 100) -> list[TicketUsage]:
        return (
            self.db.query(TicketUsage)
            .filter(TicketUsage.token_id == token_id)
            .order_by(TicketUsage.timestamp.desc())
            .limit(limit)
            .all()
        )