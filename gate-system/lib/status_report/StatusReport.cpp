#include "StatusReport.h"

void StatusReport::buildRows(GateController& gate, const RfidReader& rfid,
                             unsigned long authUntilMs, bool authResult,
                             bool authPending, bool platePending) {
  unsigned long now = millis();
  snprintf(lcdRow1, sizeof(lcdRow1), "Gate: %-10s", gate.stateName());

  const char* msg = nullptr;
  if (platePending) {
    msg = "VALIDASI PLAT...";
  } else if (now < gate.rejectUntilMs) {
    msg = "NO VEHICLE!";
  } else if (authPending) {
    msg = "TUNGGU KENDARAAN MASUK";
  } else if (now < authUntilMs) {
    msg = authResult ? "ACCESS GRANTED" : "UNAUTHORIZED";
  } else if (gate.isOpen() && gate.closeRequested && gate.passCleared) {
    msg = "VEHICLE PASSED!";
  } else if (gate.isOpen() && gate.closeRequested && gate.isVehicleNear()) {
    msg = "WAIT VEHICLE!";
  } else if (gate.state == OPENING) {
    msg = "OPENING...";
  } else if (gate.state == CLOSING) {
    msg = "CLOSING...";
  }

  if (msg != nullptr) {
    snprintf(lcdRow2, sizeof(lcdRow2), "%-16s", msg);
  } else if (gate.front.getCm() < 0) {
    snprintf(lcdRow2, sizeof(lcdRow2), "%s---",
             gate.front.isNear() ? "V:YES " : "V:NO  ");
  } else {
    snprintf(lcdRow2, sizeof(lcdRow2), "%s%2dcm ",
             gate.front.isNear() ? "V:YES " : "V:NO  ", (int)gate.front.getCm());
  }
}

void StatusReport::send(GateController& gate, const RfidReader& rfid,
                        unsigned long authUntilMs, bool authResult, char lastAuth,
                        bool authPending, bool platePending) {
  char masterList[128];
  rfid.masterListHex(masterList, sizeof(masterList));
  char lastUidHex[21];
  rfid.lastUidHex(lastUidHex, sizeof(lastUidHex));

  buildRows(gate, rfid, authUntilMs, authResult, authPending, platePending);

  Serial.print("ST|");
  Serial.print(gate.stateName());
  Serial.print("|");
  Serial.print(gate.getPos());
  Serial.print("|");
  Serial.print(gate.front.getCm() < 0 ? -1 : (int)gate.front.getCm());
  Serial.print("|");
  Serial.print(gate.isVehicleNear() ? 1 : 0);
  Serial.print("|");
  Serial.print(lcdRow1);
  Serial.print("|");
  Serial.print(lcdRow2);
  Serial.print("|");
  Serial.print(masterList);
  Serial.print("|");
  Serial.print(gate.exit.getCm() < 0 ? -1 : (int)gate.exit.getCm());
  Serial.print("|");
  byte vv = rfid.version();
  Serial.print(vv < 0x10 ? "0x0" : "0x");
  Serial.print(vv, HEX);
  Serial.print("|");
  Serial.print(lastUidHex);
  Serial.print("|");
  Serial.print(lastAuth);
  Serial.print("|");
  Serial.println(rfid.authorizedCount());
}