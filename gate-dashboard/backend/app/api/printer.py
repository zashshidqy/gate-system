"""Printer control API for POS80 / iware IW 8220 thermal printer"""
import logging
import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_current_active_user
from ..models.user import User
from ..schemas.printer import (
    ExitScanRequest,
    ExitScanResponse,
    GateTicketTestRequest,
    PrinterStatusResponse,
    PrinterTestResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/printer", tags=["Printer"])

# CUPS printer name
PRINTER_NAME = "POS80"
# Path to store generated test receipt
TEST_RECEIPT_PATH = Path("/tmp/gate_test_receipt.bin")
# Path for gate ticket test receipt
GATE_TICKET_RECEIPT_PATH = Path("/tmp/gate_ticket_receipt.bin")

# Dependency for current user
current_user_dep = Depends(get_current_active_user)


def generate_escpos_test_receipt() -> bytes:
    """Generate ESC/POS binary test receipt for POS80 thermal printer."""
    esc_init = b'\x1b\x40'              # ESC @ - Initialize printer
    esc_align_c = b'\x1b\x61\x01'       # ESC a 1 - Center align
    esc_align_l = b'\x1b\x61\x00'       # ESC a 0 - Left align
    esc_bold_on = b'\x1b\x45\x01'       # ESC E 1 - Bold on
    esc_bold_off = b'\x1b\x45\x00'      # ESC E 0 - Bold off
    esc_feed = b'\x1b\x64\x03'          # ESC d 3 - Feed 3 lines
    cut_partial = b'\x1d\x56\x00'       # GS V 0 - Partial cut

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    receipt = (
        esc_init +
        esc_align_c +
        esc_bold_on +
        b'================================\n' +
        b'      TEST RECEIPT\n' +
        b'      iware IW 8220 / POS80\n' +
        b'================================\n' +
        esc_bold_off +
        esc_align_l +
        f'Date: {now}\n'.encode() +
        b'Driver: CUPS Raw (ESC/POS)\n' +
        b'Connection: USB (0416:5011)\n' +
        b'================================\n' +
        b'Test print successful!\n' +
        esc_feed +
        cut_partial
    )
    return receipt


def generate_escpos_barcode(data: str, height: int = 50) -> bytes:
    """
    Generate ESC/POS Code 128 barcode as a raster bitmap using Pillow.
    Uses the same GS v 0 raster approach as the QR code.
    """
    from PIL import Image, ImageDraw

    # Code 128 encoding tables
    # Each pattern is a sequence of bar/space widths (in modules), starting with bar
    # There are 107 patterns (0-106), each 6 elements wide except stop (7)
    CODE128_PATTERNS = [
        [2, 1, 2, 2, 2, 2], [2, 2, 2, 1, 2, 2], [2, 2, 2, 2, 2, 1],
        [1, 2, 1, 2, 2, 3], [1, 2, 1, 3, 2, 2], [1, 3, 1, 2, 2, 2],
        [1, 2, 2, 2, 1, 3], [1, 2, 2, 3, 1, 2], [1, 3, 2, 2, 1, 2],
        [2, 2, 1, 2, 1, 3], [2, 2, 1, 3, 1, 2], [2, 3, 1, 2, 1, 2],
        [1, 1, 2, 2, 3, 2], [1, 2, 2, 1, 3, 2], [1, 2, 2, 2, 3, 1],
        [1, 1, 3, 2, 2, 2], [1, 2, 3, 1, 2, 2], [1, 2, 3, 2, 2, 1],
        [2, 2, 3, 2, 1, 1], [2, 2, 1, 1, 3, 2], [2, 2, 1, 2, 3, 1],
        [2, 1, 3, 2, 1, 2], [2, 2, 3, 1, 1, 2], [3, 1, 2, 1, 3, 1],
        [3, 1, 1, 2, 2, 2], [3, 2, 1, 1, 2, 2], [3, 2, 1, 2, 2, 1],
        [3, 1, 2, 2, 1, 2], [3, 2, 2, 1, 1, 2], [3, 2, 2, 2, 1, 1],
        [2, 1, 2, 1, 2, 3], [2, 1, 2, 3, 2, 1], [2, 3, 2, 1, 2, 1],
        [1, 1, 1, 3, 2, 3], [1, 3, 1, 1, 2, 3], [1, 3, 1, 3, 2, 1],
        [1, 1, 2, 3, 1, 3], [1, 1, 2, 3, 3, 1], [1, 3, 2, 1, 1, 3],
        [1, 3, 2, 3, 1, 1], [1, 1, 3, 1, 2, 3], [1, 1, 3, 3, 2, 1],
        [1, 3, 3, 1, 1, 3], [3, 1, 3, 1, 1, 2], [2, 1, 1, 3, 2, 3],
        [2, 3, 1, 1, 3, 2], [2, 1, 3, 1, 2, 3], [2, 1, 3, 3, 2, 1],
        [2, 1, 3, 2, 3, 1], [2, 3, 3, 1, 1, 2], [3, 1, 2, 1, 3, 1],
        [3, 1, 2, 3, 1, 1], [3, 3, 2, 1, 1, 1], [3, 1, 3, 1, 2, 1],
        [3, 1, 3, 2, 1, 1], [3, 2, 3, 1, 1, 1], [3, 2, 1, 1, 3, 1],
        [3, 2, 1, 3, 1, 1], [3, 2, 1, 1, 1, 3], [3, 1, 1, 2, 1, 3],
        [3, 1, 1, 3, 2, 1], [3, 1, 1, 3, 1, 2], [3, 1, 2, 1, 1, 3],
        [3, 1, 2, 3, 1, 1], [3, 1, 2, 1, 3, 1], [3, 2, 2, 1, 1, 3],
        [3, 2, 2, 3, 1, 1], [3, 2, 2, 1, 3, 1], [3, 1, 1, 1, 2, 3],
        [3, 1, 1, 3, 2, 1], [3, 2, 1, 1, 2, 3], [3, 2, 1, 3, 2, 1],
        [2, 2, 1, 1, 2, 2], [2, 2, 1, 2, 2, 1], [2, 2, 2, 1, 2, 1],
        [2, 2, 2, 2, 1, 1], [2, 1, 2, 2, 1, 2], [2, 1, 2, 1, 2, 2],
        [2, 1, 2, 2, 2, 1], [2, 2, 1, 2, 1, 2], [2, 2, 2, 2, 1, 1],
        [2, 2, 1, 1, 2, 2], [2, 2, 2, 1, 1, 2], [2, 2, 2, 2, 1, 1],
        [2, 1, 1, 2, 2, 2], [2, 1, 2, 1, 2, 2], [2, 1, 2, 2, 2, 1],
        [2, 2, 1, 1, 2, 2], [2, 2, 1, 2, 2, 1], [2, 2, 2, 1, 1, 2],
        [2, 2, 2, 2, 1, 1], [2, 1, 1, 2, 2, 2], [2, 1, 2, 1, 2, 2],
        [2, 1, 2, 2, 2, 1], [2, 2, 1, 1, 2, 2], [2, 2, 1, 2, 2, 1],
        [2, 2, 2, 1, 1, 2], [2, 2, 2, 2, 1, 1], [2, 1, 1, 2, 2, 2],
        [2, 1, 2, 1, 2, 2], [2, 1, 2, 2, 2, 1], [2, 2, 1, 1, 2, 2],
        [2, 2, 1, 2, 2, 1], [2, 2, 2, 1, 1, 2], [2, 2, 2, 2, 1, 1],
        [2, 1, 1, 2, 2, 2], [2, 1, 2, 1, 2, 2], [2, 1, 2, 2, 2, 1],
        [2, 2, 1, 1, 2, 2], [2, 2, 1, 2, 2, 1], [2, 2, 2, 1, 1, 2],
        [2, 2, 2, 2, 1, 1],
    ]
    # Stop pattern has 7 elements
    STOP_PATTERN = [2, 1, 1, 1, 2, 3, 1]

    # Code 128 Mode B: ASCII 32-127 map to values 0-95
    def char_to_value(c: str) -> int:
        v = ord(c) - 32
        if 0 <= v <= 95:
            return v
        return 0  # fallback for unsupported chars

    # Build the barcode pattern sequence
    values = [104]  # Start B
    for c in data:
        values.append(char_to_value(c))

    # Calculate checksum
    checksum = values[0]  # Start code value
    for i, v in enumerate(values[1:], 1):
        checksum += v * i
    checksum %= 103
    values.append(checksum)
    values.append(106)  # Stop

    # Convert values to bar/space widths
    widths = []
    for v in values:
        if v == 106:
            widths.extend(STOP_PATTERN)
        else:
            widths.extend(CODE128_PATTERNS[v])

    # Render barcode to image
    module_width = 2  # pixels per module
    quiet_zone = 10   # modules of quiet zone on each side

    total_modules = sum(widths) + (quiet_zone * 2)
    img_width = total_modules * module_width
    img_height = height

    img = Image.new('1', (img_width, img_height), 1)  # 1-bit, white background
    draw = ImageDraw.Draw(img)

    # Draw bars
    x = quiet_zone * module_width
    is_bar = True  # starts with bar
    for w in widths:
        if is_bar:
            bar_width = w * module_width
            draw.rectangle([x, 0, x + bar_width - 1, img_height - 1], fill=0)
            x += bar_width
        else:
            x += w * module_width
        is_bar = not is_bar

    # Convert to ESC/POS raster format (GS v 0)
    receipt = b'\x1b\x61\x01'  # Center align
    receipt += b'\x1d\x76\x30\x00'  # GS v 0 0 (normal mode)

    width_bytes = (img_width + 7) // 8
    receipt += bytes([width_bytes & 0xFF, (width_bytes >> 8) & 0xFF])
    receipt += bytes([img_height & 0xFF, (img_height >> 8) & 0xFF])

    pixels = list(img.getdata())
    for y in range(img_height):
        for x_byte in range(0, img_width, 8):
            byte_val = 0
            for bit in range(8):
                px = x_byte + bit
                if px < img_width:
                    if pixels[y * img_width + px] == 0:  # Black pixel
                        byte_val |= (1 << (7 - bit))
            receipt += bytes([byte_val])

    # Print human-readable text below barcode
    receipt += b'\x1b\x61\x01'  # Center align
    receipt += f'{data}\n'.encode('ascii')
    receipt += b'\x1b\x61\x00'  # Left align

    return receipt


def generate_gate_ticket_receipt(req: GateTicketTestRequest) -> bytes:
    """Generate ESC/POS binary gate ticket receipt (realistic format with QR)."""

    import qrcode

    esc_init = b'\x1b\x40'              # ESC @ - Initialize printer
    esc_align_c = b'\x1b\x61\x01'       # ESC a 1 - Center align
    esc_align_l = b'\x1b\x61\x00'       # ESC a 0 - Left align
    esc_align_r = b'\x1b\x61\x02'       # ESC a 2 - Right align
    esc_bold_on = b'\x1b\x45\x01'       # ESC E 1 - Bold on
    esc_bold_off = b'\x1b\x45\x00'      # ESC E 0 - Bold off
    esc_double_h_on = b'\x1b\x21\x10'   # ESC ! 16 - Double height
    esc_double_h_off = b'\x1b\x21\x00'  # ESC ! 0 - Normal
    esc_feed = b'\x1b\x64\x03'          # ESC d 3 - Feed 3 lines
    cut_partial = b'\x1d\x56\x00'       # GS V 0 - Partial cut

    now = datetime.now()
    date_str = now.strftime("%d/%m/%Y")
    time_str = now.strftime("%H:%M:%S")
    datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")

    direction_label = "MASUK" if req.direction == "ENTRY" else "KELUAR"
    direction_icon = ">>>" if req.direction == "ENTRY" else "<<<"
    method_labels = {
        "QR_SCAN": "Scan QR Code",
        "RFID_LINK": "Kartu RFID",
        "MANUAL": "Manual",
        "ANPR": "ANPR / Plat Nomor",
    }
    method_label = method_labels.get(req.method, req.method)
    ticket_type_labels = {
        "SINGLE_ENTRY": "Sekali Masuk",
        "MULTI_DAY": "Multi Hari",
        "VIP": "VIP",
        "STAFF": "Staf",
    }
    ticket_type_label = ticket_type_labels.get(req.ticket_type, req.ticket_type)

    # Build receipt header
    receipt = (
        esc_init +
        esc_align_c +
        esc_bold_on +
        esc_double_h_on +
        f'{req.company_name}\n'.encode() +
        esc_double_h_off +
        esc_bold_off +
        b'================================\n' +
        esc_bold_on +
        f'{direction_icon} TIKET {direction_label} {direction_icon}\n'.encode() +
        esc_bold_off +
        b'================================\n' +
        esc_align_l +
        b'\n'
    )

    if req.direction == "ENTRY":
        # ENTRY TICKET - Include scannable CODE 128 BARCODE with ticket code
        receipt += (
            esc_bold_on +
            f'KODE TIKET: {req.ticket_code}\n'.encode() +
            esc_bold_off +
            b'\n' +
            f'Tanggal    : {date_str}\n'.encode() +
            f'Waktu Masuk: {time_str}\n'.encode() +
            b'--------------------------------\n' +
            f'Tipe Tiket : {ticket_type_label}\n'.encode() +
            f'Metode     : {method_label}\n'.encode()
        )

        if req.plate:
            receipt += f'Plat Nomor : {req.plate}\n'.encode()
        if req.rfid_uid:
            receipt += f'RFID UID   : {req.rfid_uid}\n'.encode()

        receipt += (
            b'--------------------------------\n' +
            f'Gerbang    : {req.gate_name}\n'.encode() +
            f'Petugas    : {req.operator}\n'.encode() +
            b'--------------------------------\n'
        )

        # Add CODE 128 BARCODE with ticket code for exit gate scanner
        if req.show_qr:
            try:
                receipt += esc_align_c
                receipt += b'\n'
                receipt += generate_escpos_barcode(req.ticket_code)
                receipt += b'\n'
                receipt += b'SCAN BARCODE SAAT KELUAR\n'
                receipt += b'================================\n'
                receipt += esc_align_l
            except Exception:
                receipt += esc_align_c
                receipt += b'TUNJUKKAN TIKET SAAT KELUAR\n'
                receipt += esc_align_l

        receipt += (
            b'--------------------------------\n' +
            esc_align_c +
            b'Simpan tiket ini!\n' +
            b'Tunjukkan saat keluar\n'
        )

    else:  # EXIT
        # EXIT RECEIPT - Clean, professional billing layout
        receipt += (
            esc_bold_on +
            f'KODE TIKET: {req.ticket_code}\n'.encode() +
            esc_bold_off +
            b'\n'
        )

        if req.plate:
            receipt += f'Plat Nomor : {req.plate}\n'.encode()
        if req.rfid_uid:
            receipt += f'RFID UID   : {req.rfid_uid}\n'.encode()

        # Billing section with clean separators
        receipt += b'--------------------------------\n'
        receipt += esc_align_c
        receipt += esc_bold_on
        receipt += b'      RINCIAN PARKIR\n'
        receipt += esc_bold_off
        receipt += esc_align_l
        receipt += b'--------------------------------\n'

        if req.entry_time:
            receipt += f'Waktu Masuk  : {req.entry_time[11:19]}\n'.encode()
        if req.exit_time:
            receipt += f'Waktu Keluar : {req.exit_time[11:19]}\n'.encode()

        if req.duration_text:
            receipt += f'Durasi       : {req.duration_text}\n'.encode()

        receipt += b'--------------------------------\n'

        # Total - clean single-line, not oversized
        if req.parking_fee is not None:
            receipt += esc_align_r
            receipt += esc_bold_on
            receipt += f'TOTAL  Rp {req.parking_fee:,}\n'.encode()
            receipt += esc_bold_off
            receipt += esc_align_l
            receipt += b'--------------------------------\n'

        if req.payment_method:
            payment_labels = {
                "CASH": "Tunai",
                "QRIS": "QRIS",
                "CARD": "Kartu Debit/Kredit",
                "E_WALLET": "E-Wallet",
            }
            payment_label = payment_labels.get(req.payment_method, req.payment_method)
            receipt += f'Pembayaran   : {payment_label}\n'.encode()

        receipt += (
            f'Gerbang      : {req.gate_name}\n'.encode() +
            f'Petugas      : {req.operator}\n'.encode()
        )

        # Company info QR at bottom (LARGER for easy scanning)
        if req.show_qr and req.company_website:
            try:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_M,  # Medium error correction for better reliability
                    box_size=8,  # Increased from 3 to 8 for easier scanning
                    border=4,    # Increased from 1 to 4 (standard quiet zone)
                )
                qr.add_data(req.company_website)
                qr.make(fit=True)

                img = qr.make_image(fill_color="black", back_color="white")
                width, height = img.size
                img = img.convert('1')

                receipt += b'\n'
                receipt += esc_align_c
                receipt += b'\x1d\x76\x30\x00'
                width_bytes = (width + 7) // 8
                receipt += bytes([width_bytes & 0xFF, (width_bytes >> 8) & 0xFF])
                receipt += bytes([height & 0xFF, (height >> 8) & 0xFF])

                pixels = list(img.getdata())
                for y in range(height):
                    for x in range(0, width, 8):
                        byte_val = 0
                        for bit in range(8):
                            if x + bit < width:
                                if pixels[y * width + x + bit] == 0:
                                    byte_val |= (1 << (7 - bit))
                        receipt += bytes([byte_val])

                receipt += b'\n'
                receipt += f'Kunjungi: {req.company_website}\n'.encode()
                receipt += esc_align_l
            except Exception:
                pass

        receipt += (
            b'--------------------------------\n' +
            esc_align_c +
            b'Terima kasih\n' +
            b'Selamat jalan!\n'
        )

    # Footer
    receipt += (
        esc_align_l +
        b'--------------------------------\n' +
        f'ID: {datetime_str[-8:]}-{req.ticket_code[-8:]}\n'.encode() +
        b'\n' +
        esc_feed +
        cut_partial
    )
    return receipt


def write_test_receipt() -> None:
    """Write ESC/POS test receipt to temp file."""
    receipt_data = generate_escpos_test_receipt()
    TEST_RECEIPT_PATH.write_bytes(receipt_data)


def write_gate_ticket_receipt(req: GateTicketTestRequest) -> None:
    """Write ESC/POS gate ticket receipt to temp file."""
    receipt_data = generate_gate_ticket_receipt(req)
    GATE_TICKET_RECEIPT_PATH.write_bytes(receipt_data)


def check_printer_cups_status() -> dict:
    """Check CUPS printer status via lpstat."""
    try:
        result = subprocess.run(
            ["lpstat", "-p", PRINTER_NAME],
            capture_output=True,
            text=True,
            timeout=5
        )
        connected = result.returncode == 0 and "idle" in result.stdout.lower()
        return {
            "connected": connected,
            "cups_status": result.stdout.strip() if connected else result.stderr.strip(),
        }
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning(f"lpstat check failed: {e}")
        return {"connected": False, "cups_status": str(e)}


def check_usb_device() -> bool:
    """Check if POS80 USB device is present (0416:5011)."""
    try:
        result = subprocess.run(
            ["lsusb", "-d", "0416:5011"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0 and "0416:5011" in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


@router.get("/status", response_model=PrinterStatusResponse)
async def get_printer_status(current_user: User = current_user_dep) -> PrinterStatusResponse:
    """Get printer connection and CUPS status."""
    usb_connected = check_usb_device()
    cups_info = check_printer_cups_status()

    return PrinterStatusResponse(
        connected=usb_connected and cups_info["connected"],
        name=PRINTER_NAME,
        driver="Raw (ESC/POS)",
        uri="usb://PrinterCMD%3AESCPO/POS80%20Printer%20USB?serial=83700000000",
        usb_detected=usb_connected,
        cups_status=cups_info["cups_status"],
    )


@router.post("/test", response_model=PrinterTestResponse)
async def test_print(current_user: User = current_user_dep) -> PrinterTestResponse:
    """Send test receipt to POS80 printer via CUPS."""
    # Verify printer exists in CUPS
    cups_info = check_printer_cups_status()
    if not cups_info["connected"]:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Printer '{PRINTER_NAME}' not available in CUPS. "
                "Check USB connection and CUPS service."
            ),
        )

    # Generate and write test receipt
    try:
        write_test_receipt()
    except Exception as e:
        logger.exception("Failed to generate test receipt")
        raise HTTPException(status_code=500, detail=f"Failed to generate receipt: {e}") from e

    # Send to printer via lp command
    try:
        result = subprocess.run(
            ["lp", "-d", PRINTER_NAME, "-o", "raw", str(TEST_RECEIPT_PATH)],
            capture_output=True,
            text=True,
            timeout=15
        )

        if result.returncode != 0:
            logger.error(f"lp command failed: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Print job failed: {result.stderr.strip() or 'Unknown error'}"
            )

        # lp returns "request id is POS80-N" on success
        request_id = result.stdout.strip()
        logger.info(f"Print job submitted by {current_user.username}: {request_id}")

        return PrinterTestResponse(
            success=True,
            message="Test receipt sent to printer",
            request_id=request_id,
        )

    except subprocess.TimeoutExpired as e:
        raise HTTPException(status_code=504, detail="Print command timed out") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error during print")
        raise HTTPException(status_code=500, detail=f"Print failed: {e}") from e


@router.post("/test/gate-ticket", response_model=PrinterTestResponse)
async def test_gate_ticket(
    req: GateTicketTestRequest,
    current_user: User = current_user_dep,
) -> PrinterTestResponse:
    """Send realistic gate ticket receipt to POS80 printer via CUPS."""
    # Verify printer exists in CUPS
    cups_info = check_printer_cups_status()
    if not cups_info["connected"]:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Printer '{PRINTER_NAME}' not available in CUPS. "
                "Check USB connection and CUPS service."
            ),
        )

    # Generate and write gate ticket receipt
    try:
        write_gate_ticket_receipt(req)
    except Exception as e:
        logger.exception("Failed to generate gate ticket receipt")
        raise HTTPException(status_code=500, detail=f"Failed to generate receipt: {e}") from e

    # Send to printer via lp command
    try:
        result = subprocess.run(
            ["lp", "-d", PRINTER_NAME, "-o", "raw", str(GATE_TICKET_RECEIPT_PATH)],
            capture_output=True,
            text=True,
            timeout=15
        )

        if result.returncode != 0:
            logger.error(f"lp command failed: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Print job failed: {result.stderr.strip() or 'Unknown error'}"
            )

        request_id = result.stdout.strip()
        logger.info(
            f"Gate ticket print job submitted by {current_user.username}: "
            f"{req.direction} {req.ticket_code} -> {request_id}"
        )

        return PrinterTestResponse(
            success=True,
            message=f"Gate ticket ({req.direction}) sent to printer",
            request_id=request_id,
        )

    except subprocess.TimeoutExpired as e:
        raise HTTPException(status_code=504, detail="Print command timed out") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error during gate ticket print")
        raise HTTPException(status_code=500, detail=f"Print failed: {e}") from e


@router.post("/test/exit-scan", response_model=ExitScanResponse)
async def test_exit_scan(
    req: ExitScanRequest,
    current_user: User = current_user_dep,
) -> ExitScanResponse:
    """
    Simulate scanning an entry ticket barcode at the exit gate.
    Returns comprehensive ticket information for fee calculation.
    """
    now = datetime.now()
    exit_time = now.strftime("%Y-%m-%d %H:%M:%S")

    # Calculate duration
    duration_hours = 0.0
    duration_text = "0 jam 0 menit"
    if req.entry_time:
        try:
            entry_dt = datetime.fromisoformat(req.entry_time)
            delta = now - entry_dt
            duration_hours = round(delta.total_seconds() / 3600, 2)
            hours = int(duration_hours)
            minutes = int((duration_hours - hours) * 60)
            duration_text = f"{hours} jam {minutes} menit"
        except (ValueError, TypeError):
            pass

    # Calculate parking fee (example: Rp 5,000 per hour)
    base_rate = 5000
    parking_fee = int(duration_hours * base_rate) if duration_hours > 0 else base_rate

    return ExitScanResponse(
        ticket_code=req.ticket_code,
        ticket_type=req.ticket_type,
        plate=req.plate,
        rfid_uid=req.rfid_uid,
        entry_time=req.entry_time,
        exit_time=exit_time,
        duration_hours=duration_hours,
        duration_text=duration_text,
        parking_fee=parking_fee,
        payment_method="QRIS",
        gate_name=req.gate_name,
        company_name="PT Smart Gate Solutions",
        message=f"Tiket valid. Silakan bayar Rp {parking_fee:,}",
    )

