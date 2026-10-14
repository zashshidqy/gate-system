#include "DFPlayer.h"

void DFPlayer::begin() {
#if DFPLAYER_ENABLED
  Serial2.begin(9600, SERIAL_8N1, DFPLAYER_RX_PIN, DFPLAYER_TX_PIN);
  delay(200); // tunggu DFPlayer boot
  
  if (!dfp.begin(Serial2, false, 100)) {
    enabled = false;
    Serial.println("> [DFPlayer] INIT GAGAL — microSD tidak ada / modul tidak merespons. Audio dimatikan.");
    return;
  }
  
  dfp.volume(DFPLAYER_VOLUME);
  dfp.playbackSource(2); // TF card (microSD)
  enabled = true;
  Serial.println("> [DFPlayer] Siap (volume=" + String(DFPLAYER_VOLUME) + ")");
#else
  enabled = false;
#endif
}

void DFPlayer::update() {
  if (!enabled) return;
  
  // Cek status playing via library (query ke DFPlayer)
  // DFPlayerMini_Fast::isPlaying() mengirim query 0x42 dan menunggu response
  // Kita panggil sesekali, bukan tiap loop, tapi panggil di sini OK karena non-blocking
  // (library pakai timeout pendek)
  bool wasPlaying = playing;
  playing = dfp.isPlaying();
  
  // Fallback: kalau library return false tapi kita baru play sebentar lalu
  // (race condition query), pakai timer sebagai safety net
  if (!playing && wasPlaying && (millis() - playStartMs < TRACK_TIMEOUT_MS)) {
    // Mungkin query belum update, tetap anggap playing sebentar
    playing = true;
  }
}

void DFPlayer::greet() {
  if (!enabled) return;
  if (playing) return; // jangan interrupt track yang sedang jalan
  dfp.play(DFPLAYER_GREET_TRACK);
  playStartMs = millis();
  playing = true;
}

void DFPlayer::deny() {
  if (!enabled) return;
  if (playing) return;
  dfp.play(DFPLAYER_DENY_TRACK);
  playStartMs = millis();
  playing = true;
}

void DFPlayer::stop() {
  if (!enabled) return;
  dfp.stop();
  playing = false;
}