# Konfigurasi Sistem (`lib/config/config.h`)

**Satu-satunya tempat** untuk mengubah pin & perilaku sistem tanpa menyentuh logika lain.

Sumber: `lib/config/config.h`

---

## 1. Pin

| Define | Nilai | Fungsi |
|--------|-------|--------|
| `SERVO_PIN` | `18` | GPIO servo |
| `BTN_OPEN` | `4` | Button BUKA (aktif-HIGH) |
| `TRIG_PIN` / `ECHO_PIN` | `13` / `14` | HC-SR04 #1 (depan) |
| `TRIG2_PIN` / `ECHO2_PIN` | `32` / `33` | HC-SR04 #2 (exit) |
| `RST_PIN` | `27` | RFID RST |
| `SS_PIN` | `25` | RFID chip select (SDA) |
| `RFID_SCK` / `RFID_MISO` / `RFID_MOSI` | `15` / `16` / `17` | SPI bit-bang RFID |

> Setelah mengubah pin, periksa dulu pin yang TIDAK dipakai di `docs/wiring.md` (bagian
> "Pin TIDAK RECOMMENDED") — mis. GPIO 6–11 (flash), 0/2/12 (boot), 34–39 (input-only).

---

## 2. Konstanta Sensor

| Define | Nilai | Efek |
|--------|-------|------|
| `VEHICLE_CM` | `30` | Jarak ≤ nilai ini dianggap "kendaraan dekat" (kedua sensor). **Syarat buka gate.** |
| `MAX_VALID_CM` | `60` | Baca di atas ini (atau < 2cm) dianggap noise → dibuang (`-1`) |
| `NEAR_COUNT` | `3` | Jumlah baca berurutan dekat/jauh sebelum status `near` berubah (debounce) |
| `OBSTACLE_CM` | `15` | Selama menutup, jarak depan `<` nilai ini → `OBSTACLE! Reopen` |

**Cara tuning `VEHICLE_CM`:** ukur jarak kendaraan berhenti yang realistis di titik gerbang,
tambahkan margin ~5cm. Terlalu besar = gate bisa hilang kesempatan karena objek lain dianggap
kendaraan; terlalu kecil = kendaraan berhenti terlalu dekat/jauh sehingga `V:YES` tidak muncul.

---

## 3. Konstanta Timing

| Define | Nilai | Efek |
|--------|-------|------|
| `AUTO_CLOSE_MS` | `10000` | Fallback: gate otomatis siap tutup 10s setelah terbuka penuh |
| `STEP_DELAY_MS` | `15` | Interval per-step gerak servo (non-blocking) |
| `DEBOUNCE_MS` | `50` | Interval sampling button |
| `DIST_INTERVAL_MS` | `150` | Interval pembacaan sensor depan+exit |
| `SERIAL_STATUS_MS` | `300` | Interval kirim `ST|...` ke GUI |
| `MSG_DURATION_MS` | `2000` | Lama pesan `NO VEHICLE!` ditampilkan |
| `RAUTH_DURATION_MS` | `2500` | Lama pesan hasil auth RFID (`ACCESS GRANTED`/`UNAUTHORIZED`) |
| `SMOOTH_SAMPLES` | `5` | Jumlah sampel rata-rata jarak |
| `RFID_INTERVAL_MS` | `100` | Interval scan kartu RFID di `loop()` |

**Perhatian `STEP_DELAY_MS`:** terlalu kecil → servo bergerak kencang/bergetar dan loop sibuk;
terlalu besar → buka/tutup terasa lambat. 15ms (≈6°/tick dari 75° travel ≈ 0.5s) adalah nilai aman.

---

## 4. Kontrol Fitur

```cpp
#define RFID_ENABLED 1   // 1 = aktif, 0 = mask (gate buka via tombol/serial)
```

| Nilai | Perilaku |
|-------|----------|
| `1` | `RfidReader::begin()` menginisialisasi SPI + RC522, cek `chip version`, scan kartu MASTER |
| `0` | SPI/RFID tidak diinisialisasi; boot mencetak `RFID masked - open via button (GPIO4)` |

> Status RFID saat ini: modul **belum merespons** (`0x0`). Lihat [troubleshooting.md](troubleshooting.md)
> bagian RFID sebelum menyetel nilai ini.

---

## 5. Posisi Servo

| Define | Nilai | Keterangan |
|--------|-------|------------|
| `POS_CLOSED` | `105` | Sudut saat gate tertutup |
| `POS_OPEN` | `30` | Sudut saat gate terbuka penuh |

> Sesuaikan dengan **arah fisik** servo & gate. Arah pergerakan (membuka bisa naik/turun derajat)
> mengikuti tanda perbandingan `POS_OPEN > currentPos` di `GateController::loopMotion()`.

---

## 6. Ringkasan Alur Ubah Nilai

1. Edit `lib/config/config.h`.
2. Build & upload: `pio run -t upload --upload-port /dev/ttyUSB0` (tutup GUI serial dulu).
3. Verifikasi lewat `ST|...` (monitor / GUI).