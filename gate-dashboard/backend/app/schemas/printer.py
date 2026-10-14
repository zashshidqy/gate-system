"""Printer API schemas"""

from pydantic import BaseModel


class PrinterStatusResponse(BaseModel):
    connected: bool
    name: str
    driver: str
    uri: str
    usb_detected: bool
    cups_status: str


class PrinterTestResponse(BaseModel):
    success: bool
    message: str
    request_id: str | None = None


class GateTicketTestRequest(BaseModel):
    direction: str = "ENTRY"  # ENTRY or EXIT
    ticket_type: str = "SINGLE_ENTRY"
    ticket_code: str = "TKT-20261012-ABCD1234"
    plate: str | None = "B 1234 ABC"
    rfid_uid: str | None = "A1 B2 C3 D4"
    method: str = "QR_SCAN"
    gate_name: str = "Gerbang Utama"
    operator: str = "Operator 1"
    company_name: str = "PT Smart Gate Solutions"
    company_website: str = "https://smartgate.co.id"
    show_qr: bool = True
    # Exit-specific fields (only used when direction=EXIT)
    entry_time: str | None = None  # ISO format: "2026-10-12T10:30:00"
    exit_time: str | None = None   # ISO format: "2026-10-12T12:45:00"
    duration_hours: float | None = None  # 2.25 hours
    duration_text: str | None = None  # "2 jam 15 menit"
    parking_fee: int | None = None  # 15000 (in rupiah)
    payment_method: str | None = None  # "CASH", "QRIS", "CARD"


class ExitScanRequest(BaseModel):
    """Request to simulate scanning an entry ticket barcode at exit"""
    ticket_code: str = "TKT-20261012-ABCD1234"
    plate: str | None = "B 1234 ABC"
    rfid_uid: str | None = None
    ticket_type: str = "SINGLE_ENTRY"
    entry_time: str | None = None  # ISO format
    gate_name: str = "Gerbang Utama"


class ExitScanResponse(BaseModel):
    """Comprehensive information displayed when entry ticket is scanned at exit"""
    ticket_code: str
    ticket_type: str
    plate: str | None
    rfid_uid: str | None
    entry_time: str | None
    exit_time: str
    duration_hours: float
    duration_text: str
    parking_fee: int
    payment_method: str
    gate_name: str
    company_name: str
    message: str
