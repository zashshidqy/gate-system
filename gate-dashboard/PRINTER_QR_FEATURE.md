# Gate Ticket Printer with QR Code Feature

## ✅ Completed Features

### Backend (`POST /printer/test/gate-ticket`)
- **Professional ticket layout** with company branding
- **QR Code generation** linking to company website
- **ESC/POS image printing** (GS v 0 command for bitmap QR)
- **Customizable fields**:
  - Company name (appears as header in double-height bold)
  - Company website (embedded in QR code)
  - Direction indicators (>>> for ENTRY, <<< for EXIT)
  - Ticket code, type, method
  - Plate number, RFID UID (optional)
  - Gate name, operator
  - Toggle QR code on/off

### Frontend (Settings → Printer Tab)
- **Gate Ticket Test Form** with all customizable fields:
  - Direction (MASUK/KELUAR)
  - Ticket type (Sekali Masuk, Multi Hari, VIP, Staf)
  - Method (QR Scan, RFID, Manual, ANPR)
  - Gate name, Ticket code
  - Plate number, RFID UID (optional)
  - Operator name
  - **Company name** (default: "PT Smart Gate Solutions")
  - **Company website** (default: "https://smartgate.co.id")
  - **Show QR checkbox** (enable/disable QR code printing)

## 📋 Receipt Format

```
PT SMART GATE SOLUTIONS
================================
>>> TIKET MASUK >>>
================================

KODE TIKET: TKT-20261012-ABCD1234

Tanggal    : 12/10/2026
Waktu      : 12:34:56
--------------------------------
Tipe Tiket : Sekali Masuk
Metode     : Scan QR Code
Plat Nomor : B 1234 ABC
RFID UID   : A1 B2 C3 D4
--------------------------------
Gerbang    : Gerbang Utama
Petugas    : admin
--------------------------------
    [QR CODE IMAGE]
Scan untuk info lebih lanjut
https://smartgate.co.id
--------------------------------
Terima kasih atas kunjungan Anda
Selamat jalan!
--------------------------------
ID: 12:34:56-ABCD1234

[Partial Cut]
```

## 🚀 Usage

### 1. Start Backend
```bash
cd /home/zhundy/Documents/PlatformIO/Projects/gate/gate-dashboard/backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Start Frontend
```bash
cd /home/zhundy/Documents/PlatformIO/Projects/gate/gate-dashboard/frontend
npm run dev
```

### 3. Test Print
1. Navigate to **Settings → Printer** tab
2. Fill in the **"Test Print Tiket Gerbang (Real Case)"** form
3. Customize company name and website
4. Enable/disable QR code with checkbox
5. Click **"Cetak Tiket Gerbang"**

## 🔧 Technical Details

### QR Code Implementation
- Library: `qrcode` (Python, already installed)
- Error correction: Level L (low)
- Box size: 4 (optimal for 80mm thermal printer)
- Border: 2 modules
- Format: 1-bit monochrome bitmap
- ESC/POS command: `GS v 0` (raster bit image mode)

### Professional Layout Features
- **Double-height header** with company name
- **Direction indicators** (>>> or <<<) for visual clarity
- **Bold ticket code** for easy scanning
- **Aligned labels** with consistent spacing (colon-aligned)
- **Sectioned information** with separators
- **Center-aligned QR** with explanatory text
- **Friendly footer** message
- **Short transaction ID** for reference

### API Changes
- Added `company_name: str` field (default: "PT Smart Gate Solutions")
- Added `company_website: str` field (default: "https://smartgate.co.id")
- Added `show_qr: bool` field (default: true)

### Frontend Changes
- Added 2 text inputs for company branding
- Added checkbox to toggle QR code
- Updated default ticket code to 2026
- Improved form layout with better grouping

## 📝 Future Enhancements (Optional)
- [ ] Save company settings in database (System Settings table)
- [ ] Logo upload for header (convert to ESC/POS bitmap)
- [ ] Multiple language support for ticket text
- [ ] Ticket templates (save/load preset configurations)
- [ ] Print preview before sending to printer
- [ ] Batch printing with CSV import

## 🎫 Use Cases
1. **Customer/Visitor Tickets** - Entry/exit tracking with company branding
2. **Parking Receipts** - Vehicle information with website for mobile payment
3. **Event Badges** - Quick access to event website/info
4. **Loyalty Programs** - QR code links to member portal
5. **Feedback Collection** - QR code links to survey/feedback form

---
**Created:** 2026-10-12  
**Version:** 1.0  
**Printer:** iware IW 8220 / POS80 (80mm thermal, ESC/POS)
