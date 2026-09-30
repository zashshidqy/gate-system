# Gate System (ESP32 Firmware)

Sistem gerbang otomatis berbasis ESP32 dengan dua unit: **ENTRY** (gerbang masuk) dan **EXIT** (gerbang keluar).

## 📁 Struktur

```
gate-system/
├── src/
│   ├── entry/            # Firmware gerbang masuk
│   │   ├── main.cpp
│   │   └── config.h
│   └── exit/             # Firmware gerbang keluar
│       ├── main.cpp
│       └── config.h
├── lib/                  # Library bersama
│   ├── buzzer/
│   ├── gate_controller/  # State machine + servo
│   ├── rfid_reader/      # MFRC522 wrapper
│   ├── status_report/    # Protokol serial ST|...
│   └── ultrasonic/       # HC-SR04 sensor
├── sim/                  # Simulasi & GUI (Python)
│   ├── gate_dual_gui.py  # GUI dual gate (Tkinter)
│   ├── gate_serial_gui.py
│   ├── gate_sim.py       # Simulator logika
│   ├── passage_log.py    # Logger ke SQLite
│   └── anpr/             # ANPR module (optional)
├── data/                 # Database & capture
│   ├── gate.db           # SQLite (passage logs)
│   ├── captures/         # Foto RFID/ANPR
│   ├── plat_izin.json    # Plat nomor terdaftar
│   └── sounds/           # File audio
├── sound/                # Sound effects (m4a)
├── docs/                 # Dokumentasi hardware
│   ├── architecture.md
│   ├── protocol.md
│   ├── wiring.md
│   └── hardware.md
├── scripts/              # Build scripts
├── platformio.ini        # Config PlatformIO (2 env)
└── gate.code-workspace   # VS Code workspace
```

## ⚙️ Hardware

| Komponen | Pin | Keterangan |
|----------|-----|------------|
| Servo | GPIO 18 | Aktuator buka/tutup |
| Button BUKA | GPIO 4 | Manual open |
| HC-SR04 #1 (Approach) | GPIO 13/14 | Sensor kendaraan mendekat |
| HC-SR04 #2 (Exit) | GPIO 32/33 | Sensor kendaraan lewat |
| RFID SPI | GPIO 15/16/17 | SCK/MISO/MOSI |
| RFID SS/RST | GPIO 25/27 | Chip select / reset |

## 🔧 Build & Upload

```bash
# Install PlatformIO
pip install platformio

# Build & upload ENTRY
pio run -e esp32doit-devkit-v1 -t upload

# Build & upload EXIT
pio run -e esp32-exit -t upload

# Monitor serial
pio device monitor -p /dev/ttyUSB0 -b 115200
```

## 📡 Protokol Serial

**Status (ESP32 → PC)** - setiap 300ms:
```
ST|<state>|<pos>|<dist>|<vehicle>|<row1>|<row2>|<masters>|<exitCm>|<rfidVer>|<lastUid>|<lastAuth>|<count>
```

**Perintah (PC → ESP32)** - single char:
| Char | Fungsi |
|------|--------|
| `O` | Buka gate (perlu kendaraan dekat) |
| `C` | Tutup gate |
| `A` | Mode tambah master (15s) |
| `Q` | Mode hapus master (15s) |
| `L` | List master |
| `R` | Reset all master |
| `X` | Test → CLOSED (105°) |
| `Z` | Test → OPEN (30°) |

## 🗄️ Database

SQLite `data/gate.db` dengan tabel `passages`:
- `id`, `ts`, `direction` (ENTRY/EXIT), `method` (RFID/ANPR/MANUAL)
- `uid`, `plate`, `allowed`, `image_path`, `note`

## 🖥️ GUI Simulasi

```bash
cd sim
python3 gate_dual_gui.py    # Dual gate GUI (ENTRY + EXIT)
python3 gate_sim.py         # Simulator logika (tanpa hardware)
python3 gate_sim.py --selftest  # Unit test logika
```

## 📚 Dokumentasi

Lihat folder `docs/`:
- `architecture.md` - Arsitektur firmware
- `protocol.md` - Protokol serial detail
- `wiring.md` - Diagram wiring
- `hardware.md` - Spesifikasi hardware
- `configuration.md` - Konfigurasi pin & konstanta