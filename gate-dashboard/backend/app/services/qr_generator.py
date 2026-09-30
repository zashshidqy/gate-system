"""QR code generation for ticket tokens"""
import json
import base64
import qrcode
from io import BytesIO
from datetime import datetime
from typing import Dict, Any
from ..schemas.ticket import TicketTokenResponse


class QRGenerator:
    """Generates QR codes for ticket tokens."""

    # QR version: L (7% error correction) - good balance for printing
    QR_VERSION = 1
    QR_ERROR_CORRECTION = qrcode.constants.ERROR_CORRECT_L
    QR_BOX_SIZE = 10
    QR_BORDER = 4

    @staticmethod
    def build_payload(token: TicketTokenResponse) -> str:
        """Build JSON payload for QR code."""
        payload: Dict[str, Any] = {
            "v": 1,  # protocol version
            "token": token.code,
            "type": token.type,
            "exp": int(token.valid_until.timestamp()),
            "max": token.max_uses,
        }
        return json.dumps(payload, separators=(",", ":"))

    @classmethod
    def generate_qr_base64(cls, payload: str) -> str:
        """Generate QR code as base64 encoded PNG."""
        qr = qrcode.QRCode(
            version=cls.QR_VERSION,
            error_correction=cls.QR_ERROR_CORRECTION,
            box_size=cls.QR_BOX_SIZE,
            border=cls.QR_BORDER,
        )
        qr.add_data(payload)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("ascii")

    @classmethod
    def generate_for_token(cls, token: TicketTokenResponse) -> tuple[str, str]:
        """Generate QR payload and base64 image for a token."""
        payload = cls.build_payload(token)
        qr_base64 = cls.generate_qr_base64(payload)
        return payload, qr_base64