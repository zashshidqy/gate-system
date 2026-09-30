#include "Ultrasonic.h"

void USSensor::begin(byte trig, byte echo) {
  trigPin = trig;
  echoPin = echo;
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  reset();
}

void USSensor::reset() {
  idx = 0;
  nearStreak = 0;
  farStreak = 0;
  badCount = 0;
  near = false;
  lastCm = -1;
  lastRawUs = 0;
  for (int i = 0; i < SMOOTH_SAMPLES; i++) buf[i] = -1;
}

// Satu siklus trigger+ukur. Return false jika echo tidak sampai (timeout).
bool USSensor::tryOnce() {
  // Pastikan echo benar2 LOW dulu (hindari sisa pulsa dari baca sebelumnya).
  unsigned long t0 = micros();
  while (digitalRead(echoPin) == HIGH) {
    if ((micros() - t0) > 15000UL) { lastRawUs = 0; return false; }  // pin nyangkut HIGH
  }

  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Tunggu echo naik (mulai pengukuran). 30000us ≈ cukup untuk ~5m.
  t0 = micros();
  while (digitalRead(echoPin) == LOW) {
    if ((micros() - t0) > 30000UL) { lastRawUs = 0; return false; }  // tidak ada echo
  }
  unsigned long pulseStart = micros();
  // Ukur selama echo tinggi.
  while (digitalRead(echoPin) == HIGH) {
    if ((micros() - pulseStart) > 30000UL) { lastRawUs = 0; return false; }
  }
  unsigned long dur = micros() - pulseStart;
  lastRawUs = (uint16_t)dur;
  float c = dur * 0.0343 / 2.0 * calScale;
  if (c < 2 || c > maxCm) {
    lastRawUs = 0;
    return false;
  }
  lastCm = c;
  return true;
}

float USSensor::readRaw() {
  // CNT percobaan trigger; sering echo lolos pada percobaan pertama di 3.3V.
  static const byte CNT = 2;
  float c = -1;
  for (byte i = 0; i < CNT; i++) {
    if (tryOnce()) { c = lastCm; break; }
    delay(10);   // jeda antar percobaan agar modul siap lagi
  }
  return c;
}

void USSensor::update() {
  float r = readRaw();
  if (r < 0) {
    badCount++;
    if (badCount >= 2) reset();
    return;
  }
  badCount = 0;
  buf[idx] = r;
  idx = (idx + 1) % SMOOTH_SAMPLES;
  float sum = 0;
  int n = 0;
  for (int i = 0; i < SMOOTH_SAMPLES; i++) {
    if (buf[i] >= 0) { sum += buf[i]; n++; }
  }
  lastCm = (n > 0) ? (sum / n) : -1;

  if (lastCm >= 0 && lastCm <= nearCm) {
    farStreak = 0;
    nearStreak++;
    if (nearStreak >= NEAR_COUNT) near = true;
  } else {
    nearStreak = 0;
    farStreak++;
    if (farStreak >= NEAR_COUNT) near = false;
  }
}