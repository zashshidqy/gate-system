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

private:
  byte trigPin = 0;
  byte echoPin = 0;
  float buf[SMOOTH_SAMPLES];
  int idx = 0;
  int nearStreak = 0;
  int farStreak = 0;
  int badCount = 0;
  bool near = false;
  float lastCm = -1.0f;

  float readRaw();
};