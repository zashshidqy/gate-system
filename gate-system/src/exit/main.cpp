#include <Arduino.h>
#include <Preferences.h>
#include "config.h"
#include "Ultrasonic.h"
#include "RfidReader.h"
#include "GateController.h"
#include "StatusReport.h"
#include "DFPlayer.h"

// ============================================================
//  MAIN — UNIT EXIT (gerbang keluar)
//  Logika di lib/ per komponen.
//
//  Khusus EXIT:
//   - Tanpa sensor approach; hanya sensor pass (GPIO 32/33).
//   - Gate selalu standby TERTUTUP.
//   - Buka langsung dari tap RFID / button / serial 'O'
//     (tanpa syarat "kendaraan dekat").
//   - Tutup kembali setelah kendaraan lewat (passCleared) atau perintah 'C'.
//     TANPA auto-close — gate boleh lama terbuka.
// ============================================================

GateController gate;
RfidReader rfid;
StatusReport ui;
DFPlayer audio;

unsigned long authUntilMs = 0;
bool authResult = false;
char lastAuth = '-';          // 'G'=granted 'D'=denied 'A'=jadi master
bool authPending = false;     // selalu false di EXIT (tidak ada tunggu kendaraan)

void sensorDiag() {
  Serial.printf("> [diag] Sensor PASS EXIT — scale=%.3f\n", gate.exit.getScale());
  Serial.println("> [diag] raw echo + jarak — 8 baca tiap 400ms, letakkan objek di depan sensor:");
  for (int i = 0; i < 8; i++) {
    gate.exit.update();
    Serial.printf("> [diag] P: raw=%uus cm=%d near=%d\n",
                  gate.exit.rawUs(), (int)gate.exit.getCm(), gate.exit.isNear() ? 1 : 0);
    delay(400);
  }
  Serial.println("> [diag] Selesai — 0us/raw = sensor tidak membalas echo (cek wiring TRIG/ECHO).");
}

void calibrateSensor(USSensor& s, const char* name, const char* key, int knownCm) {
  Serial.printf("> [kal] %s: PASTIKAN objek tepat %dcm dari sensor — mengukur 10 sampel...\n", name, knownCm);
  float sum = 0;
  int n = 0;
  for (int i = 0; i < 10; i++) {
    s.update();
    float cm = s.getCm();
    if (cm >= 2) { sum += cm; n++; }
    delay(200);
  }
  float avg = (n > 0) ? (sum / n) : -1;
  if (avg < 2) {
    Serial.println("> [kal] GAGAL — tidak ada pembacaan valid (cek wiring / objek terlalu jauh).");
    return;
  }
  float scale = (float)knownCm / avg;
  if (scale < 0.5f) scale = 0.5f;
  if (scale > 2.0f) scale = 2.0f;
  s.setScale(scale);
  Preferences prefs;
  prefs.begin("hcsr", false);
  prefs.putFloat(key, scale);
  prefs.end();
  Serial.printf("> [kal] %s: rata2=%.1fcm, scale=%.3f -> sekarang terbaca %.1fcm. Tersimpan.\n",
                name, avg, scale, avg * scale);
}

void handleSerialCommands() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == 'O') {
      gate.openGate();
    } else if (c == 'C') {
      gate.requestClose();
    } else if (c == 'R') {
      rfid.clearMasters();
      lastAuth = '-';
    } else if (c == 'A') {
      rfid.startAddMode();
    } else if (c == 'Q') {
      rfid.startDelMode();
    } else if (c == 'L') {
      rfid.listMasters();
    } else if (c == 'X') {
      gate.testToClosed();
    } else if (c == 'Z') {
      gate.testToOpen();
    } else if (c == 'V') {
      rfid.runAudit();
    } else if (c == 'T') {
      rfid.tapTest();
    } else if (c == 'H') {
      // Tombol TIKET (dari GUI) — unit EXIT buka langsung tanpa syarat kendaraan.
      Serial.println("> [tiket] Tombol Tiket EXIT — gerbang dibuka");
      audio.greet();
      gate.openGate();
    } else if (c == 'S') {
      sensorDiag();
    } else if (c == 'K') {
      int dist = 0;
      while (Serial.available()) {
        char d = Serial.peek();
        if (d >= '0' && d <= '9') { dist = dist * 10 + (d - '0'); Serial.read(); }
        else break;
      }
      if (dist <= 0) {
        Serial.println("> [kal] Format: K<jarak> PASS (cm). Contoh: K80");
      } else {
        calibrateSensor(gate.exit, "PASS", "pass_scale", dist);
      }
    }
  }
}

void setup() {
  Serial.begin(115200);
  Serial.printf("> UNIT: EXIT\n");
  Serial.printf("> CHIP: %s flash=%uKB psram=%s (%uKB)\n",
                ESP.getChipModel(), ESP.getFlashChipSize() / 1024,
                psramFound() ? "YES" : "no", ESP.getPsramSize() / 1024);

  gate.begin();
  gate.exit.begin(TRIG2_PIN, ECHO2_PIN);   // hanya sensor pass
  gate.exit.setNearCm(PASS_VEHICLE_CM);
  {
    Preferences prefs;
    prefs.begin("hcsr", true);
    gate.exit.setScale(prefs.getFloat("pass_scale", 1.0f));
    prefs.end();
    Serial.printf("> Kalibrasi PASS: x%.3f\n", gate.exit.getScale());
  }
  pinMode(BTN_OPEN, INPUT);

  audio.begin();
  rfid.begin();
#if RFID_ENABLED
  rfid.printInitReport();
  if (!rfid.isMasterSet()) {
    Serial.println("> Tempel kartu pertama sebagai master EXIT (atau kirim 'A' lalu tempel).");
  }
#else
  Serial.println("RFID masked - open via button (GPIO4)");
#endif

  Serial.println("Gate EXIT ready - CLOSED");
  ui.send(gate, rfid, authUntilMs, authResult, lastAuth, authPending, false);
}

void loop() {
  static bool prevOpen = false;
  static bool prevExitNear = false;
  static unsigned long lastDistMs = 0;
  static unsigned long lastMoveMs = 0;
  static unsigned long lastCheck = 0;
  static unsigned long lastStatusMs = 0;
#if RFID_ENABLED
  static unsigned long lastRfidMs = 0;
  static unsigned long rfidSkipUntil = 0;
#endif

  audio.update();

  // ---- sensor pass saja + log perubahan status ----
  if (millis() - lastDistMs >= DIST_INTERVAL_MS) {
    lastDistMs = millis();
    gate.exit.update();

    bool en = gate.exit.isNear();
    if (en != prevExitNear) {
      prevExitNear = en;
      Serial.printf("> [sensor] PASS %s (%dcm)\n", en ? "V:YES" : "V:NO", (int)gate.exit.getCm());
    }
    gate.updatePass();
  }

#if RFID_ENABLED
  if (millis() - lastRfidMs >= RFID_INTERVAL_MS) {
    lastRfidMs = millis();

    if (rfid.modeExpired()) {
      rfid.stopMode();
      Serial.println("> Waktu mode tambah/hapus master habis.");
    }

    if (millis() < rfidSkipUntil) {
      rfid.clearCooldown();
    } else {
      bool any = rfid.cardPresent();
      if (!any) {
        rfid.clearCooldown();
      }

      if (rfid.activeMode() == 1) {
        // MODE TAMBAH
        if (any && rfid.tryReadCard()) {
          if (rfid.seenRecently()) { rfid.haltCurrent(); }
          else {
            rfid.noteProcessedFromCurrent();
            bool added = rfid.addReadCardAsMaster();
            lastAuth = added ? 'A' : 'D';
            authUntilMs = millis() + RAUTH_DURATION_MS;
            rfid.stopMode();
            if (added) Serial.println("> Kartu berhasil ditambahkan ke daftar master.");
          }
        } else if (any) {
          rfidSkipUntil = millis() + RFID_FAIL_BACKOFF_MS;
          Serial.println("> [rfid] kartu terdeteksi tapi gagal dibaca — geser/ulang kartu");
        }
      } else if (rfid.activeMode() == 2) {
        // MODE HAPUS
        if (any && rfid.tryReadCard()) {
          if (rfid.seenRecently()) { rfid.haltCurrent(); }
          else {
            rfid.noteProcessedFromCurrent();
            bool removed = rfid.removeReadCardFromMasters();
            lastAuth = removed ? 'R' : 'D';
            authUntilMs = millis() + RAUTH_DURATION_MS;
            rfid.stopMode();
            if (removed) Serial.println("> Kartu dihapus dari daftar master.");
          }
        } else if (any) {
          rfidSkipUntil = millis() + RFID_FAIL_BACKOFF_MS;
          Serial.println("> [rfid] kartu terdeteksi tapi gagal dibaca — geser/ulang kartu");
        }
      } else if (!rfid.isMasterSet()) {
        // Belum ada kartu — kartu pertama otomatis jadi master
        if (any && rfid.tryReadCard()) {
          if (rfid.seenRecently()) { rfid.haltCurrent(); }
          else {
            rfid.noteProcessedFromCurrent();
            bool added = rfid.addReadCardAsMaster();
            lastAuth = added ? 'A' : 'D';
            authUntilMs = millis() + RAUTH_DURATION_MS;
            if (added) {
              Serial.println("> Kartu pertama DITETAPKAN sebagai master EXIT!");
              Serial.println("> (tambah kartu lain: kirim 'A' lalu tempel)");
            }
          }
        } else if (any) {
          rfidSkipUntil = millis() + RFID_FAIL_BACKOFF_MS;
          Serial.println("> [rfid] kartu terdeteksi tapi gagal dibaca — geser/ulang kartu");
        }
      } else if (any) {
        // Kartu terotorisasi → buka langsung (tanpa syarat kendaraan dekat).
        if (rfid.tryReadCard()) {
          if (rfid.seenRecently()) {
            rfid.haltCurrent();
          } else {
            rfid.noteProcessedFromCurrent();
            bool ok = rfid.currentCardAuthorized();
            if (ok) {
              authResult = true;
              lastAuth = 'G';
              authUntilMs = millis() + RAUTH_DURATION_MS;
              authPending = false;
              Serial.println("> [rfid] ACCEPTED — gerbang exit dibuka");
              audio.greet();
              gate.openGate();
            } else {
              authResult = false;
              lastAuth = 'D';
              authUntilMs = millis() + RAUTH_DURATION_MS;
              authPending = false;
              Serial.println("> [rfid] DENIED — kartu tidak terotorisasi");
              audio.deny();
            }
          }
        } else {
          rfidSkipUntil = millis() + RFID_FAIL_BACKOFF_MS;
          Serial.println("> [rfid] kartu terdeteksi tapi gagal dibaca — geser/ulang kartu");
        }
      }
    }
  }
#endif

  handleSerialCommands();

  if (millis() - lastMoveMs >= STEP_DELAY_MS) {
    lastMoveMs = millis();
    gate.loopMotion();
  }

  if (millis() - lastCheck >= DEBOUNCE_MS) {
    lastCheck = millis();
    bool openPressed = (digitalRead(BTN_OPEN) == HIGH);
    if (openPressed && !prevOpen) {
      Serial.println("> [btn] Tombol BUKA ditekan");
      gate.openGate();
    }
    prevOpen = openPressed;
  }

  // Saat terbuka: tutup hanya jika kendaraan SUDAH lewat (sensor pass passCleared)
  // ATAU diminta manual ('C' dari GUI). TANPA auto-close — gate boleh lama terbuka
  // selama kendaraan belum melewati sensor exit.
  // Tanpa sensor approach → tanpa cek isVehicleNear().
  if (gate.isOpen()) {
    if (!gate.closeRequested) {
      if (gate.passCleared) {
        gate.closeRequested = true;
        Serial.println("> Vehicle passed - close armed");
      }
    }
    if (gate.closeRequested) {
      gate.closeGate();
    }
  }

  if (millis() - lastStatusMs >= SERIAL_STATUS_MS) {
    lastStatusMs = millis();
    ui.send(gate, rfid, authUntilMs, authResult, lastAuth, authPending, false);
  }
}