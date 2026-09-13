#include "GateController.h"

void GateController::begin() {
  gateServo.attach(SERVO_PIN);
  gateServo.setPeriodHertz(50);
  gateServo.writeMicroseconds(degToUs(POS_CLOSED));
  currentPos = POS_CLOSED;
  lastUs = degToUs(POS_CLOSED);
  state = CLOSED;
  closeRequested = false;
  passSeen = false;
  passCleared = false;
}

// Inisialisasi profil gerak: simpan titik awal/akhir & waktu mulai.
void GateController::beginServoMove(int endTarget) {
  servoStartPos = currentPos;
  servoEndPos = endTarget;
  servoStartMs = millis();
  lastUs = degToUs(currentPos);
}

// Konversi derajat (0..180) ↔ microseconds (SERVO_US_MIN..SERVO_US_MAX)
uint16_t GateController::degToUs(int deg) const {
  if (deg <= 0) return SERVO_US_MIN;
  if (deg >= 180) return SERVO_US_MAX;
  return SERVO_US_MIN + (uint16_t)((uint32_t)(deg) * (SERVO_US_MAX - SERVO_US_MIN) / 180u);
}

int GateController::usToDeg(uint16_t us) const {
  if (us <= SERVO_US_MIN) return 0;
  if (us >= SERVO_US_MAX) return 180;
  return (int)(((uint32_t)(us - SERVO_US_MIN) * 180u) / (SERVO_US_MAX - SERVO_US_MIN));
}

// Satu tick gerak dengan profil ease-in-out (cosine) DI UKURAN PULSA (µs).
// Delta per tick dibatasi SERVO_MAX_US_STEP agar tak ada lompatan keras —
// servo bergerak halus penuh percepatan→puncak→perlambatan.
bool GateController::stepServo() {
  float t = (millis() - servoStartMs) / (float)SERVO_STROKE_MS;
  if (t >= 1.0f) {
    currentPos = servoEndPos;
    gateServo.writeMicroseconds(degToUs(servoEndPos));
    lastUs = degToUs(servoEndPos);
    return false;
  }
  float eased = 0.5f - 0.5f * cos(t * PI);
  int targetDeg = servoStartPos + (int)(eased * (servoEndPos - servoStartPos) + 0.5f);
  int targetUs = degToUs(targetDeg);
  int delta = targetUs - lastUs;
  if (delta > SERVO_MAX_US_STEP) delta = SERVO_MAX_US_STEP;
  else if (delta < -SERVO_MAX_US_STEP) delta = -SERVO_MAX_US_STEP;
  int nextUs = lastUs + delta;
  if (nextUs != (int)lastUs) {
    lastUs = nextUs;
    gateServo.writeMicroseconds(lastUs);
    currentPos = usToDeg(lastUs);
  }
  return true;
}

// Gerak servo per tick (non-blocking). Halangan dicek dengan jarak LIVE.
void GateController::loopMotion() {
  if (state == OPENING) {
    if (!stepServo()) {
      state = OPEN;
      openSinceMs = millis();
      passSeen = false;
      passCleared = false;
      return;
    }
  } else if (state == CLOSING) {
    float cm = front.getCm();
    if (cm >= 0 && cm < OBSTACLE_CM) {
      Serial.println("> OBSTACLE! Reopen");
      closeRequested = false;
      beginServoMove(POS_OPEN);
      state = OPENING;
      return;
    }
    if (!stepServo()) {
      state = CLOSED;
      Serial.println("> GATE CLOSED");
      return;
    }
  }
}

bool GateController::openGate() {
  if (state == OPEN || state == OPENING) return false;
  if (!front.isNear()) {
    Serial.println("> NO VEHICLE - rejected");
    rejectUntilMs = millis() + MSG_DURATION_MS;
    return false;
  }
  Serial.println("> GATE OPEN");
  beginServoMove(POS_OPEN);
  state = OPENING;
  return true;
}

void GateController::closeGate() {
  if (state == CLOSED || state == CLOSING) return;
  closeRequested = false;
  Serial.println("> GATE CLOSING");
  beginServoMove(POS_CLOSED);
  state = CLOSING;
}

void GateController::requestClose() {
  if (state == OPEN && !closeRequested) {
    closeRequested = true;
    Serial.println("> Close requested (GUI)");
  } else if (state == OPEN) {
    Serial.println("> Already close requested");
  } else {
    Serial.println("> Gate not open");
  }
}

void GateController::testToClosed() {
  beginServoMove(POS_CLOSED);
  state = CLOSING;
  Serial.println("> Test pos CLOSED");
}

void GateController::testToOpen() {
  beginServoMove(POS_OPEN);
  state = OPENING;
  Serial.println("> Test pos OPEN");
}

// Kendaraan terdeteksi di area exit (near) → passSeen.
// Area exit kosong lagi → passCleared → boleh menutup lebih cepat.
void GateController::updatePass() {
  if (exit.isNear()) {
    passSeen = true;
  } else if (passSeen) {
    passCleared = true;
  }
}

bool GateController::isVehicleNear() const {
  return front.isNear();
}

bool GateController::isOpen() const {
  return state == OPEN;
}

bool GateController::isClosed() const {
  return state == CLOSED;
}

bool GateController::isBusy() const {
  return state == OPENING || state == CLOSING;
}

const char* GateController::stateName() const {
  switch (state) {
    case CLOSED:  return "CLOSED";
    case OPENING: return "OPENING";
    case OPEN:    return "OPEN";
    case CLOSING: return "CLOSING";
    default:      return "?";
  }
}