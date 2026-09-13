# Arsitektur Firmware Gate ESP32

Panduan memahami logika program gate ESP32. Kode dirancang sebagai **sistem gate otomatis**
dengan dua sensor ultrasonik (kendaraan dekat & kendaraan sudah lewat), proteksi halangan,
dan komunikasi serial ke GUI laptop.

---

## 0. Struktur Folder (Modular)

Kode dipecah per komponen agar mudah dicari & diperbaiki saat ada error:

```
gate/
├── lib/
│   ├── config/           → config.h   (semua pin & konstanta)
│   ├── ultrasonic/       → USSensor.h/.cpp  (kelas sensor HC-SR04)
│   ├── rfid_reader/      → RfidReader.h/.cpp (bungkus MFRC522)
│   ├── gate_controller/  → GateController.h/.cpp (state machine + servo + pass)
│   └── status_report/    → StatusReport.h/.cpp (baris display + protokol ST)
├── src/
│   └── main.cpp          → hanya orkestrasi (setup + loop + perintah serial)
├── docs/                 → dokumentasi lengkap
└── sim/                  → gate_sim.py, gate_serial_gui.py (laptop)
    └── anpr/             → kamera + OCR plat (pengganti RFID) — lihat docs/anpr.md
```

Aturan:
- **Ubah pin/konstanta → cukup `lib/config/config.h`**, tidak perlu cari di file lain.
- **Error pada sensor → buka `lib/ultrasonic`.** Error RFID → `lib/rfid_reader`.
  Error gerak/state → `lib/gate_controller`. Error status/GUI → `lib/status_report`.
- `main.cpp` tidak berisi logika — hanya menghubungkan komponen.

## 1. Arsitektur Perangkat Keras (Pin yang Dipakai)

| Fungsi | Pin | Library | Keterangan |
|--------|-----|---------|------------|
| Servo | `GPIO 18` | `ESP32Servo` | Aktuator buka/tutup gate (CLOSED=105°, OPEN=30°) |
| Button BUKA | `GPIO 4` | Arduino | Cadangan manual (aktif-HIGH) |
| HC-SR04 #1 TRIG (depan) | `GPIO 13` | Arduino | Trigger sensor depan |
| HC-SR04 #1 ECHO (depan) | `GPIO 14` | Arduino | Echo sensor depan |
| HC-SR04 #2 TRIG (exit) | `GPIO 32` | Arduino | Trigger sensor "kendaraan sudah lewat" |
| HC-SR04 #2 ECHO (exit) | `GPIO 33` | Arduino | Echo sensor exit |
| RFID SCK / MISO / MOSI | `GPIO 15/16/17` | `MFRC522` | SPI bit-bang (modul sedang diperiksa) |
| RFID SS / RST | `GPIO 25/27` | `MFRC522` | Chip select / reset |

> LCD (GPIO 21/22) dan Button TUTUP (GPIO 5) sudah dihapus dari firmware.

---

## 2. State Machine (Kondisi Gate)

```cpp
enum GateState { CLOSED, OPENING, OPEN, CLOSING };
```
Terdapat di `lib/gate_controller/GateController.h`.

| State | Arti |
|-------|------|
| `CLOSED` | Gate tertutup (posisi servo `105°` = `POS_CLOSED`) |
| `OPENING` | Gate sedang bergerak membuka |
| `OPEN` | Gate terbuka penuh (posisi servo `30°` = `POS_OPEN`) |
| `CLOSING` | Gate sedang bergerak menutup |

**Gerakan servo NON-BLOCKING:** `gate.loopMotion()` dipanggil tiap `STEP_DELAY_MS` (15ms)
dari `loop()` di `main.cpp`. Tidak ada `delay()` saat bergerak → sensor, tombol, serial, dan
status GUI tetap berjalan lancar selama gate membuka/menutup. Deteksi halangan memakai jarak
**live** (bukan basi).

---

## 3. Alur Kerja Utama

```
Kendaraan mendekat (sensor depan ≤ 30cm)
        ↓
ST:V:YES (kendaraan terdeteksi)
        ↓
Buka: button BUKA (GPIO4) / kartu RFID master (jika aktif) / serial 'O'
        ↓
OPENING → OPEN (pos 30°)
        ↓
Kendaraan lewat → sensor EXIT mendeteksi (near) lalu bersih →
         "Vehicle passed" → boleh tutup cepat
        ↓
area depan kosong → tutup (CLOSING → CLOSED)  [fallback: auto-close 10s]
```

**Prioritas "siap tutup"** (saat gate `OPEN`):
1. Sensor exit menangkap kendaraan lewat lalu area exit kosong (`passCleared`) → tutup cepat.
2. Timer `AUTO_CLOSE_MS` (10 detik) sebagai fallback.

Tutup hanya benar-benar berjalan ketika **area depan sudah kosong** (`!isVehicleNear()`) —
skenario teruji: kendaraan menyetop di gerbang tidak membuat gate menutup menimpa.

---

## 4. Logika Penting Per Bagian

### 4.1 Kelas `USSensor` (dipakai sensor depan & exit)
- Terdapat di `lib/ultrasonic` (kelas `USSensor`); objek `gate.front` & `gate.exit`
  ada di dalam `GateController`.
- `readRaw()` — kirim pulse TRIG 10µs, ukur durasi echo (`pulseIn` timeout 40ms), konversi ke cm.
  - Rumus: `cm = duration * 0.0343 / 2`
  - **Filter noise 3.3V:** nilai `< 2cm` atau `> MAX_VALID_CM` (60cm) dibuang → `-1`.
  - `badCount`: 2 baca invalid berurutan → reset buffer (tahan flicker sesaat).
- `update()` — rata-rata 5 sampel terakhir (`SMOOTH_SAMPLES`), debounce simetris
  `NEAR_COUNT=3` (3 baca dekat → `near=true`; 3 baca jauh → `near=false`).
- Kedua sensor dibaca **berurutan** dalam 1 tick (`gate.front.update()` lalu
  `gate.exit.update()`) agar echo tidak saling bertabrakan (crosstalk).

### 4.2 Sensor Exit & "Kendaraan Sudah Lewat"
`gate.updatePass()` membaca `gate.exit` + menyetel flag `passSeen` / `passCleared`
(direset setiap gate selesai terbuka):
- Kendaraan terdeteksi di area exit (`exit.isNear()`) → `passSeen = true`
- Lalu area exit kosong lagi → `passCleared = true`
- `passCleared` → `closeRequested = true` (tutup tanpa menunggu 10 detik), GUI: `VEHICLE PASSED!`

### 4.3 Buka Gate (`openGate`)
- Syarat: area depan ada kendaraan (`isVehicleNear()`) → jika tidak: `NO VEHICLE!` ditolak.
- Sumber: button BUKA (GPIO4), kartu RFID master (jika `RFID_ENABLED 1`), serial `'O'`.
- Bisa **membalik arah menutup** (CLOSING → OPENING) jika ditekan tengah menutup.

### 4.4 Tutup Gate (`closeGate`)
- Hanya berjalan saat `closeRequested` dan `!isVehicleNear()`.
- **Proteksi halangan:** selama CLOSING, jika sensor depan `< OBSTACLE_CM` (15cm) →
  gate membuka kembali (`OBSTACLE! Reopen`).

### 4.5 Tampilan Status (melalui serial ke GUI)
Prioritas baris 2 (kolom `row2`):
1. `NO VEHICLE!` — buka ditolak karena tidak ada kendaraan
2. `VEHICLE PASSED!` — kendaraan sudah lewat, siap tutup
3. `WAIT VEHICLE!` — request tutup tapi kendaraan masih dekat
4. `OPENING...` / `CLOSING...` — sedang bergerak
5. `V:YES 12cm` / `V:NO ---` — status deteksi default

---

## 5. Konfigurasi (Konstanta di `lib/config/config.h`)

| Konstanta | Nilai | Fungsi |
|-----------|-------|--------|
| `VEHICLE_CM` | 30 | Jarak ambang "kendaraan dekat" (kedua sensor) |
| `MAX_VALID_CM` | 60 | Batas atas bacaan valid (filter noise 3.3V) |
| `NEAR_COUNT` | 3 | Jumlah baca berurutan agar terdeteksi dekat/jauh |
| `OBSTACLE_CM` | 15 | Jarak halangan saat menutup |
| `AUTO_CLOSE_MS` | 10000 | Fallback auto-close setelah 10 detik terbuka |
| `STEP_DELAY_MS` | 15 | Interval gerak servo per derajat (non-blocking) |
| `DEBOUNCE_MS` | 50 | Interval cek button |
| `DIST_INTERVAL_MS` | 150 | Interval pembacaan sensor (depan+exit) |
| `SERIAL_STATUS_MS` | 300 | Interval kirim status `ST|...` ke GUI |
| `SMOOTH_SAMPLES` | 5 | Jumlah sampel rata-rata jarak |
| `RFID_ENABLED` | 1 | Saklar RFID (1 = aktif; modul belum merespons, wiring diperiksa) |
| `POS_CLOSED` / `POS_OPEN` | 105 / 30 | Sudut servo menutup / membuka |

---

## 6. Protokol Serial (Komunikasi GUI)

**Status ESP32 → PC** tiap 300ms:
```
ST|<state>|<pos>|<dist>|<vehicle>|<row1>|<row2>|<master>|<exitCm>
```
Contoh: `ST|OPEN|30|28|1|Gate: OPEN      |V:YES  28cm |----|36`

Catatan: `<exitCm>` = jarak sensor exit (field ke-9, diabaikan GUI saat ini — untuk debug).
Detail lengkap: [protocol.md](protocol.md).

**Perintah PC → ESP32:**
| Perintah | Fungsi |
|----------|--------|
| `O` | Buka gate (syarat kendaraan dekat) |
| `C` | Minta tutup (dieksekusi setelah kendaraan lewat) |
| `R` | Hapus kartu master RFID |
| `X` | Tes: pindah ke posisi CLOSED (105°) |
| `Z` | Tes: pindah ke posisi OPEN (30°) |

---

## 7. Serial Output (untuk Debug)

| Output | Arti |
|--------|------|
| `> CHIP: ESP32-D0WD-V3 ...` | Info chip saat boot |
| `> RFID chip version: 0x..` | Versi chip RC522 (0x92/0x3A = OK; 0x00/0xFF = tidak merespons) |
| `> Master card set: ...` | Kartu pertama disimpan sebagai MASTER |
| `> UID: ...` | UID kartu yang baru dibaca |
| `> GATE OPEN` | Gate membuka |
| `> Auto-close armed` | Fallback timer 10 detik aktif |
| `> Vehicle passed - close armed` | Sensor exit mendeteksi kendaraan lewat → tutup cepat |
| `> GATE CLOSING` / `> GATE CLOSED` | Proses menutup |
| `> OBSTACLE! Reopen` | Halangan terdeteksi, gate buka kembali |
| `> NO VEHICLE - rejected` | Buka ditolak karena tidak ada kendaraan |
| `> RFID UNAUTHORIZED` | Kartu tidak dikenali (saat RFID aktif) |

---

## 8. Referensi Alur Kode

```
setup()
 └─ gate.begin() (servo=CLOSED), gate.front/exit.begin(), rfid.begin(); kirim ST awal
loop()
 ├─ gate.front.update() + gate.exit.update() → baca & filter sensor (tiap 150ms)
 ├─ gate.updatePass()                        → passSeen/passCleared
 ├─ handleSerialCommands()                   → O/C/R/X/Z
 ├─ gate.loopMotion()                        → gerak servo bertahap (tiap 15ms) + halangan
 ├─ cek button (debounce+edge)               → gate.openGate() (cadangan)
 ├─ auto-close / passCleared                 → closeRequested → closeGate()
 └─ ui.send()                                → kirim ST|... tiap 300ms
```

---

## 9. Catatan Penting

- **LCD & Button TUTUP dihapus** — status diganti GUI laptop (`sim/gate_serial_gui.py`).
- **RFID aktif (`RFID_ENABLED 1`)** tapi modul RC522 belum merespons (`0x0`) — sedang
  diperiksa (wiring/power/solder pin modul). Kartu pertama saat boot = MASTER (RAM).
  Nonaktifkan sementara dengan `RFID_ENABLED 0` di `lib/config/config.h`.
- **HC-SR04 di supply 3.3V** dengan filter software noise. Untuk akurasi produksi, gunakan
  5V + voltage divider atau HC-SR04P (3.3V native).
- **Sensor exit** membaca area di sisi keluar gerbang; penutupan "cepat" hanya terjadi jika
  kendaraan benar-benar lewat AND area depan sudah kosong. Jika tidak ada kendaraan lewat,
  auto-close 10 detik tetap bekerja.
- Sudut servo `POS_CLOSED=105`, `POS_OPEN=30` — sesuaikan dengan arah fisik servo Anda.