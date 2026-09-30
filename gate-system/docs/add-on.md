# Add-on

Semua fitur **sudah diimplementasikan** dan terverifikasi.

1. ✅ **Capture Saat Tap RFID** — saat kartu (RFID) terbaca:
   - Simulator: `gate_sim.py` menyediakan ID kartu asing + tombol "Tue Kartu".
   - GUI: kartu GRANTED → buka dialog "Input Plat" (pratinjau gambar, isian plat,
     arah ENTRY/EXIT) → Simpan/Lewati → tersimpan ke DB + folder `data/captures/`.
     Kartu DENIED → hanya bunyi deny (tidak dicatat).
   - Bahan gambar dari frame terakhir kamera ANPR (`anpr`), atau sensor exit di sim.

2. ✅ **Database (recommend ai)** — SQLite `data/gate.db` (modul `sim/passage_log.py`),
   tabel `passages` + gambar di `data/captures/`. Dicatat otomatis:
   - ANPR (AI/PaddleOCR) yang `allowed` → akses disimpan saat pelat terdeteksi.
   - RFID (lewat dialog input plat).
   - Panel "Database Akses" di GUI: daftar riwayat, tombol Muat Ulang & Buka Folder Gambar.

3. ✅ **Greeting sound** — buzzer di firmware (GPIO 2, LEDC ch 7):
   - Kartu sah + kendaraan terdeteksi → nada **greet** (buang-buang ceria).
   - Kartu asing → nada **deny** (rendah).
   - Simulator/GUI juga membunyikan greeting/deny lewat aplay/paplay/play (fallback bell).

4. ✅ **Gate boleh lama tanpa auto-close** — **`AUTO_CLOSE_MS` dihapus** dari firmware
   (entry & exit). Gate dibuka tetap terbuka selama kendaraan belum melewati **sensor
   exit**. Tutup hanya terjadi setelah: kendaraan lewat (`passCleared` / `VEHICLE PASSED!`)
   atau perintah manual `C` dari GUI.