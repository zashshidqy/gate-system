#pragma once
#include <Arduino.h>
#include "config.h"
#include "GateController.h"
#include "RfidReader.h"

// ============================================================
//  STATUS_REPORT — baris display (2x16) + protokol ST ke GUI.
//  Status dikirim tiap SERIAL_STATUS_MS.
// ============================================================

class StatusReport {
public:
  // Bangun 2 baris tampilan dari kondisi saat ini
  void buildRows(GateController& gate, const RfidReader& rfid,
                 unsigned long authUntilMs, bool authResult, bool authPending);

  // Kirim: ST|<state>|<pos>|<dist>|<vehicle>|<row1>|<row2>|<masters>|<exitCm>|<rfidVer>|<lastUid>|<lastAuth>|<count>
  void send(GateController& gate, const RfidReader& rfid,
            unsigned long authUntilMs, bool authResult, char lastAuth,
            bool authPending);

  const char* row1() const { return lcdRow1; }
  const char* row2() const { return lcdRow2; }

private:
  char lcdRow1[17];
  char lcdRow2[17];
};