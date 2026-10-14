#pragma once
#include <Arduino.h>
#include "config.h"
#include <DFPlayerMini_Fast.h>

// ============================================================
//  DFPlayer Mini — MP3 playback (menggantikan Buzzer).
//  Non-blocking: begin() init Serial2 + DFPlayer, update() polling
//  isPlaying() pakai library (query status).
//  Jika microSD tidak ada / begin gagal → enabled=false, boot normal.
// ============================================================

class DFPlayer {
public:
  void begin();
  void update();
  void greet();   // putar track greet (0001.mp3)
  void deny();    // putar track deny (0002.mp3)
  void stop();
  bool isPlaying() const { return playing; }

private:
  DFPlayerMini_Fast dfp;
  bool enabled = true;
  bool playing = false;
  unsigned long playStartMs = 0;
  const unsigned long TRACK_TIMEOUT_MS = 5000; // fallback timeout jika query gagal
};