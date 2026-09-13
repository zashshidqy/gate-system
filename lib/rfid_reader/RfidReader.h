#pragma once
#include <SPI.h>
#include <MFRC522.h>
#include <Preferences.h>
#include "config.h"

// ============================================================
//  RFID_READER — bungkus MFRC522 RC522.
//  Inisialisasi SPI custom pins, kartu MASTER, autentikasi.
// ============================================================

class RfidReader {
public:
  void begin();                       // SPI.begin + PCD_Init + baca version
  void printInitReport();             // cetak version + daftar master

  bool enabled() const { return RFID_ENABLED; }
  byte version() const { return v; }

  // ---- mazter / kartu terotorisasi (multi-master, persisten NVS) ----
  bool isMasterSet() const;           // ada minimal 1 kartu terotorisasi?
  byte authorizedCount() const;
  bool cardInList(const byte* uid, byte size) const;
  const byte* masterUidAt(byte i) const;
  byte masterUidSizeAt(byte i) const;

  // ---- baca kartu ----
  bool cardPresent();                 // REQA cepat (sekali) — ada kartu di area?
  bool tryReadCard();                 // baca 1 kartu secara robust (retry), tanpa deny
  bool addReadCardAsMaster();         // daftarkan kartu YANG BARU TERBACA (jika belum)
  bool removeReadCardFromMasters();   // hapus kartu YANG BARU TERBACA dari daftar
  bool currentCardAuthorized();       // true jika kartu yang BARU TERBACA terotorisasi
  void haltCurrent();                 // HaltA + StopCrypto (bersihkan transaksi)

  // ---- anti dobel-scan / kartu menginap ----
  bool seenRecently() const;
  void noteProcessedFromCurrent();    // tandai rfid.uid yang baru saja diproses
  void clearCooldown();               // reset cooldown (dipanggil saat area kosong)

  // ---- mode tambah / hapus master (perintah 'A' / 'Q') ----
  void startAddMode();                // jendela 15s: kartu berikutnya didaftarkan
  void startDelMode();                // jendela 15s: kartu berikutnya dihapus
  void stopMode();
  byte activeMode() const;            // 0=none 1=add 2=del
  bool modeExpired() const;           // mode masih nyala tapi waktunya habis?

  void clearMasters();                // hapus SEMUA master dari RAM + NVS
  void listMasters();                 // cetak semua kartu terotorisasi (perintah 'L')
  void runAudit();                    // diagnostik lengkap RFID (perintah serial 'V')
  void tapTest();                     // uji deteksi kartu jalur normal (perintah serial 'T')

  // Hex semua kartu terotorisasi ("UID1,UID2,...") — untuk panel GUI / ST
  void masterListHex(char* out, size_t n) const;

  // Hex string UID kartu terakhir yang terbaca (untuk panel GUI)
  void lastUidHex(char* out, size_t n) const;
  bool hasLastScan() const { return lastUidSize > 0; }
  void clearLastScan() { lastUidSize = 0; }

  static void dumpUid(uint8_t* uid, byte size);

private:
  MFRC522 rfid{SS_PIN, RST_PIN};
  Preferences prefs;
  byte v = 0;

  byte masters[MAX_MASTERS][10];
  byte masterSizes[MAX_MASTERS];
  byte masterCount = 0;

  byte lastUid[10];
  byte lastUidSize = 0;
  byte lastProcUid[10];
  byte lastProcSize = 0;
  unsigned long lastProcMs = 0;

  byte mode = 0;                       // 0 none, 1 add, 2 del
  unsigned long modeUntilMs = 0;

  bool pollCard();                    // IsNewCardPresent && ReadCardSerial (1x, keras)
  void snapshotUid();                 // salin UID terbaca → lastUid
  void removeIndex(byte idx);         // hapus entri ke-idx & geser array
  void loadMastersFromNvs();          // muat daftar master persisten dari NVS
  void saveMastersToNvs();            // simpan daftar master ke NVS

  // ---- audit: bit-bang SPI murni (bebas driver SPI HAL) ----
  static void bbWriteByte(byte b);
  byte bbReadByte() const;
  byte bitBangReg(MFRC522::PCD_Register reg) const;
};