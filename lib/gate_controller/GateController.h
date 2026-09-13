#pragma once
#include <ESP32Servo.h>
#include "config.h"
#include "Ultrasonic.h"

// ============================================================
//  GATE_CONTROLLER — state machine + gerak servo + logika pass.
//  Memiliki kedua sensor (front & exit) dan semua status gate.
// ============================================================

enum GateState { CLOSED, OPENING, OPEN, CLOSING };

class GateController {
public:
  void begin();               // attach servo + posisi awal CLOSED

  // Panggil tiap STEP_DELAY_MS dari loop() — gerak bertahap (non-blocking)
  void loopMotion();

  bool openGate();            // true jika mulai membuka
  void closeGate();           // langsung menutup (setelah disetujui)
  void requestClose();        // handler perintah 'C' dari serial
  void testToClosed();        // perintah 'X'
  void testToOpen();          // perintah 'Z'

  // Sinkron logika "kendaraan sudah lewat" dari sensor exit (tiap tick sensor)
  void updatePass();

  bool isVehicleNear() const;
  bool isOpen() const;
  bool isClosed() const;
  bool isBusy() const;
  const char* stateName() const;
  int getPos() const { return currentPos; }

  // ---- status publik (dibaca status_report / main) ----
  USSensor front;             // sensor depan (kendaraan dekat)
  USSensor exit;              // sensor exit (kendaraan sudah lewat)
  GateState state = CLOSED;
  int currentPos = POS_CLOSED;
  bool closeRequested = false;
  bool passSeen = false;
  bool passCleared = false;
  unsigned long openSinceMs = 0;
  unsigned long rejectUntilMs = 0;  // pesan "NO VEHICLE!" di GUI

private:
  Servo gateServo;
  int servoStartPos = POS_CLOSED;
  int servoEndPos = POS_OPEN;
  unsigned long servoStartMs = 0;
  uint16_t lastUs = SERVO_US_MAX;   // pulsa terakhir yg ditulis (utk clamp delta)

  void beginServoMove(int endTarget);  // set profil gerak eased baru
  bool stepServo();                    // 1 tick eased; true=masih bergerak, false=selesai
  uint16_t degToUs(int deg) const;     // derajat 0..180 → microseconds
  int usToDeg(uint16_t us) const;
};