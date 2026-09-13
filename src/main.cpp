#include <Arduino.h>
#include "config.h"
#include "Ultrasonic.h"
#include "RfidReader.h"
#include "GateController.h"
#include "StatusReport.h"

// ============================================================
//  MAIN — hanya orkestrasi. Logika di lib/ per komponen:
//   - config            : pin & konstanta
//   - ultrasonic        : kelas USSensor (depan & exit)
//   - rfid_reader       : daftar kartu terotorisasi (multi-master, NVS)
//   - gate_controller   : state machine + gerak servo + logika pass
//   - status_report     : baris display + protokol ST ke GUI
// ============================================================

GateController gate;
RfidReader rfid;
StatusReport ui;

unsigned long authUntilMs = 0;
bool authResult = false;
char lastAuth = '-';          // 'G'=granted 'D'=denied 'A'=jadi master 'P'=tunggu kendaraan
bool authPending = false;     // kartu sah tapi belum ada kendaraan
unsigned long pendingUntilMs = 0;

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
    }
  }
}

void setup() {
  Serial.begin(115200);
  Serial.printf("> CHIP: %s flash=%uKB psram=%s (%uKB)\n",
                ESP.getChipModel(), ESP.getFlashChipSize() / 1024,
                psramFound() ? "YES" : "no", ESP.getPsramSize() / 1024);

  gate.begin();
  gate.front.begin(TRIG_PIN, ECHO_PIN);
  gate.exit.begin(TRIG2_PIN, ECHO2_PIN);
  pinMode(BTN_OPEN, INPUT);

  rfid.begin();
#if RFID_ENABLED
  rfid.printInitReport();
  if (!rfid.isMasterSet()) {
    Serial.println("> Tempel kartu pertama sebagai master (atau kirim 'A' lalu tempel).");
  }
#else
  Serial.println("RFID masked - open via button (GPIO4)");
#endif

  Serial.println("Gate ready - CLOSED");
  ui.send(gate, rfid, authUntilMs, authResult, lastAuth, authPending);
}

void loop() {
  static bool prevOpen = false;
  static bool prevFrontNear = false;
  static bool prevExitNear = false;
  static unsigned long lastDistMs = 0;
  static unsigned long lastMoveMs = 0;
  static unsigned long lastCheck = 0;
  static unsigned long lastStatusMs = 0;
#if RFID_ENABLED
  static unsigned long lastRfidMs = 0;
  static unsigned long rfidSkipUntil = 0;
#endif

  // ---- sensor + log perubahan status (depan & exit) ----
  if (millis() - lastDistMs >= DIST_INTERVAL_MS) {
    lastDistMs = millis();
    gate.front.update();
    gate.exit.update();   // dibaca berurutan setelah sensor depan (hindari crosstalk)

    bool fn = gate.front.isNear();
    if (fn != prevFrontNear) {
      prevFrontNear = fn;
      Serial.printf("> [sensor] ENTRY %s (%dcm)\n", fn ? "V:YES" : "V:NO", (int)gate.front.getCm());
    }
    bool en = gate.exit.isNear();
    if (en != prevExitNear) {
      prevExitNear = en;
      Serial.printf("> [sensor] EXIT %s (%dcm)\n", en ? "V:YES" : "V:NO", (int)gate.exit.getCm());
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
      // jeda singkat setelah baca gagal — hindari scan boros saat objek aneh
      rfid.clearCooldown();
    } else {
      bool any = rfid.cardPresent();
      if (!any) {
        rfid.clearCooldown();   // area kosong → tap berikutnya langsung diproses
      }

      if (rfid.activeMode() == 1) {
        // MODE TAMBAH — kartu berikutnya didaftarkan
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
        // MODE HAPUS — kartu berikutnya dihapus dari daftar
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
              Serial.println("> Kartu pertama DITETAPKAN sebagai master!");
              Serial.println("> (tambah kartu lain: kirim 'A' lalu tempel)");
            }
          }
        } else if (any) {
          rfidSkipUntil = millis() + RFID_FAIL_BACKOFF_MS;
          Serial.println("> [rfid] kartu terdeteksi tapi gagal dibaca — geser/ulang kartu");
        }
      } else if (any) {
        // Kartu terotorisasi? Kalau sah → wajib ada kendaraan (sensor ENTRY).
        if (rfid.tryReadCard()) {
          if (rfid.seenRecently()) {
            rfid.haltCurrent();
          } else {
            rfid.noteProcessedFromCurrent();
            bool ok = rfid.currentCardAuthorized();
            if (ok) {
              if (gate.isVehicleNear()) {
                authResult = true;
                lastAuth = 'G';
                authUntilMs = millis() + RAUTH_DURATION_MS;
                authPending = false;
                Serial.println("> [rfid] ACCEPTED — kendaraan terdeteksi, gerbang dibuka");
                gate.openGate();
              } else {
                authPending = true;
                pendingUntilMs = millis() + WAIT_VEHICLE_MS;
                lastAuth = 'P';
                authUntilMs = 0;
                authResult = false;
                Serial.println("> [rfid] ACCEPTED — MENUNGGU KENDARAAN (sensor entry)...");
              }
            } else {
              authResult = false;
              lastAuth = 'D';
              authUntilMs = millis() + RAUTH_DURATION_MS;
              authPending = false;
              Serial.println("> [rfid] DENIED — kartu tidak terotorisasi");
            }
          }
        } else {
          rfidSkipUntil = millis() + RFID_FAIL_BACKOFF_MS;
          Serial.println("> [rfid] kartu terdeteksi tapi gagal dibaca — geser/ulang kartu");
        }
      }
    }
  }

  // Resolusi tunggu-kendaraan: begitu sensor ENTRY V:YES → buka gerbang.
  if (authPending) {
    if (gate.isVehicleNear()) {
      authPending = false;
      authResult = true;
      lastAuth = 'G';
      authUntilMs = millis() + RAUTH_DURATION_MS;
      Serial.println("> [rfid] KENDARAAN DETEKSI — kartu sah, gerbang dibuka");
      gate.openGate();
    } else if (millis() >= pendingUntilMs) {
      authPending = false;
      authResult = false;
      lastAuth = 'D';
      authUntilMs = millis() + RAUTH_DURATION_MS;
      Serial.println("> [rfid] TAP TIMEOUT — tidak ada kendaraan, scan dibatalkan");
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

  // Saat terbuka: tutup jika diminta DAN kendaraan sudah lewat
  if (gate.isOpen()) {
    if (!gate.closeRequested) {
      if (millis() - gate.openSinceMs >= AUTO_CLOSE_MS) {
        gate.closeRequested = true;
        Serial.println("> Auto-close armed");
      } else if (gate.passCleared) {
        gate.closeRequested = true;
        Serial.println("> Vehicle passed - close armed");
      }
    }
    if (gate.closeRequested && !gate.isVehicleNear()) {
      gate.closeGate();
    }
  }

  if (millis() - lastStatusMs >= SERIAL_STATUS_MS) {
    lastStatusMs = millis();
    ui.send(gate, rfid, authUntilMs, authResult, lastAuth, authPending);
  }
}