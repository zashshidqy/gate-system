#include <Arduino.h>
#include <Preferences.h>
#include "config.h"
#include "Ultrasonic.h"
#include "RfidReader.h"
#include "GateController.h"
#include "StatusReport.h"
#include "DFPlayer.h"

// ============================================================
//  MAIN — UNIT ENTRY (gerbang masuk)
//  Logika di lib/ per komponen:
//   - config            : pin & konstanta (src/entry/config.h)
//   - ultrasonic        : kelas USSensor (approach & pass)
//   - rfid_reader       : daftar kartu terotorisasi (multi-master, NVS)
//   - gate_controller   : state machine + gerak servo + logika pass
//   - status_report     : baris display + protokol ST ke GUI
// ============================================================

GateController gate;
RfidReader rfid;
StatusReport ui;
DFPlayer audio;

unsigned long authUntilMs = 0;
bool authResult = false;
char lastAuth = '-';          // 'G'=granted 'D'=denied 'A'=jadi master 'P'=tunggu kendaraan 'V'=tunggu plat
bool authPending = false;     // kartu sah tapi belum ada kendaraan
unsigned long pendingUntilMs = 0;

// ---- Validasi plat (ANPR via GUI) — RFID + plat = dua lapis otorisasi ----
bool plateValidation = false;          // aktif kalau GUI kirim 'P' (ANPR nyala)
bool platePending = false;             // kartu sah, menunggu hasil validasi plat 'G'/'N' dari GUI
unsigned long platePendingUntilMs = 0;

void sensorDiag() {
  Serial.printf("> [diag] Sensor ENTRY — FRONT scale=%.3f PASS scale=%.3f\n",
                gate.front.getScale(), gate.exit.getScale());
  Serial.println("> [diag] raw echo + jarak — 8 baca tiap 400ms, letakkan objek di depan sensor:");
  for (int i = 0; i < 8; i++) {
    gate.front.update();
    gate.exit.update();
    Serial.printf("> [diag] F: raw=%uus cm=%d near=%d | P: raw=%uus cm=%d near=%d\n",
                  gate.front.rawUs(), (int)gate.front.getCm(), gate.front.isNear() ? 1 : 0,
                  gate.exit.rawUs(), (int)gate.exit.getCm(), gate.exit.isNear() ? 1 : 0);
    delay(400);
  }

  // ---- Uji silang approach: TRIG/ECHO MUNGKIN tertukar ----
  // Kirim trigger via pin ECHO (14), baca echo via pin TRIG (13).
  Serial.println("> [diag] UJI SILANG approach (TRIG<->ECHO ditukar) 5 baca:");
  pinMode(ECHO_PIN, OUTPUT);
  pinMode(TRIG_PIN, INPUT);
  for (int i = 0; i < 5; i++) {
    digitalWrite(ECHO_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(ECHO_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(ECHO_PIN, LOW);
    unsigned long t0 = micros();
    while (digitalRead(TRIG_PIN) == LOW) {
      if ((micros() - t0) > 60000UL) break;
    }
    unsigned long st = micros();
    while (digitalRead(TRIG_PIN) == HIGH) {
      if ((micros() - st) > 60000UL) break;
    }
    Serial.printf("> [diag] X: raw=%uus cm=%d\n", (unsigned long)(micros() - st), (int)((micros() - st) * 0.0343 / 2.0));
    delay(300);
  }
  // Kembalikan ke mode normal (TRIG=13 OUT, ECHO=14 IN).
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  Serial.println("> [diag] 'F raw=0us' + 'X raw>0'   = TRIG & ECHO approach tertukar (tukar kabel 13/14).");
  Serial.println("> [diag] 'F raw=0us' + 'X raw=0us' = kabel approach lepas/modul mati.");

  // ---- Uji silang pass: TRIG2/ECHO2 MUNGKIN tertukar ----
  Serial.println("> [diag] UJI SILANG pass (TRIG2<->ECHO2) 5 baca:");
  pinMode(ECHO2_PIN, OUTPUT);
  pinMode(TRIG2_PIN, INPUT);
  for (int i = 0; i < 5; i++) {
    digitalWrite(ECHO2_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(ECHO2_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(ECHO2_PIN, LOW);
    unsigned long t0 = micros();
    while (digitalRead(TRIG2_PIN) == LOW) {
      if ((micros() - t0) > 40000UL) break;
    }
    unsigned long st = micros();
    while (digitalRead(TRIG2_PIN) == HIGH) {
      if ((micros() - st) > 40000UL) break;
    }
    Serial.printf("> [diag] XP: raw=%uus cm=%d\n", (unsigned long)(micros() - st), (int)((micros() - st) * 0.0343 / 2.0));
    delay(300);
  }
  pinMode(TRIG2_PIN, OUTPUT);
  pinMode(ECHO2_PIN, INPUT);
  Serial.println("> [diag] P raw=0us & XP raw>0 = PASS tertukar (32/33).");
  Serial.println("> [diag] PASS raw=0 & XP raw=0 = PASS kabel lepas/modul mati.");
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
      // Tombol TIKET (dari GUI) — alternatif akses: tetap wajib ada kendaraan.
      if (gate.isVehicleNear()) {
        Serial.println("> [tiket] Tombol Tiket — gerbang dibuka");
        audio.greet();
        gate.openGate();
      } else {
        Serial.println("> [tiket] TIDAK ADA KENDARAAN — tiket diabaikan");
      }
    } else if (c == 'S') {
      sensorDiag();
    } else if (c == 'K' || c == 'J') {
      // Kalibrasi: '+K<jarak>' untuk FRONT, '+J<jarak>' untuk PASS.
      // Contoh: K50  → objek FRONT tepat 50cm;  J80 → objek PASS tepat 80cm.
      char sel = c;
      int dist = 0;
      while (Serial.available()) {
        char d = Serial.peek();
        if (d >= '0' && d <= '9') { dist = dist * 10 + (d - '0'); Serial.read(); }
        else break;
      }
      if (dist <= 0) {
        Serial.println("> [kal] Format: K<jarak> utk FRONT, J<jarak> utk PASS (cm). Contoh: K50");
      } else if (sel == 'K') {
        calibrateSensor(gate.front, "FRONT", "front_scale", dist);
      } else {
        calibrateSensor(gate.exit, "PASS", "pass_scale", dist);
      }
    } else if (c == 'P') {
      plateValidation = true;
      Serial.println("> VALIDASI PLAT AKTIF — tap RFID wajib diikuti plat terdeteksi (ANPR).");
    } else if (c == 'p') {
      plateValidation = false;
      Serial.println("> Validasi plat NONAKTIF — RFID normal (tanpa cek plat).");
    } else if (c == 'G') {
      // GUI: ANPR berhasil memvalidasi plat → buka gate.
      if (platePending) {
        platePending = false;
        platePendingUntilMs = 0;
        authPending = false;
        authResult = true;
        lastAuth = 'G';
        authUntilMs = millis() + RAUTH_DURATION_MS;
        Serial.println("> [anpr] PLAT TERVERIFIKASI — gerbang dibuka");
        audio.greet();
        gate.openGate();
      } else {
        Serial.println("> [anpr] 'G' diabaikan — tidak ada kartu menunggu validasi plat.");
      }
    } else if (c == 'N') {
      // GUI: ANPR tidak menemukan plat / plat tidak valid → tolak akses.
      if (platePending) {
        platePending = false;
        platePendingUntilMs = 0;
        authPending = false;
        authResult = false;
        lastAuth = 'D';
        authUntilMs = millis() + RAUTH_DURATION_MS;
        Serial.println("> [anpr] PLAT TIDAK TERVERIFIKASI — akses ditolak");
        audio.deny();
      } else {
        Serial.println("> [anpr] 'N' diabaikan — tidak ada kartu menunggu validasi plat.");
      }
    }
  }
}

void setup() {
  Serial.begin(115200);
  Serial.printf("> UNIT: ENTRY\n");
  Serial.printf("> CHIP: %s flash=%uKB psram=%s (%uKB)\n",
                ESP.getChipModel(), ESP.getFlashChipSize() / 1024,
                psramFound() ? "YES" : "no", ESP.getPsramSize() / 1024);

  gate.begin();
  gate.front.begin(TRIG_PIN, ECHO_PIN);
  gate.front.setNearCm(VEHICLE_CM);
  gate.exit.begin(TRIG2_PIN, ECHO2_PIN);
  gate.exit.setNearCm(PASS_VEHICLE_CM);
  {
    Preferences prefs;
    prefs.begin("hcsr", true);
    gate.front.setScale(prefs.getFloat("front_scale", 1.0f));
    gate.exit.setScale(prefs.getFloat("pass_scale", 1.0f));
    prefs.end();
    Serial.printf("> Kalibrasi: FRONT x%.3f, PASS x%.3f\n",
                  gate.front.getScale(), gate.exit.getScale());
  }
  pinMode(BTN_OPEN, INPUT);

  audio.begin();
  rfid.begin();
#if RFID_ENABLED
  rfid.printInitReport();
  if (!rfid.isMasterSet()) {
    Serial.println("> Tempel kartu pertama sebagai master (atau kirim 'A' lalu tempel).");
  }
#else
  Serial.println("RFID masked - open via button (GPIO4)");
#endif

  Serial.println("Gate ENTRY ready - CLOSED");
  ui.send(gate, rfid, authUntilMs, authResult, lastAuth, authPending, platePending);
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

  audio.update();

  // ---- sensor + log perubahan status (approach & pass) ----
  // Front & EXIT dibaca BERGANTIAN (tiap interval bergantian) agar kedua
  // sensor tidak pernah trigger bersamaan (crosstalk) & loop tidak diblokir
  // dua-duanya dalam satu tick.
  if (millis() - lastDistMs >= DIST_INTERVAL_MS) {
    lastDistMs = millis();
    static byte phase = 0;   // 0 = baca FRONT, 1 = baca EXIT

    if (phase == 0) {
      gate.front.update();    // baca approach ENTRY
      // ---- kecepatan approach + level AMAN/HATI-HATI/BAHAYA (Δd antar 2 update) ----
      {
        static unsigned long spPrevMs = 0;
        static int spPrevCm = -1;
        unsigned long spNow = millis();
        int spCm = (int)gate.front.getCm();
        if (spPrevCm > 0 && spCm > 0) {
          unsigned long spDt = spNow - spPrevMs;
          if (spDt >= 100UL && spDt <= 2000UL) {
            float kmh = (float)(spCm - spPrevCm) / (float)spDt * 3600.0f * 0.01f;
            const char *lvl = (kmh < 8.0f) ? "AMAN" : (kmh <= 20.0f ? "HATI-HATI" : "BAHAYA");
            Serial.printf("> [speed] ENTRY %.1f km/h LEVEL=%s (Δ%dcm/%lums)\n",
                          kmh, lvl, spCm - spPrevCm, (long)spDt);
          }
        }
        spPrevCm = spCm;
        spPrevMs = spNow;
      }

      bool fn = gate.front.isNear();
      if (fn != prevFrontNear) {
        prevFrontNear = fn;
        Serial.printf("> [sensor] ENTRY %s (%dcm)\n", fn ? "V:YES" : "V:NO", (int)gate.front.getCm());
      }
      phase = 1;
    } else {
      gate.exit.update();   // dibaca terpisah dari front (anti crosstalk)
      gate.updatePass();
      bool en = gate.exit.isNear();
      if (en != prevExitNear) {
        prevExitNear = en;
        Serial.printf("> [sensor] EXIT %s (%dcm)\n", en ? "V:YES" : "V:NO", (int)gate.exit.getCm());
      }
      phase = 0;
    }
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

      if (platePending) {
        // Sedang menunggu hasil validasi plat — jangan proses kartu lagi
        // sampai GUI membalas 'G'/'N' atau timeout.
        rfid.clearCooldown();
      } else if (rfid.activeMode() == 1) {
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
                if (plateValidation) {
                  // Dua-lapis: kartu sah + wajib validasi plat dari kamera.
                  platePending = true;
                  platePendingUntilMs = millis() + PLATE_TIMEOUT_MS;
                  authPending = false;
                  authResult = false;
                  lastAuth = 'V';
                  authUntilMs = 0;
                  Serial.println("> [rfid] KARTU SAH + kendaraan — menunggu validasi plat (ANPR)...");
                } else {
                  authResult = true;
                  lastAuth = 'G';
                  authUntilMs = millis() + RAUTH_DURATION_MS;
                  authPending = false;
                  Serial.println("> [rfid] ACCEPTED — kendaraan terdeteksi, gerbang dibuka");
                  audio.greet();
                  gate.openGate();
                }
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

  // Resolusi tunggu-kendaraan: begitu sensor ENTRY V:YES → buka gerbang.
  if (authPending) {
    if (gate.isVehicleNear()) {
      authPending = false;
      if (plateValidation) {
        // Dua-lapis: kartu sah + wajib validasi plat dari kamera.
        platePending = true;
        platePendingUntilMs = millis() + PLATE_TIMEOUT_MS;
        authResult = false;
        lastAuth = 'V';
        authUntilMs = 0;
        Serial.println("> [rfid] KENDARAAN DETEKSI — menunggu validasi plat (ANPR)...");
      } else {
        authResult = true;
        lastAuth = 'G';
        authUntilMs = millis() + RAUTH_DURATION_MS;
        Serial.println("> [rfid] KENDARAAN DETEKSI — kartu sah, gerbang dibuka");
        audio.greet();
        gate.openGate();
      }
    } else if (millis() >= pendingUntilMs) {
      authPending = false;
      authResult = false;
      lastAuth = 'D';
      authUntilMs = millis() + RAUTH_DURATION_MS;
      Serial.println("> [rfid] TAP TIMEOUT — tidak ada kendaraan, scan dibatalkan");
    }
  }

  // Timeout validasi plat — GUI tidak membalas 'G'/'N' tepat waktu → tolak.
  if (platePending && millis() >= platePendingUntilMs) {
    platePending = false;
    platePendingUntilMs = 0;
    authPending = false;
    authResult = false;
    lastAuth = 'D';
    authUntilMs = millis() + RAUTH_DURATION_MS;
    Serial.println("> [anpr] PLATE TIMEOUT — plat tidak terverifikasi, akses ditolak");
    audio.deny();
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

  // Saat terbuka: tutup hanya jika kendaraan SUDAH lewat (sensor exit passCleared)
  // ATAU diminta manual (perintah 'C' dari GUI). TANPA auto-close — gate boleh
  // lama terbuka selama kendaraan belum melewati sensor exit.
  if (gate.isOpen()) {
    if (!gate.closeRequested) {
      if (gate.passCleared) {
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
    ui.send(gate, rfid, authUntilMs, authResult, lastAuth, authPending, platePending);
  }
}