# Protokol Serial (ESP32 ↔ GUI)

Komunikasi antara ESP32 dan laptop (GUI `sim/gate_serial_gui.py` atau terminal) lewat USB-serial
baud **115200**, format ASCII, baris dipisah `\n`.

---

## 1. Status ESP32 → PC (`ST|...`)

Dikirim **tiap 300ms** (`SERIAL_STATUS_MS`).

```
ST|<state>|<pos>|<dist>|<vehicle>|<row1>|<row2>|<masters>|<exitCm>|<rfidVer>|<lastUid>|<lastAuth>|<count>
```

| #  | Field       | Contoh       | Tipe  | Keterangan |
|----|-------------|--------------|-------|------------|
| 1  | `ST`        | `ST`         | const | Penanda baris status |
| 2  | `<state>`   | `OPEN`       | str   | `CLOSED` / `OPENING` / `OPEN` / `CLOSING` |
| 3  | `<pos>`     | `30`         | int   | Posisi servo saat ini (derajat) |
| 4  | `<dist>`    | `28`         | int   | Jarak sensor **depan** (cm); `-1` = tidak valid/noise |
| 5  | `<vehicle>` | `1`          | int   | `1` = kendaraan dekat (≤ `VEHICLE_CM`), `0` = kosong |
| 6  | `<row1>`    | `Gate: OPEN      ` | str | Baris 1 tampilan (16 karakter) |
| 7  | `<row2>`    | `V:YES  28cm `    | str | Baris 2 tampilan (16 karakter) |
| 8  | `<masters>` | `A4B3...,D5E6...` | hex   | Daftar UID kartu terotorisasi (dipisah koma); `-` = belum ada |
| 9  | `<exitCm>`  | `36`          | int   | Jarak sensor **exit** (cm); `-1` = tidak valid |
| 10 | `<rfidVer>` | `0x92`        | hex   | Versi chip RC522 dari `VersionReg`; `0x00`/`0xFF` = modul tidak merespons |
| 11 | `<lastUid>` | `A4B3C2D1`    | hex   | UID kartu terakhir yang terbaca; `-` = belum ada |
| 12 | `<lastAuth>`| `G`           | char  | Hasil kartu terakhir: `G`=granted, `D`=denied, `A`=jadi master, `P`=menunggu kendaraan, `-`=belum |
| 13 | `<count>`   | `2`           | int   | Jumlah kartu terotorisasi |

**Contoh baris lengkap:**
```
ST|OPEN|30|28|1|Gate: OPEN      |V:YES  28cm |A4B3C2D1,D5E6F7A8|36|0x82|A4B3C2D1|G|2
ST|CLOSED|105|-1|0|Gate: CLOSED    |V:NO  ---|-|-1|0x00|-|-|0
```

### Makna `<row2>` (prioritas pesan)

| Pesan | Kondisi |
|-------|---------|
| `NO VEHICLE!` | Buka ditolak karena area depan kosong (`rejectUntilMs`) |
| `TUNGGU KENDARAAN MASUK` | Kartu sah tapi sensor ENTRY belum mendeteksi kendaraan (`authPending`) |
| `ACCESS GRANTED` / `UNAUTHORIZED` | Hasil RFID (2.5 detik) |
| `VEHICLE PASSED!` | Gate terbuka, kendaraan sudah lewat, siap tutup |
| `WAIT VEHICLE!` | Tutup diminta tapi kendaraan masih dekat |
| `OPENING...` / `CLOSING...` | Gate sedang bergerak |
| `V:YES 12cm` / `V:NO ---` | Status deteksi default |

> **Tanpa auto-close:** gate yang sudah terbuka (`OPEN`) tetap terbuka selama yang diminta —
> tutup hanya terjadi setelah kendaraan melewati sensor exit (`VEHICLE PASSED!` → `passCleared`)
> atau perintah `C` (close) dikirim dari GUI.

---

## 2. Perintah PC → ESP32

Satu karakter per perintah (tanpa `\n` wajib, tanpa balasan di luar log).

| Perintah | Fungsi | Syarat / Efek |
|----------|--------|----------------|
| `O` | Buka gate | Hanya jalan jika kendaraan dekat (`V:YES`). Log `> NO VEHICLE - rejected` jika tidak ada |
| `C` | Minta tutup | Gate harus `OPEN`. Menyetel `closeRequested` — eksekusi setelah kendaraan lewat & area depan kosong |
| `A` | Mode tambah master | 15 detik: kartu berikutnya yang disentuh didaftarkan sebagai master (persisten NVS) |
| `Q` | Mode hapus master | 15 detik: kartu berikutnya yang disentuh dihapus dari daftar master |
| `L` | Daftar master | Mencetak semua UID kartu terotorisasi |
| `R` | Hapus semua master | Menghapus seluruh daftar kartu dari RAM + NVS |
| `X` | Tes → CLOSED | Pindah state `CLOSING` → posisi `105°` (tanpa syarat) |
| `Z` | Tes → OPEN | Pindah state `OPENING` → posisi `30°` (tanpa syarat) |

> `X`/`Z` ada untuk **uji gerak servo** tanpa kendaraan. `C` baru benar-benar menutup saat
> `closeRequested && !isVehicleNear()`.

---

## 3. Log Debug (semua diawali `>`)

| Output | Arti |
|--------|------|
| `> CHIP: ESP32-D0WD-V3 flash=4096KB psram=no (0KB)` | Info chip saat boot |
| `> RFID chip version: 0x..` | Versi chip RC522 (`0x92`/`0x3A` = OK; `0x00`/`0xFF` = tidak merespons) |
| `> Master ditambahkan: A4 B3 ...` | Kartu baru masuk daftar terotorisasi |
| `> Master dihapus: A4 B3 ...` | Kartu keluar dari daftar terotorisasi |
| `> Semua kartu master dihapus.` | Perintah `R` |
| `> MODE TAMBAH/HAPUS MASTER aktif...` | Perintah `A` / `Q` (jendela 15 detik) |
| `> UID: A4 B3 ...` | UID kartu yang baru dibaca |
| `> [sensor] ENTRY V:YES (12cm)` / `EXIT...` | Perubahan status sensor depan/exit |
| `> [rfid] ACCEPTED — MENUNGGU KENDARAAN...` | Kartu sah, sensor ENTRY belum V:YES → pending |
| `> [rfid] KENDARAAN DETEKSI — kartu sah, gerbang dibuka` | Pending terpenuhi → buka |
| `> [rfid] TAP TIMEOUT ...` | Kartu sah tapi 30s tanpa kendaraan → batal |
| `> [rfid] DENIED — kartu tidak terotorisasi` | Kartu tidak ada di daftar |
| `> GATE OPEN` | Sequence buka dimulai |
| `> Vehicle passed - close armed` | Sensor exit → kendaraan lewat → siap tutup |
| `> GATE CLOSING` / `> GATE CLOSED` | Sequence tutup |
| `> OBSTACLE! Reopen` | Halangan `< 15cm` saat menutup → buka kembali |
| `> NO VEHICLE - rejected` | Buka ditolak |
| `> Close requested (GUI)` | Perintah `C` diterima |

---

## 4. Cara Uji dengan Terminal

```bash
pio device monitor -p /dev/ttyUSB0 -b 115200
# lalu kirim: Z  (lihat ST berubah OPENING → OPEN, pos 30)
#             X  (lihat ST berubah CLOSING → CLOSED, pos 105)
```

Atau dengan Python:
```python
import serial, time
s = serial.Serial('/dev/ttyUSB0', 115200)
s.write(b'O')          # buka (perlu kendaraan dekat)
while True:
    line = s.readline().decode().strip()
    if line.startswith('ST|'): print(line)
```