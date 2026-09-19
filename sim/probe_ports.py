#!/usr/bin/env python3
"""Probe-diagnostik kedua port ESP32 — DETACHABLE, 6 detik per port, tanpa GUI."""
import serial
import serial.tools.list_ports as lp
import time
import sys

ports = [p.device for p in lp.comports()]
usb = sorted(d for d in ports if "ttyUSB" in d or "ttyACM" in d)
print("Port USB terdeteksi:", usb)
if not usb:
    print("RESULT: TIDAK ADA PORT USB -> kabel/unplug/udev. GUI mustahil konek.")
    sys.exit(0)

for port in usb:
    try:
        s = serial.Serial(port, 115200, timeout=1.0)
        s.dtr = False
        s.rts = False
    except Exception as e:
        print("[%s] GAGAL BUKA: %s" % (port, e))
        continue
    end = time.time() + 6
    buf = b""
    while time.time() < end:
        try:
            buf += s.read(1024)
        except serial.SerialException as e:
            print("[%s] PUTUS-SAAT-BACA: %s" % (port, e))
            break
    s.close()
    st = [l.decode(errors="replace") for l in buf.splitlines() if l.startswith(b"ST|")]
    print("[%s] dlm 6dtk -> %d baris ST; contoh: %s"
          % (port, len(st), st[0][:80] if st else "(TIADA DATA - kabel/firmware/solder)"))
