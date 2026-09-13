# Gate System ESP32 — Dokumentasi

Sistem **gate otomatis** berbasis ESP32: servo buka/tutup, dua sensor ultrasonik (kendaraan
datang & kendaraan sudah lewat), RFID RC522 (master card), dan GUI laptop pengganti LCD.

---

## Isi Dokumentasi

| File | Isi |
|------|-----|
| [architecture.md](architecture.md) | Arsitektur firmware: struktur folder, state machine, alur utama, logika per komponen |
| [anpr.md](anpr.md) | **ANPR (pengganti RFID)**: kamera + OCR plat, mode simulasi, CCTV nanti |
| [hardware.md](hardware.md) | Daftar komponen (BOM), kebutuhan daya, pin allocation |
| [wiring.md](wiring.md) | **Wiring lengkap** pin-ke-pin di breadboard |
| [protocol.md](protocol.md) | Protokol serial ESP32 ↔ GUI (`ST|...` + perintah `O/C/R/X/Z`) |
| [configuration.md](configuration.md) | Semua konstanta/tuning di `lib/config/config.h` + cara aktif/mask RFID |
| [testing.md](testing.md) | Prosedur verifikasi sistem (serial, servo, sensor, GUI, skenario) |
| [troubleshooting.md](troubleshooting.md) | Gejala error → penyebab → solusi (RFID, sensor, servo, dll) |
| [CHANGELOG.md](CHANGELOG.md) | Log perubahan kode/hardware |

---

## Ringkasan Cepat

| Hal | Nilai |
|-----|-------|
| MCU | ESP32 DOIT DevKit V1 (`ESP32-D0WD-V3`, 4MB flash, tanpa PSRAM) |
| Framework | PlatformIO + Arduino |
| Aktuator | Servo (SIG = GPIO **18**), `POS_CLOSED=105°`, `POS_OPEN=30°` |
| Sensor depan (kendaraan datang) | HC-SR04, TRIG=**13**, ECHO=**14** |
| Sensor exit (kendaraan lewat) | HC-SR04, TRIG=**32**, ECHO=**33** |
| RFID | RC522, SCK=**15** MISO=**16** MOSI=**17** SS=**25** RST=**27** (**status: modul belum merespons `0x0`**) |
| ANPR (pembuka alternatif RFID) | Kamera + OCR plat → daftar `data/plat_izin.json` → buka gate (lihat [anpr.md](anpr.md)) |
| Button | BUKA = GPIO **4** (aktif-HIGH, cadangan) |
| Status ke GUI | Serial `ST|...` tiap **300ms** |
| Display fisik | — (LCD dihapus, diganti `sim/gate_serial_gui.py`) |

> Semua nilai pin/konstanta hanya boleh diubah di **`lib/config/config.h`**.

---

## Menjalankan

```bash
# Build & upload ke ESP32 (pastikan GUI serial ditutup dulu agar port tidak dipakai)
pio run -t upload --upload-port /dev/ttyUSB0

# Monitor serial (debug langsung)
pio device monitor -p /dev/ttyUSB0 -b 115200

# GUI laptop (pengganti LCD) — wajib python3.11
python3.11 sim/gate_serial_gui.py

# Simulator murni di laptop (tanpa hardware)
python3.11 sim/gate_sim.py --selftest
```

---

## Struktur Folder

```
gate/
├── lib/                    # komponen firmware (PlatformIO auto-build per folder)
│   ├── config/             # config.h — semua pin & konstanta
│   ├── ultrasonic/         # USSensor (depan & exit)
│   ├── rfid_reader/        # bungkus MFRC522 (init/master/auth)
│   ├── gate_controller/    # state machine + gerak servo + logika pass
│   └── status_report/      # baris display 2x16 + protokol ST
├── src/
│   └── main.cpp            # hanya orkestrasi (setup + loop + perintah serial)
├── docs/                   # dokumentasi ini
├── sim/                    # gate_sim.py (sim), gate_serial_gui.py (GUI live)
│   └── anpr/               # ANPR (kamera + OCR plat) — pengganti RFID
└── data/
    └── plat_izin.json      # whitelist plat berizin (dibaca modul ANPR)
```

- **Mau ubah pin/jarak/timing?** → `lib/config/config.h`
- **Error saat membaca sensor?** → `lib/ultrasonic`
- **Error RFID/kartu?** → `lib/rfid_reader`
- **Error gerak/state?** → `lib/gate_controller`
- **Error tampilan/protokol?** → `lib/status_report`