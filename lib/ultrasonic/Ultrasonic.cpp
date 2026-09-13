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
  for (int i = 0; i < SMOOTH_SAMPLES; i++) buf[i] = -1;
}

float USSensor::readRaw() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  long dur = pulseIn(echoPin, HIGH, 40000);
  if (dur == 0) return -1;
  float c = dur * 0.0343 / 2.0;
  if (c < 2 || c > MAX_VALID_CM) return -1;
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

  if (lastCm >= 0 && lastCm <= VEHICLE_CM) {
    farStreak = 0;
    nearStreak++;
    if (nearStreak >= NEAR_COUNT) near = true;
  } else {
    nearStreak = 0;
    farStreak++;
    if (farStreak >= NEAR_COUNT) near = false;
  }
}