# Changelog Project Gate

> Log perubahan project gate. Diupdate setiap ada perubahan kode/hardware.
> Format: `[Tanggal] - Fitur yang ditambahkan/diubah`

## Log

### 2026-09-14 — Add-on: Capture Saat Tap, Database, Greeting Sound, Tanpa Auto-Close
Semua 4 poin di `docs/add-on.md` selesai (`RFID_ENABLED`, buzzer, gate_db, simulator).

**Firmware (Entry & Exit — `pio run` 2 env SUCCESS):**
- **Greeting sound** — lib `lib/buzzer/` (non-blocking) + `BUZZER_PIN` (GPIO 2, LEDC ch 7):
  kartu sah + kendaraan → `greet()`; kartu asing → `deny()`. Pin/config di
  `src/entry/config.h` + `src/exit/config.h` (`BUZZER_PIN 2`, `BUZZER_LEDC_CH 7`).
- **Tanpa auto-close** — `AUTO_CLOSE_MS` dibuang; gate boleh terbuka lama; tutup hanya
  setelah kendaraan lewat sensor pass (`passCleared`) atau perintah `C` manual.
- **Simulator** `sim/gate_sim.py`: state sensor **exit** (pass/cleared), tombol "Tutup Manual",
  selftest **18 cek ALL PASS**; GUI tanpa auto-close.

**Simulator/GUI add-on:**
- **DB akses** — `sim/passage_log.py` (SQLite `data/gate.db`, gambar `data/captures/`):
  `PassageLog.record()`, `recent()`, `count()`, `clear()`, `save_image()`; selftest ALL PASS.
- **Capture saat tap RFID** — GUI `sim/gate_serial_gui.py`: deteksi GRANTED/DENIED dari `ST|`,
  dialog `CaptureDialog` (preview kamera + **input plat** + arah ENTRY/EXIT) → gambar disimpan
  + baris DB; metode `_grab_latest_frame`, `_record_passage`, `_on_rfid_granted/denied`.
- **Greeting sound di GUI** — `_play_greeting()`/`_play_deny()` via aplay/paplay/play (fallback bell);
  ANPR pakai API `PaddleOCR` lazy-load (`available()` pakai `find_spec`).

### 2026-09-09 — Live Kamera + Deteksi Kotak di GUI
- Panel **Kamera (langsung)** di GUI: video real-time dari webcam (~30fps, thread terpisah)
- **Kotak deteksi** digambar di video: segmen pengisi plat (hijau) vs teks lain (kuning)
- **Banner overlay** memperlihatkan hasil kamera: `PLAT | skor% | IZIN/TIDAK TERDAFTAR`
- `PlateOCR` menyimpan `last_boxes` + segmen terpilih (rekan `_best_plate`)
- `AnprService.attempt(frame=None)` menerima frame dari luar → scan tanpa rebutan kamera
- OCR di two bicara `GA`→ditolak (uji), `B1234CD` baca-tunggal → IZIN (uji buatan)

### 2026-09-09 — ANPR (Pengganti RFID, Kamera + OCR Plat)
- **Latar:** modul RC522 belum berfungsi (`0x0`) → otorisasi masuk disandarkan dulu ke pembacaan plat nomor via kamera.
- Modul baru `sim/anpr/`: `config`, `plate_db` (whitelist + fuzzy match), `camera_source` (webcam index / URL RTSP), `plate_ocr` (PaddleOCR lazy-load), `plate_service` (orkestrasi)
- Integrasi ke GUI `gate_serial_gui.py`: panel "ANPR — Pengganti RFID (kamera)" — check aktif, kolom sumber, tombol **Scan Plat Sekarang**, label hasil; **auto-trigger** saat `vehicle=1 & state=CLOSED` → kirim `O`
- Threading aman: worker OCR via `queue.Queue` (tanpa `root.after` lintas-thread)
- Daftar plat berizin: `data/plat_izin.json` (format plat Indonesia + koreksi O↔0, I↔1, S↔5, dsb)
- **Mode simulasi** `MOCK_ANPR` (`sim/anpr/config.py`) untuk uji alur tanpa kamera/OCR
- Dependency: `sim/requirements-anpr.txt` (opencv, numpy, paddlepaddle, paddleocr 2.8.1)
- Firmware ESP32 **tidak diubah** — tetap `openGate()` via serial `O`
- Night-operation: dicatat untuk kamera IR/RTSP di gate asli (docs/anpr.md)
- Test otomatis: allow (kirim `O`) & deny (tidak kirim) — PASS

### 2026-09-09 — Refactor Modular (Kode Per Komponen)
- Kode single-file `main.cpp` (~470 baris) dipecah menjadi **folder per komponen** di `lib/` supaya mudah dicari saat ada error & mudah dikelola:
  - `lib/config` → semua pin & konstanta (`config.h`)
  - `lib/ultrasonic` → kelas `USSensor` (depan & exit)
  - `lib/rfid_reader` → bungkus `MFRC522` (init/master/auth/version)
  - `lib/gate_controller` → state machine + gerak servo + logika pass
  - `lib/status_report` → baris display 2x16 + protokol `ST|...` ke GUI
- `src/main.cpp` kini hanya **orkestrasi** (setup + loop + perintah serial)
- Family nama fungsi lama → baru: `updateMotion()`→`gate.loopMotion()`, `updateDist()/updateExit()`→`gate.front.update()`/`gate.exit.update()`, `updateExit()`+keadaan pass→`gate.updatePass()`
- Konstanta globals `posClosed`/`posOpen` → `POS_CLOSED`/`POS_OPEN` (di `config.h`, sama nilainya: 105/30)
- Build clean (0 warning), upload OK, gerak non-blocking terverifikasi (Z→OPEN 30, X→CLOSED 105) dan ST tetap streaming

### 2026-09-09 — Sensor Exit HC-SR04 #2 (Kendaraan Sudah Lewat)
**Kode:**
- Tambah HC-SR04 kedua: TRIG=`GPIO32`, ECHO=`GPIO33` → deteksi kendaraan yang **sudah lewat gerbang**
- Logika pass-through: `passSeen` (kendaraan masuk area exit) → lalu area exit kosong → `passCleared` → gate **menutup lebih cepat** (tanpa menunggu 10 detik), selama area depan sudah kosong
- Refactor dua sensor jadi kelas `USSensor` (smoothing + debounce simetris `NEAR_COUNT=3`, filter badCount)
- Kedua sensor dibaca berurutan dalam 1 tick → hindari crosstalk
- Auto-close 10 detik tetap jadi **fallback** jika sensor exit tidak mendeteksi lewatan
- Pesan status baru: `VEHICLE PASSED!` (row2 GUI) + log `> Vehicle passed - close armed`
- Leading `pulseIn` timeout diturunkan 80ms → 40ms agar loop tidak tersendat

**Hardware:**
- HC-SR04 #2 → VCC/GND 3.3V, TRIG→GPIO32, ECHO→GPIO33 (pojok header, jauh dari servo & RFID agar tidak tabrakan/noise)

### 2026-09-09 — Audit & Refactor Non-Blocking (Smooth + Minim Error)
**Bug yang diperbaiki:**
- Gerak servo memakai `delay()` blocking → selama buka/tutup, sensor, tombol, serial, dan GUI **membeku**; deteksi halangan saat menutup memakai jarak basi → tidak pernah berfungsi benar
- `currentPos` init 90 ≠ `posClosed` 105
- Satu baca sensor invalid langsung menghapus `vehicleNear` (flicker)
- UID RFID >4-byte terpotong (buffer 7 hex)
- Pesan ST boot hardcode `90` (seharusnya 105)

**Perubahan:**
- `updateMotion()` non-blocking (tick 15ms) — status GUI live selama gerak, deteksi halangan pakai jarak segar, `openGate()` bisa membalik arah tengah menutup
- `vehicleNear` tidak langsung hilang karena 1 noise → butuh 2 baca invalid berurutan
- Anti-runaway: `X`/`Z` saat sudah di posisi tujuan → transisi langsung, tidak melewati ujung
- Bersihkan variabel tak terpakai (`rawDist`, `lastRfidMs` global, `moveTo`)

---

### 2026-09-08 — Simulasi Laptop (GUI pengganti LCD)
- Tambah `sim/gate_sim.py` — port penuh logika `main.cpp` ke Python + **tkinter**, berjalan 100% di laptop tanpa hardware
- GUI menggantikan **LCD 16x2** (panel LCD juga dirender di GUI) dan **tanpa button TUTUP** (penutupan via auto-close saja)
- Isi simulasi: servo/SM (CLOSED/OPENING/OPEN/CLOSING), RFID RC522 (kartu master/asing), HC-SR04 (jarak via slider), auto-close, proteksi halangan, serial log
- Jalankan: `python3.11 sim/gate_sim.py` (python3.11 wajib — punya tkinter)
- Cek logika: `python3.11 sim/gate_sim.py --selftest` (14 test, ALL PASS)
- `main.cpp` TIDAK diubah — tetap menargetkan hardware fisik (LCD + button TUTUP)

---

### 2026-09-08 — RFID RC522 (Ganti Simulasi → RFID Sungguhan)
**Kode:**
- Tambah library `MFRC522` di `platformio.ini`
- Inisialisasi RC522 via SPI bit-bang di pin aman (`SCK=15, MISO=16, MOSI=17, SS=25, RST=27`)
- Kartu pertama yang discan saat boot = **MASTER** (tersimpan di RAM)
- Kartu yang cocok → gate terbuka (`ACCESS GRANTED`)
- Kartu tidak dikenal → ditolak (`UNAUTHORIZED`) + log serial
- Button BUKA (GPIO4) dipertahankan sebagai **cadangan** manual

**Hardware:**
- Tambah RFID RC522 → VCC/GND 3.3V, SDA→GPIO25, SCK→GPIO15, MOSI→GPIO17, MISO→GPIO16, RST→GPIO27
- Pin SPI tidak pakai default (18/19/23) karena 18 sudah dipakai servo → pakai bit-bang custom

---

### 2026-09-07 — LCD 16x2 I2C & Perbaikan Logika Button
**Kode:**
- Tambah library `LiquidCrystal_I2C` di `platformio.ini`
- (Akan) tampilkan status gate di LCD: `CLOSED` / `OPEN`

**Hardware:**
- Tambah LCD 16x2 I2C → SDA `GPIO21`, SCL `GPIO22`

**Bug fixes:**
- Perbaikan logika button:
  - BUKA (GPIO4): aktif-HIGH (idle `0`, ditekan `1`)
  - TUTUP (GPIO5): aktif-LOW (idle `1`, ditekan `0`)
- Tambah debounce (50ms) + edge detection → tiap tekan 1 aksi, mencegah looping

---

### 2026-09-07 — Diagnosa Logika Button
**Proses:**
- Kode diagnostik mencetak nilai `BTN_OPEN` & `BTN_CLOSE` tiap 500ms
- Hasil tes:
  | Button | Idle | Ditekan |
  |--------|------|---------|
  | BUKA | 0 | 1 |
  | TUTUP | 1 | 0 |
- Terbukti kedua button punya logika berbeda → kode lama (baca keduanya HIGH=ditekan) tidak valid

**Masalah teratasi:** gate tidak lagi looping.

---

### 2026-09-07 — Wiring Breadboard
- Dokumentasi wiring lengkap pindah ke layout breadboard
- Rel daya: kiri `3.3V` (button, LCD), kanan `5V` (servo), `GND` bersama
- Ditambahkan di `docs/wiring.md`

---

### 2026-09-07 — Auto-Close Timer (Tahap 2)
- Gate menutup otomatis setelah `AUTO_CLOSE_MS` (10 detik) terbuka
- Refactor state machine: `CLOSED`, `OPENING`, `OPEN`, `CLOSING`
- Gerakan servo dipisah ke fungsi `openGate()` / `closeGate()`

---

### 2026-09-07 — Test Servo (Tahap 1)
- Inisialisasi project PlatformIO untuk ESP32 DOIT DevKit V1
- Kode dasar: servo `GPIO18`, button BUKA `GPIO4`, button TUTUP `GPIO5`
- Library: `ESP32Servo`

## Status Saat Ini

**Chip:** ESP32 DOIT DevKit V1
**Framework:** Arduino (PlatformIO)

| Fungsi | GPIO | Logika |
|--------|------|--------|
| Servo | 18 | PWM (CLOSED=105°, OPEN=30°) |
| Button BUKA (cadangan) | 4 | aktif-HIGH |
| HC-SR04 #1 (depan) TRIG/ECHO | 13/14 | deteksi kendaraan dekat + halangan |
| HC-SR04 #2 (exit) TRIG/ECHO | 32/33 | deteksi kendaraan sudah lewat |
| RFID SCK/MISO/MOSI | 15/16/17 | SPI bit-bang (dimask, menunggu modul) |
| RFID SS / RST | 25 / 27 | Chip select / reset (dimask) |
| Auto-close | - | 10 detik (fallback) + tutup cepat via sensor exit |
| Status | - | Serial `ST|...` tiap 300ms → GUI laptop |

**Tahap berikutnya (opsional):**
- [ ] Limit switch (deteksi posisi gate)
- [x] RFID sungguhan (RC522) ✓
- [ ] Simpan master UID ke EEPROM/NVS agar tidak kehilangan saat reboot
- [ ] Buzzer / LED indikator
- [ ] Kontrol WiFi / Web server