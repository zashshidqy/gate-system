# ANPR — Automatic Number Plate Recognition (Pembuka Alternatif)

RFID RC522 (kartu master) adalah otorisasi utama (modul sedang diperbaiki secara fisik). ANPR
menjadi **pembuka alternatif**: kamera + pembacaan **plat nomor**. Plat yang terdaftar di
whitelist → sistem menyuruh ESP32 membuka gate (perintah `O`, jalur yang sama dengan tombol GUI).

```
[Kamera (webcam / nanti CCTV RTSP)]   →  [Laptop: anpr module] → serial 'O' → ESP32 openGate()
                                          OCR plat → cek data/plat_izin.json          (V:YES tetap dicek ESP32)
```

**Firmware ESP32 tidak diubah sama sekali (RFID & ANPR jalan paralel).**

---

## Arsitektur Modul (`sim/anpr/`)

| File | Fungsi |
|------|--------|
| `config.py` | Sumber kamera, cooldown, ambang score, regex plat, mode MOCK |
| `plate_db.py` | Whitelist plat (`data/plat_izin.json`), normalisasi, fuzzy match (O↔0, I↔1, dsb) |
| `camera_source.py` | Buka sumber kamera (index webcam / URL RTSP), ambil 1 frame |
| `plate_ocr.py` | Bungkus PaddleOCR (lazy-load), ambil kandidat plat terbaik + score |
| `plate_service.py` | Orkestrasi: tangkap frame → OCR → cek db → hasil izin/tolak |

**Alur auto-trigger (di GUI `gate_serial_gui.py`):**
1. GUI membaca frame `ST|...` dari ESP32.
2. Saat `state=CLOSED` **dan** `vehicle=1` (kendaraan menunggu di gerbang) → scan plat.
3. Cooldown `AUTO_COOLDOWN_S` (6 dtk) mencegah spam hasta.
4. Hasil OCR dicocokkan dengan `data/plat_izin.json` (dengan koreksi huruf-aneh).
5. Cocok → kirim `O` → ESP32 `openGate()` (tetap memeriksa `V:YES`). Beda → log, tidak buka.

---

## Instalasi Dependensi (sekali saja)

```bash
python3.11 -m pip install -r sim/requirements-anpr.txt
# opencv-python-headless, numpy, paddlepaddle, paddleocr==2.8.1
```

> Model PaddleOCR otomatis diunduh saat pertama kali scan (~200MB).

---

## Menjalankan

```bash
python3.11 sim/gate_serial_gui.py
```

Panel **"ANPR — Pengganti RFID (kamera)"** di bawah jendela:
- **Kamera (langsung)** — live video dari webcam; setelah scan muncul **kotak deteksi**
  + teks per segmen, dan **banner overlay** di video: `PLAT | skor% | IZIN/TIDAK TERDAFTAR`.
- **Aktif ANPR** — nyalakan agar auto-scan aktif.
- **Sumber** — index webcam (`0`, `1`, ...) atau URL RTSP untuk CCTV nanti.
- **Scan Plat Sekarang** — uji manual: proses frame terakhir, tampilkan kotak + hasil.
- Label status menampilkan: plat terbaca, score, dan `IZIN` / `TIDAK TERDAFTAR`.

### Cara kerja live + kotak
1. Thread preview membaca kamera terus-menerus (~30fps) dan menampilkan di panel.
2. Scan (auto saat `vehicle=1 & CLOSED`, atau tombol) memakai **frame terakhir** dari
   preview — tidak berebut kamera dengan loop live.
3. `PlateOCR` menyimpan kotak deteksi untuk semua teks yang ditemukan. Segmen yang
   membentuk plat (yang dipilih oleh `_best_plate`) digambar **hijau**, sisanya **kuning**.
4. Hasil scan (plat, skor, kotak) dipakai sebagai overlay pada video sampai scan berikutnya.

---

## Mode Simulasi (tanpa kamera/OCR)

Cocok untuk uji alur sebelum install dependensi / di laptop tanpa kamera:

```python
# sim/anpr/config.py
MOCK_ANPR = True       # ← aktifkan
MOCK_PLATE = "B1234CD" # plat yang "selalu terbaca" saat simulasi
```

Dengan `MOCK_ANPR=True`, saat `vehicle=1 & CLOSED` maka sistem otomatis "membaca" `B1234CD`;
jika plat itu ada di `data/plat_izin.json` → kirim `O`. Label panel menampilkan `[mock]`.

> Set `MOCK_ANPR = False` setelah dependensi terpasang.

---

## Daftar Plat Berizin

File: `data/plat_izin.json` (format list, otomatis dinormalisasi uppercase + tanpa spasi):

```json
[
  "B1234CD",
  "D1ABC",
  "KT123ZZ"
]
```

- Tambah/hapus manual lalu simpan; tidak perlu restart aplikasi (db dibaca ulang saat scan).
- Format plat Indonesia: `<1-2 huruf><1-4 angka><1-3 huruf>`. Format lain → tidak dianggap valid.
- **Fuzzy match:** kesalahan OCR umum (O↔0, I↔1, S↔5, B↔8, Z↔2) tetap cocok ke plat terdaftar.

---

## Konfigurasi (`sim/anpr/config.py`)

| Konfig | Default | Fungsi |
|--------|---------|--------|
| `CAMERA_SOURCE` | `"0"` | index webcam, atau `"rtsp://..."` untuk CCTV |
| `AUTO_COOLDOWN_S` | `6.0` | jeda antar auto-scan |
| `MANUAL_COOLDOWN_S` | `2.0` | jeda antar scan manual |
| `MIN_SCORE` | `0.60` | ambang kepercayaan OCR (di bawah ini dianggap ragu) |
| `MOCK_ANPR` / `MOCK_PLATE` | `True` / `"B1234CD"` | mode simulasi tanpa kamera |
| `PLATE_REGEX` | `^[A-Z]{1,2}-?\d{1,4}-?[A-Z]{1,3}$` | format plat yang diterima |
| `CHAR_CONFUSION` | O↔0 Q, I↔1 L T, ... | pasangan kesamaan karakter OCR |

---

## Pindah ke CCTV (Gate Asli) Nanti

1. Ganti `CAMERA_SOURCE` menjadi URL RTSP satu line.
2. Posisi kamera: tinggi ±2,5–3,5m, sudut 15–30° terhadap plat, jarak 1–3m, resolusi ≥ HD.
3. **Operasi malam:** perlu kamera IR/ekspose malam atau lampu IR — webcam biasa tidak akan
   membaca plat di gelap (software tidak berubah).
4. OCR tetap di laptop (gate asli perlu laptop/PC di pos security).

---

## Catatan Limitasi

- OCR terbukti jika cahaya cukup & plat terlihat jelas; `score` dibawah `MIN_SCORE` ditolak.
- Tidak ada anti-pengecoh: orang di gerbang tetap perlu `C`/auto-close; ANPR hanya **membuka**.
- Keamanan praktis: gunakan daftar plat + button/BUKA manual sebagai cadangan.