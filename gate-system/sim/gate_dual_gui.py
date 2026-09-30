#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_dual_gui.py — ALL-IN-ONE: Unit ENTRY (kiri) + Unit EXIT (kanan).

Satu jendela Tk, DUA panel kartu berdampingan. Setiap unit punya port serial
nya sendiri (lebih detail di bawah). GUI menampilkan SEMUA sensor kedua unit
sekaligus — sehingga memudahkan melihat sensor mana yang hidup / yang
menghasilkan -1 (misal approach ENTRY yang sering tak terbaca).

Protokol serial (sama persis dgn gate_serial_gui.py, hasil emit ESP32):

  ST|<state>|<pos>|<front_cm>|<vehicle>|<lcd1>|<lcd2>|<masters>|
    <pass_cm>|<rfid_ver>|<last_uid>|<last_auth>|<count>
  field:
    front_cm  = HC-SR04 #1 (APPROACH) — ENTRY pakai GPIO13/14; EXIT -1 (by design)
    pass_cm   = HC-SR04 #2 (PASS)      — keduanya GPIO32/33
    vehicle   = 1 bila kendaraan dekat approach ENTRY
    rfid_*    = versi RC522 + UID terakhir + hasil auth (G/D/P/A/R)

Tiap unit EXPORT dari ESP32-nya masing2 lewat port USB terpisah:
    /dev/ttyUSB0 → ENTRY    /dev/ttyUSB1 → EXIT
(kalau kebalik juga tak masalah — GUI auto-cari, dan ada tombol tukar.)

Cara jalan (di environment grafis, dua kabel USB terpasang):
    cd sim
    .venv/bin/python3.11 gate_dual_gui.py

Dependensi: pyserial, tkinter (bawaan Python). Tanpa ANPR/paddle/PIL → stabil
tidak SIGABRT. Bila mau mode single-unit ada di gate_serial_gui.py.
"""

import os
import queue
import sys
import threading
import time

import tkinter as tk
from tkinter import ttk, scrolledtext

import serial
import serial.tools.list_ports

# ---------------- konstanta (netral, konsisten dgn gui lama) ----------------
WIN_BG  = "#eef0f3"
CARD_BG = "#ffffff"
CARD_BG2 = "#f6f7f9"
BORDER  = "#dce0e5"
TEXT    = "#20242a"
MUTED   = "#5f6a76"
ACCENT  = "#2f6fd0"
OK      = "#16794c"
WARN    = "#9a6b1f"
ERR     = "#c0392b"
GRAY    = "#8a94a0"
FONT    = "DejaVu Sans"
PY = sys.executable


def list_ports():
    devices = [p.device for p in serial.tools.list_ports.comports()]
    usb = sorted(d for d in devices if "ttyUSB" in d or "ttyACM" in d)
    return usb


def parse_st(line):
    """'ST|...' (13 field) → dict; None bila baris bukan ST/rusak."""
    if not line.startswith("ST|"):
        return None
    p = line.split("|")
    if len(p) < 13:
        return None

    def _i(i):
        try:
            return int(p[i])
        except (ValueError, IndexError):
            return -1

    return {
        "state":   p[1],
        "pos":     _i(2),
        "front":   _i(3),     # approach (ENTRY sah; EXIT -1)
        "vehicle": p[4] == "1",
        "lcd1":    p[5],
        "lcd2":    p[6],
        "masters": p[7],
        "pass":    _i(8),     # pass sensor (ENTRY & EXIT)
        "rfid_ver":p[9],
        "last_uid":p[10],
        "last_auth":p[11],
        "count":   _i(12),
    }


# ============================================================
#  PANEL SATU UNIT (ENTRY / EXIT)
# ============================================================
class UnitPanel:
    def __init__(self, parent, title, on_log=None):
        self.title = title
        self.on_log = on_log
        self.state = "CLOSED"
        self.pos   = 120
        self.front_cm = -1
        self.vehicle = False
        self.lcd1  = "-"
        self.lcd2  = "-"
        self.masters = "-"
        self.pass_cm = -1
        self.rfid_ver  = "-"
        self.rfid_uid  = "-"
        self.rfid_auth = "-"
        self.rfid_count = 0

        self._q = queue.Queue()
        self._log_q = queue.Queue()

        self.root = tk.Frame(parent, bg=WIN_BG)
        self.root.pack(fill="both", expand=True)
        self._build_header()
        self._build_status()
        self._build_sensor()
        self._build_conn()

    # ----- layout helpers -----
    def _card(self, parent, title):
        c = tk.Frame(parent, bg=CARD_BG, highlightbackground=BORDER,
                     highlightthickness=1)
        c.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(c, text=title, bg=CARD_BG, fg=MUTED,
                 font=(FONT, 10, "bold")).pack(anchor="w", padx=10, pady=(8, 0))
        return c

    def _kv(self, parent, key, value, bold=True):
        f = tk.Frame(parent, bg=CARD_BG)
        f.pack(anchor="w", padx=10)
        tk.Label(f, text=key + ":", bg=CARD_BG, fg=MUTED,
                 font=(FONT, 10)).pack(side="left")
        lv = tk.Label(f, text=value, bg=CARD_BG, fg=TEXT,
                      font=(FONT, 13, "bold" if bold else "normal"))
        lv.pack(side="left")
        return lv

    def _build_header(self):
        h = tk.Frame(self.root, bg=WIN_BG)
        h.pack(fill="x", padx=8, pady=(8, 0))
        tk.Label(h, text=self.title, bg=WIN_BG, fg=TEXT,
                 font=(FONT, 13, "bold")).pack(side="left")
        self.lbl_conn = tk.Label(h, text="Terputus", bg=WIN_BG, fg=ERR,
                                 font=(FONT, 9, "bold"))
        self.lbl_conn.pack(side="right")

    def _build_status(self):
        c = self._card(self.root, "Status Gerbang")
        self.lbl_state = tk.Label(c, text="Tertutup", bg=CARD_BG, fg=OK,
                                  font=(FONT, 15, "bold"))
        self.lbl_state.pack(anchor="w", padx=10)
        self.lbl_pos = self._kv(c, "Posisi", "-")
        self.bar = ttk.Progressbar(c, maximum=100)
        self.bar.pack(fill="x", padx=10, pady=(0, 8))

    def _build_sensor(self):
        c = self._card(self.root, "Sensor")
        self.lbl_dist = tk.Label(c, text="--- cm", bg=CARD_BG, fg=TEXT,
                                 font=(FONT, 17, "bold"))
        self.lbl_dist.pack(anchor="w", padx=10)
        self.lbl_vehicle = tk.Label(c, text="Jalur kosong", bg=CARD_BG, fg=GRAY,
                                    font=(FONT, 11, "bold"))
        self.lbl_vehicle.pack(anchor="w", padx=10)
        self.bar_dist = ttk.Progressbar(c, maximum=100)
        self.bar_dist.pack(fill="x", padx=10)
        passf = tk.Frame(c, bg=CARD_BG)
        passf.pack(anchor="w", padx=10, pady=(4, 4))
        tk.Label(passf, text="Pass sensor:", bg=CARD_BG, fg=MUTED,
                 font=(FONT, 10)).pack(side="left")
        self.lbl_pass = tk.Label(passf, text="--- cm", bg=CARD_BG, fg=TEXT,
                                 font=(FONT, 11, "bold"))
        self.lbl_pass.pack(side="left", padx=8)

    def _build_conn(self):
        c = self._card(self.root, "Status")
        self.lbl_rfid = tk.Label(c, text="RFID: tidak merespons", bg=CARD_BG,
                                 fg=ERR, font=(FONT, 11, "bold"))
        self.lbl_rfid.pack(anchor="w", padx=10)
        self.lbl_uid = tk.Label(c, text="-", bg=CARD_BG, fg=MUTED,
                                font=(FONT, 9))
        self.lbl_uid.pack(anchor="w", padx=10)
        self.lbl_lcd = tk.Label(c, text="- / -", bg=CARD_BG, fg=MUTED,
                                font=(FONT, 10, "bold"))
        self.lbl_lcd.pack(anchor="w", padx=10, pady=(0, 6))

    def assign(self, st):
        if not st:
            return
        self.state    = st.get("state", self.state)
        self.pos      = st.get("pos", self.pos)
        self.front_cm = st.get("front", self.front_cm)
        self.vehicle  = st.get("vehicle", self.vehicle)
        self.lcd1     = st.get("lcd1", self.lcd1)
        self.lcd2     = st.get("lcd2", self.lcd2)
        self.masters  = st.get("masters", self.masters)
        self.pass_cm  = st.get("pass", self.pass_cm)
        self.rfid_ver  = st.get("rfid_ver", self.rfid_ver)
        self.rfid_uid  = st.get("last_uid", self.rfid_uid)
        self.rfid_auth = st.get("last_auth", self.rfid_auth)
        self.rfid_count = st.get("count", self.rfid_count)

    def render(self):
        # state
        sm = {"CLOSED": ("Tertutup", OK), "OPEN": ("Terbuka", ACCENT),
              "OPENING": ("Membuka", WARN), "CLOSING": ("Menutup", WARN)}
        t, col = sm.get(self.state, (self.state, ERR))
        self.lbl_state.config(text=t, fg=ACCENT)
        self.lbl_pos.config(text="%d" % self.pos)
        self.bar["value"] = (1.0 - max(0.0, min(1.0, self.pos / 120.0))) * 100.0

        # approach
        if self.front_cm < 0:
            self.lbl_dist.config(text="--- cm")
            self.bar_dist["value"] = 0.0
        else:
            self.lbl_dist.config(text="%d cm" % self.front_cm)
            self.bar_dist["value"] = (1.0 - min(1.0, max(0.0, self.front_cm / 30.0))) * 100.0
        if self.vehicle:
            self.lbl_vehicle.config(text="Kendaraan terdeteksi", fg=OK)
        else:
            self.lbl_vehicle.config(text="Jalur kosong", fg=GRAY)

        # pass
        self.lbl_pass.config(text="%s" % ("--- cm" if self.pass_cm < 0
                                          else "%d cm" % self.pass_cm))
        # rfid
        ok = self.rfid_ver not in ("0x00", "-", "")
        self.lbl_rfid.config(text=("RFID: siap (%s)" % self.rfid_ver) if ok
                             else "RFID: tidak merespons",
                             fg=OK if ok else ERR)
        self.lbl_uid.config(text="kartu: %s (auth: %s, %d total)" %
                            (self.rfid_uid, self.rfid_auth, self.rfid_count))
        self.lbl_lcd.config(text="%s | %s" % (self.lcd1, self.lcd2))

    def log_tag(self, msg, tag="info"):
        self._log_q.put((msg, tag))

    def drain_log(self, log_w):
        while True:
            try:
                msg, tag = self._log_q.get_nowait()
            except queue.Empty:
                return
            log_w.config(state="normal")
            log_w.insert("end", msg + "\n", (tag,))
            log_w.see("end")
            log_w.config(state="disabled")


# ============================================================
#  THREAD SERIAL per unit
# ============================================================
class SerialReader:
    def __init__(self, panel, port):
        self.panel = panel
        self.port = port
        self.ser = None
        self._stop = False
        self._buf = b""

    def open(self):
        self.ser = serial.Serial(self.port, 115200, timeout=0.2)
        self.panel.log_tag("Terhubung ke %s" % self.port, tag="ok")

    def close(self):
        self._stop = True
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except serial.SerialException:
                pass

    def run(self):
        while not self._stop:
            if self.ser is None or not self.ser.is_open:
                time.sleep(0.2)
                continue
            try:
                data = self.ser.read(512)
            except (serial.SerialException, OSError, TypeError):
                self.panel.log_tag("Serial terputus.", tag="err")
                break
            if not data:
                continue
            self._buf += data
            while b"\n" in self._buf:
                line, self._buf = self._buf.split(b"\n", 1)
                txt = line.decode(errors="replace").strip()
                if txt.startswith("ST|"):
                    st = parse_st(txt)
                    if st:
                        self.panel.assign(st)
                        self.panel.log_tag(txt, tag="info")
                elif txt.startswith(">"):
                    tag = "err" if ("DENIED" in txt or "gagal" in txt
                                    or "NO VEHICLE" in txt) else "info"
                    self.panel.log_tag(txt, tag=tag)


# ============================================================
#  APP — dua panel berdampingan
# ============================================================
class GateDualApp:
    def __init__(self, root):
        self.root = root
        self.readers = []
        self._buf_by_readers = {}

        root.title("All-in-One — Gate Control (ENTRY & EXIT)")
        root.configure(bg=WIN_BG)

        top = tk.Frame(root, bg=WIN_BG)
        top.pack(fill="x", padx=10, pady=(10, 4))
        tk.Label(top, text="Gate All-in-One — 2 unit dalam 1 window",
                 bg=WIN_BG, fg=TEXT, font=(FONT, 14, "bold")).pack(anchor="w")
        tk.Label(top, text="ENTRY kiri · EXIT kanan — 2 koneksi serial terpisah.",
                 bg=WIN_BG, fg=MUTED, font=(FONT, 10)).pack(anchor="w")

        ctrl = tk.Frame(root, bg=WIN_BG)
        ctrl.pack(fill="x", padx=10)
        self.lbl_foot = tk.Label(ctrl, text="", bg=WIN_BG, fg=MUTED,
                                 font=(FONT, 9))
        self.lbl_foot.pack(side="left")
        tk.Label(ctrl, text="ANPR: %s" % (
            "AKTIF (ENV GATE_DUAL_ANPR=1)" if os.environ.get("GATE_DUAL_ANPR") == "1"
            else "nonaktif — set GATE_DUAL_ANPR=1 utk nyalakan"),
            bg=WIN_BG, fg=(OK if os.environ.get("GATE_DUAL_ANPR") == "1" else WARN),
            font=(FONT, 9)).pack(side="right")

        body = tk.Frame(root, bg=WIN_BG)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=WIN_BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        right = tk.Frame(body, bg=WIN_BG)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        self.lbl_pl_port = {}
        # Pemetakan PORT — diverifikasi lewat boot log masing-masing board
        # (kirim reset DTR lalu baca "> UNIT: ..."):
        #   ttyUSB0 = unit ENTRY
        #   ttyUSB1 = unit EXIT
        ports = list_ports()
        self.panel_entry = UnitPanel(left, "ENTRY")
        self.panel_exit  = UnitPanel(right, "EXIT")

        self.port_entry = tk.StringVar(
            value=ports[0] if ports else "")
        self.port_exit = tk.StringVar(
            value=ports[1] if len(ports) > 1 else (ports[0] if ports else ""))
        self.port_combo_entry = self._mk_port_select(self.root, self.port_entry,
                                                     "ENTRY")
        self.port_combo_exit  = self._mk_port_select(self.root, self.port_exit,
                                                     "EXIT")

        self.log_q = queue.Queue()
        self.log_w = scrolledtext.ScrolledText(
            self.root, height=8, relief="flat", borderwidth=0, bg=CARD_BG2,
            fg=TEXT, wrap="none", state="disabled", font=(FONT, 9))
        self.log_w.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self._open_entry = True
        self._open_exit = True
        if os.environ.get("GATE_DUAL_ANPR") == "1":
            try:
                from anpr.plate_service import AnprService
                self._anpr = AnprService()
                from anpr.camera_source import CameraSource
                from anpr.config import CAMERA_SOURCE_2
                self._cam2 = CameraSource(CAMERA_SOURCE_2)
                self._anpr_on = True
            except Exception as e:
                self._anpr = None
                self._anpr_on = False
                self.lbl_foot.config(
                    text="ANPR mati: %s" % e, fg=ERR)
        else:
            self._anpr = None
            self._anpr_on = False
            self.lbl_foot.config(
                text="(GATE_DUAL_ANPR=1 untuk nyalakan ANPR+kamera)",
                fg=MUTED)

        self._toggle("ENTRY")
        self._toggle("EXIT")
        self.root.after(120, self._poll)

    def _mk_port_select(self, parent, var, unit):
        f = tk.Frame(parent, bg=WIN_BG)
        f.pack(fill="x", padx=10, pady=(0, 2))
        tk.Label(f, text=unit + ":", bg=WIN_BG, fg=MUTED,
                 font=(FONT, 10)).pack(side="left")
        cb = ttk.Combobox(f, textvariable=var, state="readonly",
                          values=list_ports(), width=16)
        cb.pack(side="left", padx=4)
        ttk.Button(f, text="Hubungkan %s" % unit,
                   command=lambda u=unit: self._toggle(u)).pack(side="left", padx=4)
        return cb

    def _toggle(self, unit):
        panel = self.panel_entry if unit == "ENTRY" else self.panel_exit
        existing = next((r for r in self.readers if r.panel is panel), None)
        if existing:
            existing.close()
            if existing in self.readers:
                self.readers.remove(existing)
            panel.log_tag("Diputuskan.", tag="info")
            return
        port = (self.port_entry if unit == "ENTRY" else self.port_exit).get()
        if not port:
            panel.log_tag("Pilih port dulu.", tag="warn")
            return
        try:
            rd = SerialReader(panel, port)
            rd.open()
        except serial.SerialException as e:
            panel.log_tag("Koneksi gagal: %s" % e, tag="err")
            return
        self.readers.append(rd)
        threading.Thread(target=rd.run, daemon=True).start()
        panel.log_tag("Thread %s dimulai." % unit, tag="ok")

    def _poll(self):
        for rd in self.readers:
            rd.panel.render()
            rd.panel.drain_log(self.log_w)
        self.root.after(120, self._poll)


def main():
    root = tk.Tk()
    GateDualApp(root)

    def _shot():
        try:
            import subprocess
            subprocess.run(["import", "-window", "root", "/tmp/gate_dual_shot.png"],
                           env={**os.environ, "DISPLAY": ":0"}, timeout=6,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    root.after(5000, _shot)
    root.mainloop()


if __name__ == "__main__":
    main()
