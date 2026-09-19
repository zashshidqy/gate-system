#pragma once
#include <Arduino.h>
#include "config.h"

// ============================================================
//  ULTRASONIC — bungkus HC-SR04 (dipakai sensor depan & exit)
//  Filter noise, rata-rata 5 sampel, debounce NEAR_COUNT.
// ============================================================

class USSensor {
public:
  void begin(byte trig, byte echo);
  void update();
  void reset();

  bool isNear() const { return near; }
  float getCm() const { return lastCm; }
  uint16_t rawUs() const { return lastRawUs; }   // durasi echo mentah (debug)

  // Threshold bisa diubah per sensor (mis. approach vs pass berbeda).
  void setNearCm(byte v) { nearCm = v; }
  void setMaxValidCm(uint16_t v) { maxCm = v; }

  // Kalibrasi: geser hasil jarak dengan faktor skala (dari NVS / perintah 'K').
  void setScale(float s) { calScale = (s > 0.5f && s <= 1.5f) ? s : 1.0f; }
  float getScale() const { return calScale; }

private:
  byte trigPin = 0;
  byte echoPin = 0;
  byte nearCm = VEHICLE_CM;
  uint16_t maxCm = MAX_VALID_CM;
  float calScale = 1.0f;      // faktor koreksi kalibrasi
  uint16_t lastRawUs = 0;
  float buf[SMOOTH_SAMPLES];
  int idx = 0;
  int nearStreak = 0;
  int farStreak = 0;
  int badCount = 0;
  bool near = false;
  float lastCm = -1.0f;

  bool tryOnce();    // satu siklus trigger+ukur
  float readRaw();
};