# Wiring ESP32 Gate System

> Dokumentasi ini akan **selalu diupdate** setiap terjadi penambahan/perubahan hardware.

## Board
Sistem terdiri dari **2 unit ESP32 mandiri** — satu per palang gerbang. Wiring **tidak sepenuhnya
identik**: Unit Entry pakai 2 HC-SR04, sedangkan Unit Exit hanya pakai **1 HC-SR04** (sensor pass).

Per unit:
| Komponen | Unit **Entry** | Unit **Exit** |
|---|---|---|
| ESP32 DOIT DevKit V1 | ✅ | ✅ |
| Servo SG90/MG996R | ✅ | ✅ |
| Module button (BUKA) | ✅ | ✅ (opsional) — pengganti RFID / cadangan |
| HC-SR04 approach (kendaraan menunggu) | ✅ | ❌ — tidak dipasang |
| HC-SR04 pass (kendaraan sudah lewat) | ✅ | ✅ |
| RFID RC522 | ✅ | ✅ (tap untuk buka) |
| **Active buzzer** (greeting/deny) | ✅ | ✅ |

> **Unit Exit** selalu **standby** dalam keadaan tertutup: buka hanya lewat tap RFID (atau button),
> tidak ada syarat "kendaraan dekat". Sensor pass dipakai untuk mendeteksi kendaraan lewat → tutup
> kembali.

---

## Pin Allocation — Unit Entry (TERBARU)

### Unit Entry — full (2x HC-SR04 + servo + RFID + button)

| Fungsi | GPIO | Mode | Keterangan |
|--------|------|------|------------|
| Servo SIG | GPIO 18 | Output (LEDC) | PWM servo |
| Button BUKA | GPIO 4 | Input (OUT) | Active-HIGH saat ditekan (cadangan) |
| HC-SR04 #1 TRIG (approach) | GPIO 13 | Output | Trigger sensor approach (kendaraan menunggu) |
| HC-SR04 #1 ECHO (approach) | GPIO 14 | Input | Echo sensor approach (3.3V) |
| HC-SR04 #2 TRIG (pass) | **GPIO 32** | **Output** | Trigger sensor "kendaraan sudah lewat" |
| **HC-SR04 #2 ECHO (pass)** | **GPIO 33** | **Input** | Echo sensor pass (3.3V) |
| RFID SCK | GPIO 15 | SPI | Clock RFID RC522 |
| RFID MISO | GPIO 16 | SPI | Respond dari reader |
| RFID MOSI | GPIO 17 | SPI | Perintah ke reader |
| RFID SS | GPIO 25 | SPI | Chip select / SDA |
| RFID RST | GPIO 27 | Output | Reset reader |

> **Catatan:** LCD 16x2 I2C (GPIO 21/22) dan Button TUTUP (GPIO 5) sudah **dihapus** dari firmware.
> GPIO 21/22/5 kini bebas. Sensor pass sengaja dipasang di **GPIO 32/33** (pojok header, jauh dari
> servo GPIO18, RFID GPIO15/17/25/27, dan USB-serial GPIO1/3) agar kabel tidak menabrak / terkena noise.

### Unit Exit — ringkas (1x HC-SR04 + servo + RFID + button opsional)

| Fungsi | GPIO | Mode | Keterangan |
|--------|------|------|------------|
| Servo SIG | GPIO 18 | Output (LEDC) | PWM servo |
| Button BUKA | GPIO 4 | Input (OUT) | Active-HIGH (opsional, cadangan) |
| HC-SR04 #2 TRIG (pass) | GPIO 32 | Output | Trigger sensor "kendaraan sudah lewat" |
| HC-SR04 #2 ECHO (pass) | GPIO 33 | Input | Echo sensor pass (3.3V) |
| RFID SCK | GPIO 15 | SPI | Clock RFID RC522 |
| RFID MISO | GPIO 16 | SPI | Respond dari reader |
| RFID MOSI | GPIO 17 | SPI | Perintah ke reader |
| RFID SS | GPIO 25 | SPI | Chip select / SDA |
| RFID RST | GPIO 27 | Output | Reset reader |
| GPIO 13 / 14 | — | — | **Tidak dipasang** (tanpa sensor approach) |

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

### HC-SR04 #1 — Sensor Approach (kendaraan menunggu di depan palang) — **hanya Unit Entry**
> **PENTING:** kedua HC-SR04 disupply **3.3V** agar ECHO mengeluarkan ±3.3V dan **aman ke ESP32
> tanpa resistor**. (Kalau disupply 5V, wajib pakai voltage divider di ECHO.)
> Unit Exit **tidak** memasang sensor ini — GPIO 13/14 dibiarkan kosong.
```
HC-SR04 #1     ESP32
VCC          → 3.3V
GND          → GND
TRIG         → GPIO 13
ECHO         → GPIO 14
```

### HC-SR04 #2 — Sensor Pass (kendaraan sudah lewat) — Entry & Exit
```
HC-SR04 #2     ESP32
VCC          → 3.3V
GND          → GND
TRIG         → GPIO 32
ECHO         → GPIO 33
```
> Dipasang di **sisi belakang palang** (setelah gate ketika terbuka), menghadap area tempat
> kendaraan melintas setelah lewat. Sensor approach & pass dibaca **bergantian** di kode
> agar echo keduanya tidak saling mengganggu (crosstalk).
> Pin 32/33 dipilih di **pojok header** supaya tidak bersebelahan dengan servo (18) maupun
> RFID (15/16/17/25/27) → wiring rapi & bebas noise.

### RFID RC522 (terpasang — modul sedang diperiksa)
> **PENTING:** RC522 disupply **3.3V** (bukan 5V — bisa rusak). Menggunakan **SPI bit-bang**.
> `RFID_ENABLED 1` di `src/entry/config.h` / `src/exit/config.h`
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
GPIO 13  → HC-SR04 #1 ECHO (approach)
GPIO 14  → HC-SR04 #1 TRIG (approach)
GPIO 18  → Servo
GPIO 32  → HC-SR04 #2 TRIG (pass)
GPIO 33  → HC-SR04 #2 ECHO (pass)
GPIO 15  → RFID SCK
GPIO 16  → RFID MISO
GPIO 17  → RFID MOSI
GPIO 25  → RFID SS
GPIO 27  → RFID RST
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
- **Sensor approach (HC-SR04 #1) — Unit Entry saja:** deteksi kendaraan "dekat" (`≤ VEHICLE_CM` 30cm) → syarat agar gate boleh buka.
- **Sensor pass (HC-SR04 #2) — Entry & Exit:** kendaraan terdeteksi lewat area palang lalu kosong → `passCleared` → gate boleh **menutup lebih cepat** (tanpa menunggu 10 detik penuh).
- **Unit Exit:** tanpa approach → **selalu standby tertutup**; buka langsung dari tap RFID / button (tanpa syarat "kendaraan dekat"); tutup setelah `passCleared` atau auto-close.
- **Button BUKA (GPIO4):** cadangan manual → `openGate()`.
- **Auto-close:** 10 detik (`AUTO_CLOSE_MS`) sebagai fallback jika sensor pass tidak mendeteksi lewatan.
- **Proteksi halangan (Entry):** saat menutup, sensor approach `< OBSTACLE_CM` (15cm) → gate membuka kembali. *(Unit Exit tanpa approach → proteksi halangan nonaktif.)*
- Kartu RFID: kartu pertama saat boot = MASTER; provisioning kartu diulang di tiap unit (Entry & Exit).

---

## Arsitektur Dua Unit (Entry + Exit)

```
   LUAR (jalan)
        │
  ┌─────┴──────┐          ┌──────┴─────┐
  │  UNIT 1    │  jalur   │  UNIT 2    │
  │  ENTRY     │ ═════════ │  EXIT      │
  │  approach◄─┤           ├─► (no)     │
  │  pass ──►  │           │  pass ──►  │
  └────────────┘           └────────────┘
```

- **Unit 1 (Entry):** 2 sensor (approach + pass). Kendaraan datang → approach + tap RFID → buka → pass → tutup cepat.
- **Unit 2 (Exit):** 1 sensor (pass saja). **Selalu standby tertutup**; buka hanya via **tap RFID** (atau button) → kendaraan lewat → pass mendeteksi + kosong → tutup. Tanpa syarat "kendaraan dekat".
- **Power per unit:** tiap unit punya suplai sendiri — 3.3V untuk sensor+RFID,
  5V (atau eksternal) untuk servo, ground bersama dalam satu unit. Jangan disambung antar unit.
- **Firmware** perlu pembedaan sisi (**ENTRY vs EXIT**) via konfigurasi: unit EXIT menonaktifkan
  sensor approach & syarat "vehicle near" saat buka.
- **Provisioning kartu master** diulang per unit: tap kartu pertama saat boot (jadi master), atau
  kirim serial `A` lalu tap kartu — dilakukan terpisah di ESP32 Entry dan ESP32 Exit.
- Daftar kartu master **tidak otomatis tersinkron antar unit** — tambah/hapus kartu harus diulang
  di masing-masing unit (perintah `A` / `Q` / `R`).

---

## Log Update
| Tanggal | Perubahan |
|---------|-----------|
| (hari ini) | **Unit Exit ringkas** — hanya 1 HC-SR04 (pass); tanpa approach; buka via tap RFID/button; selalu standby tertutup |
| (hari ini) | **Arsitektur 2 unit ESP32** (Entry + Exit) — Unit Entry full, Unit Exit ringkas; RFID dinyalakan (`RFID_ENABLED 1`) |
| (hari ini) | **Tambah HC-SR04 #2 (exit)** — TRIG=GPIO32, ECHO=GPIO33: deteksi kendaraan sudah lewat → tutup lebih cepat |
| (hari ini) | Pin exit dipaksa di pojok header (32/33) agar tidak menabrak servo(18) & RFID |
| (hari ini) | Hapus LCD (GPIO21/22) & Button TUTUP (GPIO5) dari firmware |
| (hari ini) | Servo CLOSED=105°, OPEN=30°; gerak non-blocking (sensor/tombol/serial tetap responsif saat bergerak) |
| (hari ini) | RFID dimask (`RFID_ENABLED 0`) — modul RC522 tidak merespons, menunggu penggantian |
| (hari ini) | RFID difungsikan lagi (`RFID_ENABLED 1`) — modul baru tetap `0x0`, diagnosa wiring/power/solder pin modul |
| (hari ini) | **Greeting sound** — active buzzer (GPIO 2, LEDC ch 7) masuk BOM & wiring per unit; +section pemasangan |
| (hari ini) | **Tanpa auto-close** — `AUTO_CLOSE_MS` dihapus; gate terbuka boleh lama, tutup hanya setelah pass/sensor exit |
| (hari ini) | **Refactor modular** — kode dipecah per komponen di `lib/` (config, ultrasonic, rfid_reader, gate_controller, status_report); pin & konstanta pindah ke `lib/config/config.h` |