# Verifikasi & Pengujian Sistem

Prosedur untuk membuktikan tiap bagian bekerja. Urutan dari yang paling dasar.

---

## 0. Persiapan

- Tutup GUI serial saat mau upload (port dipakai): `fuser -k /dev/ttyUSB0` bila perlu.
- Upload terbaru:
  ```bash
  pio run -t upload --upload-port /dev/ttyUSB0
  ```
- Monitor:
  ```bash
  pio device monitor -p /dev/ttyUSB0 -b 115200
  ```

Kriteria boot OK (satu menit):
```
> CHIP: ESP32-D0WD-V3 ...
Gate ready - CLOSED
ST|CLOSED|105|-1|0|Gate: CLOSED    |V:NO  ---|----|-1
```

---

## 1. Uji Servo (non-blocking)

Kirim `Z` → gate bergerak ke OPEN (pos 30°), kirim `X` → kembali CLOSED (pos 105°).

```
kirim Z: ST|OPENING|86 → 66 → 51 → 37 → ST|OPEN|30
kirim X: ST|CLOSING|... → ST|CLOSED|105
```

**Cek:** posisi bergerak **bertahap** (beberapa frame berbeda), dan `ST|...` tetap terkirim
setiap 300ms selama bergerak (bukti non-blocking).

---

## 2. Uji Sensor Depan (HC-SR04 #1)

Dari monitor/GUI amati field `<dist>` & `<vehicle>`:

| Situasi | `<dist>` | `<vehicle>` |
|---------|----------|-------------|
| Tidak ada objek ≤ 60cm | `-1` | `0` |
| Tangan/objek 10–30cm | ~jarak | `1` (setelah `NEAR_COUNT=3`) |
| Objek 31–60cm | ~jarak | masih `0` |

**Cek:** jarak naik-turun mengikuti objek; noise sesekali tidak mengganti `vehicle` mendadak
(debaounce `NEAR_COUNT`); objek lepas → `V:NO` setelah 3 baca.

---

## 3. Uji Buka-Tutup Lengkap (skenario utama)

1. Pastikan `V:YES` (taruh objek ≤ 30cm depan sensor depan).
2. Tekan button BUKA / kirim `O` / scan kartu master.
3. Amati: `OPENING → OPEN`, pos ≅ 30°.
4. Gerakkan objek ke area **sensor exit** (sensor exit `near`) lalu jauhkan →
   log `> Vehicle passed - close armed` → tutup mulai saat depan kosong.
5. Jika tidak ada lewatan → `> Auto-close armed` setelah 10s → tutup.

**Cek wajib (safety):**
- Kiraan gate terbuka & kendaraan masih di depan (`V:YES`) → gate **tidak menutup**.
- Saat menutup, halangi gerbang (< 15cm) → `> OBSTACLE! Reopen` → buka lagi.
- Kirim `O` saat `CLOSING` → arah balik ke `OPENING`.

---

## 4. Uji Button BUKA (GPIO4)

- Idle: `<dist>` normal, tidak ada efek.
- Tekan sekali: `> GATE OPEN` saat `V:YES`; `> NO VEHICLE - rejected` saat kosong.
- Tekan cepat berkali-kali: hanya **1 transisi per tekan** (debounce + edge detection).

---

## 5. Uji RFID (saat `RFID_ENABLED 1`)

### 5.1 Cek modul merespons
Setelah boot harus ada:
```
> RFID chip version: 0x92   (atau 0x3A)   ← berarti modul hidup
```
Jika `0x0` / `0xFF` → modul tidak merespons → ikuti [troubleshooting.md](troubleshooting.md) §RFID.

### 5.2 Uji master & auth
1. Tempel kartu → log `> Master card set: A4 B3 ...`, field `<master>` terisi hex.
2. Tempel kartu sama saat `V:YES` → `ACCESS GRANTED` + gate membuka.
3. Tempel kartu beda → `> UID: ...` + `> RFID UNAUTHORIZED`.
4. Perintah `R` → `<master>` kembali `----`.

---

## 6. Uji GUI Laptop

```bash
python3.11 sim/gate_serial_gui.py
```

- Pilih COM/ttyUSB0, Connect.
- Panel "Gate", LCD 16x2, timer "Tutup dalam" mengikuti frame `ST|...`.
- Tombol **Buka (via serial)** → kirim `O`; **Tutup Sekarang** → kirim `C`.

> Simulator murni (tanpa hardware): `python3.11 sim/gate_sim.py --selftest` (semua test harus ALL PASS).

### 6.1 Uji ANPR (kamera + OCR plat)

Mode simulasi (tanpa kamera/OCR, cocok untuk cek alur):
1. `sim/anpr/config.py` → `MOCK_ANPR = True`.
2. `data/plat_izin.json` memuat `B1234CD`.
3. Jalankan GUI, aktifkan **Aktif ANPR**, hubungkan ESP32, arahkan objek di depan sensor sampai `V:YES`.
4. Saat gate `CLOSED` + `V:YES` → dalam ≤6 dtk label tampil `IZIN (B1234CD) [mock]` dan gate membuka (log `>> O (via ANPR)`).

Uji mandiri tanpa GUI:
```bash
python3.11 -c "from sim.anpr.plate_service import AnprService; print(AnprService().attempt())"
```

Test kamera + OCR asli (setelah `pip install -r sim/requirements-anpr.txt`, `MOCK_ANPR=False`):
1. Posisikan plat di depan webcam, tekan **Scan Plat Sekarang** → harus tampil plat + score.
2. Uji plat terdaftar → `IZIN` → gate buka; plat tidak terdaftar → `TIDAK TERDAFTAR` (tidak buka).
3. Uji kesalahan OCR ringan (miring/gelap) → fuzzy match tetap cocok (lihat [anpr.md](anpr.md)).

---

## 7. Checklist Peluncuran

- [ ] Boot: `Gate ready - CLOSED`, ST normal
- [ ] `Z`/`X` gerak servo halus & non-blocking
- [ ] Sensor depan: `V:YES` saat ≤ 30cm, `V:NO` saat kosong
- [ ] Sensor exit: `passSeen → passCleared` → tutup cepat
- [ ] Auto-close 10s jalan saat tanpa lewatan
- [ ] Halangan saat menutup → `OBSTACLE! Reopen`
- [ ] ANPR: `V:YES` + gate `CLOSED` → plat terdaftar → gate buka sendiri
- [ ] ANPR: plat tak terdaftar → tidak membuka (cek label status)
- [ ] Gate tidak pernah menutup saat kendaraan masih dekat
- [ ] RFID (jika aktif): version chip OK, master & auth bekerja
- [ ] GUI terhubung & menampilkan status live