# Wiring ESP32 Gate System

> Dokumentasi ini akan **selalu diupdate** setiap terjadi penambahan/perubahan hardware.

## Board
- **MCU:** ESP32 DOIT DevKit V1
- **Aktuator:** Servo (SG90/MG996R)
- **Input:** Module button (VCC/GND/OUT) x1 (Buka)
- **Sensor:** HC-SR04 (ultrasonic) x2 — sensor depan (kendaraan dekat) & sensor exit (kendaraan sudah lewat)
- **RFID:** RC522 (MFRC522) — kartu berizin membuka gate (SEMENTARA DINONAKTIFKAN, menunggu modul baru)

---

## Pin Allocation (TERBARU)

| Fungsi | GPIO | Mode | Keterangan |
|--------|------|------|------------|
| Servo SIG | GPIO 18 | Output (LEDC) | PWM servo |
| Button BUKA | GPIO 4 | Input (OUT) | Active-HIGH saat ditekan (cadangan) |
| HC-SR04 #1 TRIG (depan) | GPIO 13 | Output | Trigger sensor depan |
| HC-SR04 #1 ECHO (depan) | GPIO 14 | Input | Echo sensor depan (3.3V) |
| HC-SR04 #2 TRIG (exit) | **GPIO 32** | **Output** | Trigger sensor "kendaraan sudah lewat" |
| **HC-SR04 #2 ECHO (exit)** | **GPIO 33** | **Input** | Echo sensor exit (3.3V) |
| RFID SCK | GPIO 15 | SPI (bit-bang) | Clock RFID RC522 (cadangan) |
| RFID MISO | GPIO 16 | SPI (bit-bang) | Respond dari reader (cadangan) |
| RFID MOSI | GPIO 17 | SPI (bit-bang) | Perintah ke reader (cadangan) |
| RFID SS | GPIO 25 | SPI (bit-bang) | Chip select / SDA (cadangan) |
| RFID RST | GPIO 27 | Output | Reset reader (cadangan) |

> **Catatan:** LCD 16x2 I2C (GPIO 21/22) dan Button TUTUP (GPIO 5) sudah **dihapus** dari firmware.
> GPIO 21/22/5 kini bebas. Sensor exit sengaja dipasang di **GPIO 32/33** (pojok header, jauh dari
> servo GPIO18, RFID GPIO15/17/25/27, dan USB-serial GPIO1/3) agar kabel tidak menabrak / terkena noise.

### Power / Ground
| Jalur | Tujuan |
|-------|--------|
| 3.3V | VCC Button Buka, **VCC HC-SR04 x2**, VCC RFID RC522 |
| 5V | Servo VCC (atau power eksternal) |
| GND | Servo, Button Buka, HC-SR04 x2, RFID RC522 |

---

## Wiring Lengkap (Breadboard)

### Rel Daya Breadboard
```
           [ + ] = 3.3V      [ + ] = 5V
ESP32 ──────────────────────── breadboard
 3.3V ──rel (+) kiri ──→ VCC button + VCC kedua HC-SR04 + VCC RFID
 5V   ──rel (+) kanan──→ VCC servo
 GND  ──rel (-) ───────→ GND semua
```

### Servo
```
Servo        ESP32
VCC (merah)  → 5V   (atau power eksternal 5V)
GND (coklat) → GND
SIG (oranye) → GPIO 18
```

### Module Button Buka (VCC/GND/OUT)
```
Button        ESP32
VCC         → 3.3V
GND         → GND
OUT         → GPIO 4
```

### HC-SR04 #1 — Sensor Depan (deteksi kendaraan dekat)
> **PENTING:** kedua HC-SR04 disupply **3.3V** agar ECHO mengeluarkan ±3.3V dan **aman ke ESP32
> tanpa resistor**. (Kalau disupply 5V, wajib pakai voltage divider di ECHO.)
```
HC-SR04 #1     ESP32
VCC          → 3.3V
GND          → GND
TRIG         → GPIO 13
ECHO         → GPIO 14
```

### HC-SR04 #2 — Sensor Exit (kendaraan sudah lewat)
```
HC-SR04 #2     ESP32
VCC          → 3.3V
GND          → GND
TRIG         → GPIO 32
ECHO         → GPIO 33
```
> Dipasang di **sisi keluar gerbang** (± setelah posisi gate ketika terbuka), menghadap area
> tempat kendaraan melintas setelah lewat. Sensor depan & exit dibaca **bergantian** di kode
> agar echo keduanya tidak saling mengganggu (crosstalk).
> Pin 32/33 dipilih di **pojok header** supaya tidak bersebelahan dengan servo (18) maupun
> RFID (15/16/17/25/27) → wiring rapi & bebas noise.

### RFID RC522 (terpasang — modul sedang diperiksa)
> **PENTING:** RC522 disupply **3.3V** (bukan 5V — bisa rusak). Menggunakan **SPI bit-bang**.
> `RFID_ENABLED 1` di `lib/config/config.h`, tapi modul belum merespons (`chip version: 0x0`)
> → sedang diperiksa (power/wiring/pin solder). Wiring tetap seperti di bawah ini.
```
RC522            ESP32
VCC (3.3V)     → 3.3V
GND            → GND
SDA  (SS)      → GPIO 25
SCK  (clock)   → GPIO 15
MOSI (TX/Data) → GPIO 17
MISO (RX/Data) → GPIO 16
RST  (reset)   → GPIO 27
IRQ            → (tidak dipakai, abaikan)
```
> **Catatan pin:** susunan pin modul biasanya `SDA – SCK – MOSI – MISO – IRQ – GND – RST – VCC`.

---

## Pin yang TELAH DIPAKAI (Avoid)
```
GPIO 4   → Button Buka
GPIO 13  → HC-SR04 #1 TRIG (depan)
GPIO 14  → HC-SR04 #1 ECHO (depan)
GPIO 18  → Servo
GPIO 32  → HC-SR04 #2 TRIG (exit)
GPIO 33  → HC-SR04 #2 ECHO (exit)
GPIO 15  → RFID SCK   (cadangan)
GPIO 16  → RFID MISO  (cadangan)
GPIO 17  → RFID MOSI  (cadangan)
GPIO 25  → RFID SS    (cadangan)
GPIO 27  → RFID RST   (cadangan)
GPIO 1   → TX (USB-Serial, dipakai upload)
GPIO 3   → RX (USB-Serial, dipakai upload)
```

### Pin TIDAK RECOMMENDED di ESP32 (DOIT DevKit V1)
| GPIO | Alasan |
|------|--------|
| 0, 2, 12 | Boot strap / flash mode |
| 6, 7, 8, 9, 10, 11 | Terhubung ke flash SPI - TIDAK BOLEH dipakai |
| 1, 3 | TX0 / RX0 (USB serial untuk upload & monitor) |
| 34, 35, 36, 39 | Input-ONLY - tidak bisa output PWM |

### Pin AMAN untuk ekspansi berikutnya
```
GPIO 5, 19, 21, 22, 26
```

---

## Logika / Status
- **Sensor depan (HC-SR04 #1):** deteksi kendaraan "dekat" (`≤ VEHICLE_CM` 30cm) → syarat agar gate boleh buka.
- **Sensor exit (HC-SR04 #2):** kendaraan terdeteksi lewat area exit lalu kosong → `passCleared` → gate boleh **menutup lebih cepat** (tanpa menunggu 10 detik penuh), selama area depan sudah kosong.
- **Button BUKA (GPIO4):** cadangan manual → `openGate()`.
- **Auto-close:** 10 detik (`AUTO_CLOSE_MS`) sebagai fallback jika sensor exit tidak mendeteksi lewatan.
- **Proteksi halangan:** saat menutup, sensor depan `< OBSTACLE_CM` (15cm) → gate membuka kembali.
- Kartu RFID: kartu pertama saat boot = MASTER (sementara; RFID dimatikan, menunggu modul baru).

---

## Log Update
| Tanggal | Perubahan |
|---------|-----------|
| (hari ini) | **Tambah HC-SR04 #2 (exit)** — TRIG=GPIO32, ECHO=GPIO33: deteksi kendaraan sudah lewat → tutup lebih cepat |
| (hari ini) | Pin exit dipaksa di pojok header (32/33) agar tidak menabrak servo(18) & RFID |
| (hari ini) | Hapus LCD (GPIO21/22) & Button TUTUP (GPIO5) dari firmware |
| (hari ini) | Servo CLOSED=105°, OPEN=30°; gerak non-blocking (sensor/tombol/serial tetap responsif saat bergerak) |
| (hari ini) | RFID dimask (`RFID_ENABLED 0`) — modul RC522 tidak merespons, menunggu penggantian |
| (hari ini) | RFID difungsikan lagi (`RFID_ENABLED 1`) — modul baru tetap `0x0`, diagnosa wiring/power/solder pin modul |
| (hari ini) | **Refactor modular** — kode dipecah per komponen di `lib/` (config, ultrasonic, rfid_reader, gate_controller, status_report); pin & konstanta pindah ke `lib/config/config.h` |