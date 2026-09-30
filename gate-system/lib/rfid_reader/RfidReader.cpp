#include "RfidReader.h"

void RfidReader::begin() {
#if RFID_ENABLED
  SPI.begin(RFID_SCK, RFID_MISO, RFID_MOSI, SS_PIN);
  rfid.PCD_Init();
  rfid.PCD_SetAntennaGain(rfid.RxGain_max);
  v = rfid.PCD_ReadRegister(MFRC522::VersionReg);
#endif
#if RFID_ENABLED
  prefs.begin("gate_rfid", false);
  loadMastersFromNvs();
#endif
}

void RfidReader::printInitReport() {
  Serial.print("> RFID chip version: 0x");
  Serial.println(v, HEX);
  if (v == 0x00 || v == 0xFF) {
    Serial.println("> RFID TIDAK MERESPON! cek wiring (VCC=3.3V, GND, RST pin27, SDA pin25)");
  }
  if (masterCount > 0) {
    Serial.printf("> %d kartu terotorisasi di NVS:\n", masterCount);
    listMasters();
    Serial.println("> (tambah kartu: 'A' lalu tempel. hapus: 'Q'. hapus semua: 'R')");
  } else {
    Serial.println("> Belum ada kartu — tempel kartu pertama sebagai master!");
  }
}

// REQA cepat — cek ada kartu di area antena (1x, ~26ms), tidak memblokir lama.
bool RfidReader::cardPresent() {
  return rfid.PICC_IsNewCardPresent();
}

// Baca satu kartu secara robust: beberapa percobaan REQA+select dengan jeda.
// Menghindari deny PALS jadi UNAUTHORIZED hanya karena select gagal sekejap,
// dan menangkap kartu yang di-tap cepat / masih melintas.
bool RfidReader::tryReadCard() {
  for (int attempt = 0; attempt < RFID_READ_ATTEMPTS; attempt++) {
    if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
      return true;
    }
    delay(RFID_READ_RETRY_MS);
  }
  return false;
}

bool RfidReader::pollCard() {
  return rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial();
}

// ------------------------------------------------------------
//  MULTI-MASTER — daftar kartu yang berhak buka gerbang.
// ------------------------------------------------------------
bool RfidReader::isMasterSet() const {
  return masterCount > 0;
}

byte RfidReader::authorizedCount() const { return masterCount; }

const byte* RfidReader::masterUidAt(byte i) const { return masters[i]; }
byte RfidReader::masterUidSizeAt(byte i) const { return masterSizes[i]; }

bool RfidReader::cardInList(const byte* uid, byte size) const {
  for (byte i = 0; i < masterCount; i++) {
    if (masterSizes[i] == size) {
      bool same = true;
      for (byte j = 0; j < size; j++) {
        if (masters[i][j] != uid[j]) { same = false; break; }
      }
      if (same) return true;
    }
  }
  return false;
}

// Daftarkan kartu yang baru saja terbaca (rfid.uid). Tidak dobel.
bool RfidReader::addReadCardAsMaster() {
  if (cardInList(rfid.uid.uidByte, rfid.uid.size)) {
    snapshotUid();
    Serial.println("> Kartu SUDAH terotorisasi (tidak ditambahkan lagi).");
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
    return false;
  }
  if (masterCount >= MAX_MASTERS) {
    snapshotUid();
    Serial.println("> Daftar master PENUH! hapus salah satu dulu.");
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
    return false;
  }
  snapshotUid();
  masterSizes[masterCount] = rfid.uid.size;
  for (byte i = 0; i < rfid.uid.size; i++) masters[masterCount][i] = rfid.uid.uidByte[i];
  masterCount++;
  saveMastersToNvs();
  Serial.print("> Master ditambahkan: ");
  dumpUid(masters[masterCount - 1], masterSizes[masterCount - 1]);
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
  return true;
}

// Hapus kartu yang baru saja terbaca dari daftar.
bool RfidReader::removeReadCardFromMasters() {
  snapshotUid();
  byte idx = 0xFF;
  for (byte i = 0; i < masterCount; i++) {
    if (masterSizes[i] == rfid.uid.size) {
      bool same = true;
      for (byte j = 0; j < rfid.uid.size; j++) {
        if (masters[i][j] != rfid.uid.uidByte[j]) { same = false; break; }
      }
      if (same) { idx = i; break; }
    }
  }
  if (idx == 0xFF) {
    Serial.println("> Kartu bukan terotorisasi — tidak ada yang dihapus.");
  } else {
    removeIndex(idx);
    saveMastersToNvs();
    Serial.print("> Master dihapus: ");
    dumpUid(rfid.uid.uidByte, rfid.uid.size);
  }
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
  return idx != 0xFF;
}

// Variabel UID sudah diisi oleh tryReadCard(). Hanya deny jika UID BENAR-BENAR
// terbaca tetapi tidak ada di daftar master.
bool RfidReader::currentCardAuthorized() {
  snapshotUid();
  bool ok = cardInList(rfid.uid.uidByte, rfid.uid.size);
  if (!ok) {
    Serial.print("> UID: ");
    dumpUid(rfid.uid.uidByte, rfid.uid.size);
    Serial.println("> RFID UNAUTHORIZED");
  }
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
  return ok;
}

void RfidReader::haltCurrent() {
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
}

// ------------------------------------------------------------
//  ANTI DOBEL-SCAN — kartu sama yang baru diproses tidak boleh
//  langsung memicu lagi (mencegah dobel auth/tambah berulang).
// ------------------------------------------------------------
bool RfidReader::seenRecently() const {
  if (lastProcSize == 0) return false;
  if (rfid.uid.size != lastProcSize) return false;
  for (byte i = 0; i < lastProcSize; i++) {
    if (rfid.uid.uidByte[i] != lastProcUid[i]) return false;
  }
  return (millis() - lastProcMs) < RFID_COOLDOWN_MS;
}

void RfidReader::noteProcessedFromCurrent() {
  lastProcSize = rfid.uid.size;
  if (lastProcSize > sizeof(lastProcUid)) lastProcSize = sizeof(lastProcUid);
  for (byte i = 0; i < lastProcSize; i++) lastProcUid[i] = rfid.uid.uidByte[i];
  lastProcMs = millis();
}

void RfidReader::clearCooldown() {
  lastProcSize = 0;
}

// ------------------------------------------------------------
//  MODE TAMBAH / HAPUS MASTER — jendela waktu (RFID_MODE_WINDOW_MS).
//  Selama mode aktif, kartu berikutnya yang di-scan akan otomatis
//  didaftarkan / dihapus, lalu mode berhenti.
// ------------------------------------------------------------
void RfidReader::startAddMode() {
  mode = 1;
  modeUntilMs = millis() + RFID_MODE_WINDOW_MS;
  Serial.println("> MODE TAMBAH MASTER aktif (15 detik) — tempel kartu baru.");
}

void RfidReader::startDelMode() {
  mode = 2;
  modeUntilMs = millis() + RFID_MODE_WINDOW_MS;
  Serial.println("> MODE HAPUS MASTER aktif (15 detik) — tempel kartu yang mau dihapus.");
}

void RfidReader::stopMode() { mode = 0; }

byte RfidReader::activeMode() const { return mode; }

bool RfidReader::modeExpired() const {
  return mode != 0 && millis() >= modeUntilMs;
}

void RfidReader::clearMasters() {
  masterCount = 0;
  for (byte i = 0; i < MAX_MASTERS; i++) {
    prefs.remove(("m" + String(i)).c_str());
  }
  prefs.remove("mcount");
  Serial.println("> Semua kartu master dihapus.");
}

void RfidReader::removeIndex(byte idx) {
  for (byte i = idx; i + 1 < masterCount; i++) {
    masterSizes[i] = masterSizes[i + 1];
    for (byte j = 0; j < masterSizes[i]; j++) masters[i][j] = masters[i + 1][j];
  }
  masterCount--;
}

void RfidReader::listMasters() {
  if (masterCount == 0) {
    Serial.println("> (tidak ada kartu terotorisasi)");
    return;
  }
  for (byte i = 0; i < masterCount; i++) {
    Serial.printf(">   [%d] ", i + 1);
    dumpUid(masters[i], masterSizes[i]);
  }
}

void RfidReader::saveMastersToNvs() {
  prefs.putUChar("mcount", masterCount);
  for (byte i = 0; i < masterCount; i++) {
    prefs.putBytes(("m" + String(i)).c_str(), masters[i], masterSizes[i]);
  }
  for (byte i = masterCount; i < MAX_MASTERS; i++) {
    prefs.remove(("m" + String(i)).c_str());
  }
}

void RfidReader::loadMastersFromNvs() {
  masterCount = 0;
  byte n = prefs.getUChar("mcount", 0);
  if (n > MAX_MASTERS) n = MAX_MASTERS;
  for (byte i = 0; i < n; i++) {
    byte sz = prefs.getBytes(("m" + String(i)).c_str(), nullptr, 0);
    if (sz == 0 || sz > sizeof(masters[i])) continue;
    masterSizes[masterCount] = prefs.getBytes(("m" + String(i)).c_str(),
                                              masters[masterCount], sizeof(masters[i]));
    masterCount++;
  }
}

void RfidReader::snapshotUid() {
  lastUidSize = rfid.uid.size;
  if (lastUidSize > sizeof(lastUid)) lastUidSize = sizeof(lastUid);
  for (byte i = 0; i < lastUidSize; i++) lastUid[i] = rfid.uid.uidByte[i];
}

// ------------------------------------------------------------
//  TAP TEST — jalur NORMAL murni (PCD_Init → antenna gain → REQA).
//  Tidak ada bit-bang/reset tambahan. Uji apakah kartu terdeteksi.
// ------------------------------------------------------------
void RfidReader::tapTest() {
  rfid.PCD_Init();
  rfid.PCD_SetAntennaGain(rfid.RxGain_max);
  Serial.println("=== TAP TEST ===");
  Serial.println("> Tempel & TAHAN kartu di tengah antenna (jendela 45 detik)...");
  unsigned long t0 = millis();
  unsigned long lastDiag = 0;
  bool found = false;
  bool logDiag = true;
  while (millis() - t0 < 45000 && !found) {
    if (rfid.PICC_IsNewCardPresent()) {
      if (rfid.PICC_ReadCardSerial()) {
        Serial.print("> KARTU DITEMUKAN, UID: ");
        dumpUid(rfid.uid.uidByte, rfid.uid.size);
        Serial.print("  (type: ");
        Serial.print(rfid.PICC_GetTypeName(rfid.PICC_GetType(rfid.uid.sak)));
        Serial.println(")");
        found = true;
      } else {
        Serial.println("> reaksi kartu tapi gagal baca serial (collision?)");
      }
    }
    // Diagnostik RF tiap 2 detik: status REQA mentah + register TX/antar-lemparan
    if (millis() - lastDiag >= 2000) {
      lastDiag = millis();
      byte atqa[2]; byte atqaSize = 2;
      MFRC522::StatusCode st = rfid.PICC_RequestA(atqa, &atqaSize);
      byte irq = rfid.PCD_ReadRegister(MFRC522::ComIrqReg);
      byte err = rfid.PCD_ReadRegister(MFRC522::ErrorReg);
      if (logDiag) {
        Serial.printf("> REQA status=%u (0=OK 1=err 2=salah-kolisi 3=timeout 7=CRC 255=NACK) irq=0x%02X err=0x%02X\n",
                      (byte)st, irq, err);
        if (st == 0) {
          Serial.printf("  ATQA=0x%02X 0x%02X (0x0003=Classic 1K)\n", atqa[0], atqa[1]);
        }
      }
    }
    delay(30);
  }
  if (!found) {
    Serial.println("> TIDAK ADA KARTU terdeteksi dalam 45 detik");
  }
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
  Serial.println("=== END TAP TEST ===");
}

// ------------------------------------------------------------
//  AUDIT — memisahkan masalah software (SPI HAL) vs fisik/wiring.
//  3 jalur baca VersionReg:
//    1) hardware SPI 4MHz (jalur library normal)
//    2) hardware SPI 250kHz (slow clock, langsung transfer)
//    3) bit-bang murni (hanya digitalWrite/Read, tanpa driver SPI)
//  Modul sehat & pins benar → ketiganya harus 0x92/0x91/0x3A.
// ------------------------------------------------------------
void RfidReader::bbWriteByte(byte b) {
  for (int i = 7; i >= 0; i--) {
    digitalWrite(RFID_SCK, LOW);
    digitalWrite(RFID_MOSI, (b & (1 << i)) ? HIGH : LOW);
    delayMicroseconds(2);
    digitalWrite(RFID_SCK, HIGH);
    delayMicroseconds(2);
  }
}

byte RfidReader::bbReadByte() const {
  byte val = 0;
  for (int i = 7; i >= 0; i--) {
    digitalWrite(RFID_SCK, LOW);
    digitalWrite(RFID_MOSI, LOW);
    delayMicroseconds(2);
    digitalWrite(RFID_SCK, HIGH);
    delayMicroseconds(2);
    if (digitalRead(RFID_MISO)) val |= (1 << i);
  }
  return val;
}

byte RfidReader::bitBangReg(MFRC522::PCD_Register reg) const {
  pinMode(RFID_SCK, OUTPUT);
  pinMode(RFID_MOSI, OUTPUT);
  pinMode(RFID_MISO, INPUT);
  pinMode(SS_PIN, OUTPUT);
  pinMode(RST_PIN, OUTPUT);

  digitalWrite(RFID_SCK, LOW);
  digitalWrite(SS_PIN, HIGH);           // unselect dulu
  digitalWrite(RST_PIN, LOW);           // hard reset modul
  delay(10);
  digitalWrite(RST_PIN, HIGH);
  delay(50);                            // oscillator start-up (8.8.2 datasheet)

  digitalWrite(SS_PIN, LOW);            // select
  bbWriteByte(0x80 | reg);              // reg sudah pre-shift (0x37<<1)
  byte val = bbReadByte();
  digitalWrite(SS_PIN, HIGH);           // unselect
  return val;
}

void RfidReader::runAudit() {
  Serial.println("=== RFID AUDIT ===");
  Serial.printf("> pins SCK=%d MISO=%d MOSI=%d SS=%d RST=%d\n",
                RFID_SCK, RFID_MISO, RFID_MOSI, SS_PIN, RST_PIN);

  SPI.begin(RFID_SCK, RFID_MISO, RFID_MOSI, SS_PIN);
  rfid.PCD_Init();
  v = rfid.PCD_ReadRegister(MFRC522::VersionReg);
  Serial.printf("> [SPI 4MHz ] version=0x%02X\n", v);
  // Status antenna pada init NORMAL (tanpa reset): harus 0x83 = ON
  byte txcLib = rfid.PCD_ReadRegister(MFRC522::TxControlReg);
  Serial.printf("> [ANT-NORM ] TxControlReg=0x%02X -> driver %s\n",
                txcLib, (txcLib & 0x03) ? "AKTIF" : "MATI (!)");
  Serial.printf("> [SPI 4MHz ] selftest=%d gain=0x%02X\n",
                rfid.PCD_PerformSelfTest() ? 1 : 0, rfid.PCD_GetAntennaGain());
  rfid.PCD_Init();
  rfid.PCD_SetAntennaGain(rfid.RxGain_max);

  SPI.beginTransaction(SPISettings(250000, MSBFIRST, SPI_MODE0));
  digitalWrite(SS_PIN, LOW);
  SPI.transfer(0x80 | MFRC522::VersionReg);
  byte slow = SPI.transfer(0x00);
  digitalWrite(SS_PIN, HIGH);
  SPI.endTransaction();
  Serial.printf("> [SPI 250k ] version=0x%02X\n", slow);

  byte bb = bitBangReg(MFRC522::VersionReg);
  Serial.printf("> [BITBANG  ] version=0x%02X\n", bb);

  byte cmd  = bitBangReg(MFRC522::CommandReg);
  byte mode = bitBangReg(MFRC522::ModeReg);
  byte irq  = bitBangReg(MFRC522::ComIrqReg);
  byte txc  = bitBangReg(MFRC522::TxControlReg);
  Serial.printf("> [BITBANG  ] CommandReg=0x%02X ModeReg=0x%02X ComIrqReg=0x%02X\n",
                cmd, mode, irq);
  Serial.printf("> [ANTENNA  ] TxControlReg=0x%02X -> driver %s\n",
                txc, (txc & 0x03) ? "AKTIF (0x83/0x8D)" : "MATI (bawaan reset bit-bang)");

  // Reset modul lagi lalu init normal sebelum probe kartu
  rfid.PCD_Init();
  rfid.PCD_SetAntennaGain(rfid.RxGain_max);
  Serial.printf("> [ANT-PROBE] TxControlReg=0x%02X -> driver %s\n",
                rfid.PCD_ReadRegister(MFRC522::TxControlReg),
                (rfid.PCD_ReadRegister(MFRC522::TxControlReg) & 0x03) ? "AKTIF" : "MATI");

  Serial.println("> TAP KARTU SEKARANG (jendela 15 detik)...");
  unsigned long t0 = millis();
  bool found = false;
  while (millis() - t0 < 15000 && !found) {
    if (rfid.PICC_IsNewCardPresent()) {
      if (rfid.PICC_ReadCardSerial()) {
        Serial.print("> KARTU DITEMUKAN, UID: ");
        dumpUid(rfid.uid.uidByte, rfid.uid.size);
        Serial.print("  (type: ");
        Serial.print(rfid.PICC_GetTypeName(rfid.PICC_GetType(rfid.uid.sak)));
        Serial.println(")");
        found = true;
      } else {
        Serial.println("> ada reaksi tapi gagal baca serial (collision?)");
      }
    }
    delay(30);
  }
  if (!found) {
    Serial.println("> TIDAK ADA KARTU terdeteksi dalam 6 detik");
  }
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();

  auto isKnownVersion = [](byte x) -> bool {
    // Keluarga MFRC522: 0x92 (MFRC522 v2), 0x91 (v1), 0x82 (klon MF522), 0x3A (klon lain)
    return x == 0x92 || x == 0x91 || x == 0x82 || x == 0x3A;
  };
  bool chipOk = isKnownVersion(v) && isKnownVersion(slow) && isKnownVersion(bb);
  bool chipOkCmd = (v != 0x00 && v != 0xFF) && cmd == 0x20;
  Serial.printf("> AUDIT KESIMPULAN: %s\n",
                (chipOk || chipOkCmd)
                    ? "MODUL MENANGGAPI (software beres — scan kartu pertama untuk master)"
                    : (bb != 0x00 && bb != 0xFF)
                        ? "BITBANG hidup tapi SPI HAL beda → bug/pin mapping software"
                        : "SEMUA 0x00/0xFF → masalah FISIK (VCC/GND/pin/power modul)");
  Serial.println("=== END AUDIT ===");
}

// Comma-separated hex semua kartu terotorisasi: "31E70F0A,B0D90255,..."
void RfidReader::masterListHex(char* out, size_t n) const {
  if (n < 1) return;
  out[0] = '\0';
  if (masterCount == 0) {
    snprintf(out, n, "-");
    return;
  }
  int idx = 0;
  for (byte c = 0; c < masterCount; c++) {
    if (c > 0 && idx + 1 < (int)n) out[idx++] = ',';
    for (byte i = 0; i < masterSizes[c] && idx + 2 < (int)n; i++) {
      out[idx++] = "0123456789ABCDEF"[masters[c][i] >> 4];
      out[idx++] = "0123456789ABCDEF"[masters[c][i] & 0x0F];
    }
    if (idx + 2 >= (int)n) break;
  }
  out[idx] = '\0';
}

void RfidReader::lastUidHex(char* out, size_t n) const {
  if (n < 1) return;
  out[0] = '\0';
  if (lastUidSize == 0) {
    snprintf(out, n, "-");
    return;
  }
  int idx = 0;
  for (byte i = 0; i < lastUidSize && idx + 2 < (int)n; i++) {
    out[idx++] = "0123456789ABCDEF"[lastUid[i] >> 4];
    out[idx++] = "0123456789ABCDEF"[lastUid[i] & 0x0F];
  }
  out[idx] = '\0';
}

void RfidReader::dumpUid(uint8_t* uid, byte size) {
  for (byte i = 0; i < size; i++) {
    Serial.print(uid[i] < 0x10 ? "0" : "");
    Serial.print(uid[i], HEX);
    Serial.print(" ");
  }
  Serial.println();
}