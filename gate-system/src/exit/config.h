#pragma once
#include <Arduino.h>

// ============================================================
//  CONFIG — UNIT EXIT (gerbang keluar)
//  Ubah nilai di sini bila perlu; jangan ubah di file lain.
//
//  Khusus EXIT:
//   - Hanya 1x HC-SR04 (pass) di GPIO 32/33. Tanpa sensor approach.
//   - RFID_TRIG/ECHO (13/14) tidak dipakai.
//   - Buka langsung dari tap RFID / button (tanpa syarat kendaraan dekat).
// ============================================================

// ---- Pin ----
#define SERVO_PIN 18
#define BTN_OPEN 4

// HC-SR04 #1 (approach) — TIDAK DIPAKAI di unit EXIT.
// Pin 13/14 dibiarkan kosong. Nilai tetap agar lib kompatibel.
#define TRIG_PIN 13
#define ECHO_PIN 14

// HC-SR04 #2 (pass — deteksi kendaraan sudah lewat)
#define TRIG2_PIN 32
#define ECHO2_PIN 33

// RFID RC522 (SPI custom pins)
#define RST_PIN 27
#define SS_PIN 25
#define RFID_SCK 15
#define RFID_MISO 16
#define RFID_MOSI 17

// ---- Sensor ----
#define VEHICLE_CM 50      // kendaraan "dekat" jika <= 50cm (approach — tdk dipakai EXIT)
#define PASS_VEHICLE_CM 80 // kendaraan "lewat" jika <= 80cm (sensor pass)
#define MAX_VALID_CM 200    // baca di atas ini = noise/jauh, anggap tidak ada objek
#define NEAR_COUNT 3       // butuh N baca berurutan dekat sebelum V:YES
#define OBSTACLE_CM 10     // halangan saat menutup (<10cm) — nonaktif tanpa approach

// ---- Timing ----
// TANPA AUTO_CLOSE_MS — gate boleh lama terbuka; tutup hanya setelah
// passCleared (kendaraan lewat) atau perintah 'C'.
#define STEP_DELAY_MS   10       // interval gerak servo per tick (non-blocking)
#define DEBOUNCE_MS     50       // interval cek button
#define DIST_INTERVAL_MS 150     // interval pembacaan sensor pass
#define SERIAL_STATUS_MS 300     // interval kirim status ST|... ke GUI
#define MSG_DURATION_MS 2000     // durasi pesan hasil auth
#define RAUTH_DURATION_MS 2500   // durasi pesan hasil auth RFID
#define SMOOTH_SAMPLES 5         // jumlah sampel rata-rata jarak
#define RFID_INTERVAL_MS 100     // interval scan kartu RFID
#define SERVO_STROKE_MS 2400     // durasi penuh gerak servo (ease-in/out, halus)
#define SERVO_US_MIN 544         // lebar pulsa servo utk 0° (SG90/MG996R)
#define SERVO_US_MAX 2400        // lebar pulsa servo utk 180°
#define SERVO_MAX_US_STEP 25     // max lompatan pulsa per tick (~2.4° @10ms) → halus

// ---- Kontrol ----
// 1 = RFID aktif; 0 = dimask (gate dibuka via tombol/serial)
#define RFID_ENABLED 0

// ---- Mode unit ----
// EXIT : 1x HC-SR04 (pass) saja; selalu standby tertutup, buka langsung via
// tap RFID/button (tanpa syarat kendaraan dekat), tutup via pass sensor.
#ifndef GATE_MODE_EXIT
#define GATE_MODE_EXIT 1
#endif

// ---- RFID multi-master (daftar kartu yang berhak buka gerbang) ----
#define MAX_MASTERS         8        // maksimal jumlah kartu terotorisasi
#define RFID_COOLDOWN_MS    2000UL   // kartu sama yg masih MENGINAP tak diproses ulang
#define WAIT_VEHICLE_MS     30000UL  // jendela tunggu kendaraan setelah kartu disetujui
#define RFID_MODE_WINDOW_MS 15000UL  // berapa lama mode tambah/hapus master aktif
#define RFID_READ_ATTEMPTS  6        // percobaan REQA+select saat kartu terdeteksi
#define RFID_READ_RETRY_MS  25       // jeda antar percobaan baca kartu (ms)
#define RFID_FAIL_BACKOFF_MS 1500UL  // jeda scan ulang setelah baca gagal (anti penuh)

// ---- Posisi servo ----
#define POS_CLOSED 120
#define POS_OPEN 30

// ---- DFPlayer Mini (menggantikan buzzer) ----
#define DFPLAYER_ENABLED 1
#define DFPLAYER_RX_PIN 19    // ESP32 RX <- DFPlayer TX (Serial2 remap)
#define DFPLAYER_TX_PIN 21    // ESP32 TX -> DFPlayer RX (Serial2 remap)
#define DFPLAYER_VOLUME 20    // 0-30, 20 aman & cukup keras untuk 8Ω 3W
#define DFPLAYER_GREET_TRACK 1  // mp3/0001.mp3
#define DFPLAYER_DENY_TRACK 2   // mp3/0002.mp3