# Hardware Gate ESP32

Daftar komponen (bill of materials), kebutuhan daya, dan ringkasan pin. Wiring detail:
[wiring.md](wiring.md).

---

## BOM (Bill of Materials)

| # | Komponen | Jumlah | Keterangan |
|---|----------|--------|------------|
| 1 | ESP32 DevKit (module DOIT V1 / WROOM-32, `ESP32-D0WD-V3`, flash 4MB, tanpa PSRAM) | 1 | MCU utama |
| 2 | Servo SG90 / MG996R | 1 | Aktuator buka/tutup gate |
| 3 | HC-SR04 (ultrasonic) | 2 | Sensor depan (kendaraan datang) & exit (kendaraan lewat) |
| 4 | Module button (VCC/GND/OUT) | 1 | Button BUKA (cadangan manual) |
| 5 | MFRC522 RC522 (RFID 13.56MHz) | 1 | Kartu berizin membuka gate (**sedang diperiksa**: belum merespons `0x0`) |
| 6 | Tag / kartu RFID (13.56MHz, mifare klasik) | 1+ | Kartu pertama saat boot = MASTER |
| 7 | Breadboard + kabel jumper | secukupnya | Wiring |
| 8 | Power supply eksternal 5V (opsional) | 1 | Hoseel servo besar (jika MG996R) |
| 9 | **Active buzzer 5V** (`HIGH` = bunyi) | 1 | Greeting/deny sound (GPIO 2) |

---

## Kebutuhan Daya

| Jalur | Tegangan | Pemakai |
|-------|----------|---------|
| **3.3V** (dari ESP32) | 3.3V | Button BUKA, HC-SR04 ×2, MFRC522 RC522 |
| **5V** (dari ESP32/eksternal) | 5V | Servo (SG90 bisa 5V dari board; MG996R → power eksternal) |
| **3.3V / 5V** | sesuai modul | Active buzzer (lihat spesifikasi; GPIO 2 aktif-HIGH) |
| **GND** | 0V | Bersama semua perangkat |

> **PENTING:**
> - RC522 & HC-SR04 **dilarang 5V** → komponen rusak (RC522) / ECHO 5V ke ESP32 tanpa
>   divider dapat merusak GPIO.
> - HC-SR04 diberi **3.3V** agar ECHO keluar ±3.3V → aman ke ESP32 tanpa resistor.
> - Jika servo besar (MG996R) menarik arus tinggi, gunakan **power eksternal 5V + ground
>   bersama** (bukan dari pin 5V board).

---

## Ringkasan Pin

| Fungsi | GPIO | Mode | Keterangan |
|--------|------|------|------------|
| Servo SIG | 18 | Output (LEDC/PWM) | Servo buka/tutup |
| Button BUKA | 4 | Input (pull internal OFF) | Aktif-HIGH saat ditekan |
| HC-SR04 #1 TRIG (depan) | 13 | Output | Trigger sensor depan |
| HC-SR04 #1 ECHO (depan) | 14 | Input | Echo sensor depan |
| HC-SR04 #2 TRIG (exit) | 32 | Output | Trigger sensor exit |
| HC-SR04 #2 ECHO (exit) | 33 | Input | Echo sensor exit |
| RFID SCK | 15 | SPI bit-bang | Clock RC522 |
| RFID MISO | 16 | SPI bit-bang | Data keluar reader |
| RFID MOSI | 17 | SPI bit-bang | Data masuk reader |
| RFID SS (SDA) | 25 | SPI bit-bang | Chip select |
| RFID RST | 27 | Output | Reset reader |
| RFID IRQ | — | — | Tidak dipakai (mode polling) |
| **Buzzer SIG** | **2** | Output (LEDC ch 7) | Greeting/deny; aktif-HIGH. GPIO 2 = juga LED onboard DOIT |
| GPIO 1 / 3 | TX0 / RX0 | — | USB-Serial (upload & monitor) |

---

## Jalur Daya / Ground di Breadboard

```
ESP32 ─────────────────────── breadboard
  3.3V ──rel (+) kiri ──→ VCC button + VCC HC-SR04×2 + VCC RC522
  5V   ──rel (+) kanan──→ VCC servo (atau power eksternal)
  GND  ──rel (-) ───────→ GND semua modul + servo
```

---

## Catatan Modul RFID (RC522)

- Pin header modul umumnya: `SDA – SCK – MOSI – MISO – IRQ – GND – RST – VCC`.
  **Banyak klon urutan berbeda dari silkscreen** — verifikasi dengan multimeter.
- Modul **harus di-solder** (header/jumper ditusuk tanpa solder sering kontak lemah:
  LED nyala tapi semua sinyal bisu).
- IRQ tidak wajib untuk mode polling kita.

Lebih lanjut: [troubleshooting.md](troubleshooting.md) (bagian RFID).