# Troubleshooting Gate ESP32

Panduan menyelesaikan error: gejala → penyebab → solusi.

---

## 1. Upload Gagal / Port Terpakai

**Gejala:** `Could not open port /dev/ttyUSB0` saat `pio run -t upload`.

**Penyebab:** GUI serial / monitor masih membuka port.

**Solusi:**
```bash
fuser -k /dev/ttyUSB0     # tutup pemegang port
pio run -t upload --upload-port /dev/ttyUSB0
```

---

## 2. RFID `chip version: 0x0` / `0xFF` (modul bisu)

**Audit hardware vs software (perintah `V` di monitor serial):**

Kirim huruf `V` → firmware menjalankan `RfidReader::runAudit()` yang membaca `VersionReg`
lewat **3 jalur independen**: hardware SPI 4MHz, hardware SPI 250kHz, dan **bit-bang murni**
(hanya `digitalWrite/Read`, bebas dari driver SPI). Hasil disimpulkan otomatis.

| Hasil | Arti |
|-------|------|
| Ketiga jalur `0x92`/`0x91`/`0x3A` | Modul & software beres → check kartu/antena |
| Bit-bang `0x92` tapi SPI HAL `0x00` | **Bug software SPI** (lapor/dev bagian firmware) |
| Semua `0x00`/`0xFF` | **Masalah fisik 100%** (software sudah dibuktikan bersih) |

> Hasil terakhir (semua jalur `0x00`, `CommandReg` ikut `0x00` padahal pasca-reset harus `0x20`):
> modul **tidak men-drive MISO** → fault fisik, bukan software. GPIO juga sudah diuji sehat
> sebelumnya (GPIO16 dibenamkan HIGH → terbaca `1`).

**Periksa fisik (board mati/lepas USB):**

1. **Kontinuitas (multimeter, mode buzzer):** GPIO25→SDA, GPIO15→SCK, GPIO17→MOSI,
   GPIO16→MISO, GPIO27→RST. Urutan header klon sering beda dari silkscreen; default:
   `SDA – SCK – MOSI – MISO – IRQ – GND – RST – VCC`.
2. **Tegangan:** ESP32 nyala, ukur VCC–GND modul = **3.3V** (bukan 0V). Jangan 5V.
3. **Solder:** modul klon sering belum di-solder → VCC/GND "menempel" sehingga LED nyala
   tetapi pin sinyal tidak kontak — gejala persis `0x00` semua jalur.
4. **Uji independen:** modul di Arduino Uno + lib MFRC522. Tetap bisu → modul rusak (ganti).

**Cara aman menonaktifkan RFID sementara:**
```c
#define RFID_ENABLED 0      // lib/config/config.h
```

---

## 2b. RFID Chip OK Tapi Kartu Kadang Tidak Terbaca

**Gejala:** `version: 0x82`, antenna `AKTIF`, `ST|...|0x82|...` normal, tetapi saat di-tap
kartu kadang tidak merespons / tidak jadi master.

**PENTING — pemetaan status (enum MFRC522):** `0`=OK, `1`=error, `2`=collision,
`3`=**TIMEOUT** (tidak ada kartu merespons), `7`=CRC salah, `0xFF`=NACK.

> Revisi 2: versi sebelumnya salah menafsirkan `status=3` sebagai CRC-wrong. `status=3`
> = **timeout = normal ketika tidak ada kartu di area**. Hasil tes lanjutan: setelah kartu
> benar-benar di-tap, kartu terbaca (`UID B0 D9 02 55`) — modul sehat.

**Diagnosis (perintah `T` di monitor):** firmware mencetak status REQA mentah tiap 2 detik:

| Status | Arti |
|--------|------|
| `0` (OK) | Kartu menjawab → di area, siap dibaca |
| `3` (timeout) | Tidak ada kartu di area (normal) |
| `2` (collision) | ≥2 kartu / kartu + interferensi 13.56 MHz |
| `7` (CRC) | Data RX rusak → cek kristal/antena, jauhkan phone NFC |

**Jika kadang terbaca kadang tidak (intermiten):** kemungkinan besar tap terlalu cepat
(kartu hanya lewat sesaat), kartu lemah, atau ada maksimal–baca satu kali. Firmware sekarang
menangani dengan **retry baca (6×58ms) saat kartu terdeteksi**, jeda cooldown yang di-reset
otomatis saat area kosong, dan **backoff + pesan `kartu terdeteksi tapi gagal dibaca`** agar
kegagalan terlihat di log (bukan diam).

**Praktik terbaik saat men-tap:**
1. **Tempel & tahan ±0.5 detik** di tengah antenna (jangan lirih/sekejap), kemudian angkat.
2. **Jauhkan phone/reader NFC** ≥ 50cm selama scan (interferensi nyata tetap bisa bikin CRC).
3. Jangan biarkan kartu lain menempel di antenna saat menyetel/hapus master.
4. Coba kartu lain untuk membandingkan — kartu lemah (tag tipis/rusak) sering intermiten.
5. Periksa antenna coil & solder di sekitar kumparan TX1/TX2 modul.

---

## 3. Gate Tidak Mau Menutup

**Gejala:** `closeRequested` sudah `true` (`> Close requested` / `> Auto-close armed`) tapi
gate tetap `OPEN`.

**Penyebab paling umum:** `!isVehicleNear()` (area depan masih ada objek/kabel).
Cek `ST|...`: field `<vehicle>` = `1` & `<dist>` ≈ jarak statis.

**Solusi:**
- Bersihkan area ≤ 30cm di depan sensor depan (termasuk kabel/plastik yang menghalangi).
- Kalau memang selalu tertutup objek menjulang di depan sensor, angkat/kurangi jangkauan sensor
  depan atau turunkan `VEHICLE_CM` di `config.h`.

**Kasus teruji:** objek statis ±17cm di depan sensor depan → `V:YES` di semua posisi gate →
gate memang menolak menutup (bukan bug).

---

## 4. Gate Terbalik / Posisi Salah (Servo)

**Gejala:** `X`/`Z` gerak ke arah yang salah, atau `posOpen`/`posClosed` tidak sampai.

**Solusi:**
- Ubah `POS_CLOSED` / `POS_OPEN` di `lib/config/config.h` sesuai arah fisik servo.
- Arah pergerakan mengikuti perbandingan `POS_OPEN > currentPos` di
  `GateController::loopMotion()` — jika terbalik total, tukar nilai `POS_OPEN`/`POS_CLOSED`.

---

## 5. Sensor Depan Selalu `V:YES` / Selalu `V:NO`

| Gejala | Penyebab umum | Solusi |
|--------|---------------|--------|
| `V:YES` terus + dist kecil statis | Objek/cable di depan sensor | Bersihkan area; cek arah sensor |
| `V:NO` terus + `dist = -1` | TRIG/ECHO tertukar, atau sensor kena noise | Cek kabel 13/14; pastikan 3.3V |
| Dist meloncat-loncat / `-1` bergantian | Noise & objek > 60cm | Baca normal: `-1` jika kosong ±60cm |

**Cek sensor cepat (tanpa objek):**
- Angkat tangan 10–30cm di depan → dist ≈ jarak, `V:YES`.
- Jauhkan → dalam bbrp tick `V:NO`.

---

## 6. Servo Bergetar / Bergerak Tersendat

**Penyebab:** `STEP_DELAY_MS` terlalu kecil, atau servo kelebihan bobot tanpa power eksternal.

**Solusi:**
- Naikkan `STEP_DELAY_MS` (misal 20–25ms).
- Servo besar (MG996R) → power eksternal 5V + ground bersama.

---

## 7. GUI Tidak Terhubung

**Gejala:** GUI blank / tombol tidak responsif, atau tidak ada garis `ST|...`.

**Solusi:**
- Pakai **`python3.11`** (punya tkinter+pyserial) — `python3` biasa sering gagal.
- Pastikan tidak ada monitor lain yang membuka port.
- Cek kolom `<vehicle>`/`<row2>` muncul di monitor → berarti ESP32 OK.
- Hubungkan ulang / pilih port yang benar di dropdown.

---

## 8. Tombol BUKA Tidak Berfungsi

- Log `> NO VEHICLE - rejected` saat kosong? → **normal**, butuh `V:YES`.
- Sama sekali tidak ada log → cek kabel GPIO4 (aktif-HIGH: idle `0`, ditekan `1`).
- Tekan lama / ganda → debounce `DEBOUNCE_MS=50` + edge detection sudah menangani.

---

## 9. Boot Gagal / Tidak Ada Serial Sama Sekali

- Cek kabel USB & driver CH340 (`ls /dev/ttyUSB*`).
- Tekan **EN** (reset) di ESP32.
- Pastikan board tidak short (servo menarik arus besar dari pin 5V board).
- Log boot `> CHIP: ...` wajib muncul — jika tidak, masalah di power/board.