#include "Buzzer.h"

// "selamat datang dan tap kartu" — nada naik (selamat datang),
// jeda singkat, lalu dua beep cepat (ajakan "tap kartu").
static const int GREET_FREQ[] = { 523, 659, 784, 784, 0, 1568, 1319 };
static const unsigned long GREET_DUR[] = { 90, 90, 110, 60, 80, 60, 150 };
static const byte   GREET_N  = 7;

static const int    DENY_FREQ[] = { 220, 180 };
static const unsigned long DENY_DUR[] = { 180, 220 };
static const byte   DENY_N   = 2;

void Buzzer::begin() {
  if ((int)BUZZER_PIN < 0) {
    enabled = false;
    return;
  }
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  ledcSetup(BUZZER_LEDC_CH, 1000, 8);
  ledcAttachPin(BUZZER_PIN, BUZZER_LEDC_CH);
  ledcWriteTone(BUZZER_LEDC_CH, 0);
  active = false;
}

void Buzzer::startPattern(const int* f, const unsigned long* d, byte n) {
  if (!enabled) return;
  freqs = f;
  durs = d;
  count = n;
  idx = 0;
  active = true;
  noteUntilMs = 0;
  playNote();
}

void Buzzer::playNote() {
  if (!active) return;
  ledcWriteTone(BUZZER_LEDC_CH, freqs[idx] > 0 ? freqs[idx] : 0);
  noteUntilMs = millis() + durs[idx];
}

void Buzzer::update() {
  if (!active) return;
  if (millis() < noteUntilMs) return;
  idx++;
  if (idx >= count) {
    stop();
    return;
  }
  playNote();
}

void Buzzer::greet() {
  startPattern(GREET_FREQ, GREET_DUR, GREET_N);
}

void Buzzer::deny() {
  startPattern(DENY_FREQ, DENY_DUR, DENY_N);
}

void Buzzer::stop() {
  if (!enabled) return;
  active = false;
  ledcWriteTone(BUZZER_LEDC_CH, 0);
}