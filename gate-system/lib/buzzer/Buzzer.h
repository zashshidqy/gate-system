#pragma once
#include <Arduino.h>
#include "config.h"

// ============================================================
//  BUZZER — greeting sound (add-on).
//  Buzzer pasif di BUZZER_PIN (default GPIO2). Non-blocking:
//  nada dimainkan bertahap via millis(), panggil update() tiap loop().
//  Set BUZZER_PIN = -1 di config.h untuk menonaktifkan.
// ============================================================

class Buzzer {
public:
  void begin();
  void update();           // lanjutkan nada berikutnya bila sudah waktunya
  void greet();            // greeting: nada naik (kartu diterima / gate buka)
  void deny();             // deny: buzz rendah (kartu ditolak)
  void stop();
  bool isPlaying() const { return active; }

private:
  const int* freqs = nullptr;
  const unsigned long* durs = nullptr;
  byte count = 0;
  byte idx = 0;
  unsigned long noteUntilMs = 0;
  bool active = false;
  bool enabled = true;

  void startPattern(const int* f, const unsigned long* d, byte n);
  void playNote();
};