#!/usr/bin/env python3
"""
Simulasi Smart Gate (port logika dari src/main.cpp) — tanpa hardware.

Jalankan (wajib python3.11 karena memiliki tkinter):
    python3.11 sim/gate_sim.py

GUI menggantikan LCD 16x2 (tidak ada LCD fisik) dan tidak memakai button TUTUP
(penutupan terjadi otomatis lewat auto-close). Tombol BUKA (GPIO4) tetap ada
sebagai cadangan manual.

Tes logika tanpa GUI:
    python3.11 sim/gate_sim.py --selftest
"""

import math
import random
import time
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext

# --- Konstanta paritas dengan main.cpp ---
VEHICLE_CM = 30
MAX_VALID_CM = 60
NEAR_COUNT = 3
OBSTACLE_CM = 15
STEP_DELAY_MS = 15
MSG_DURATION_MS = 2000
RAUTH_DURATION_MS = 2500
DIST_INTERVAL_MS = 150
LCD_UPDATE_MS = 300
TICK_MS = 30


class GateSystem:
    """Mesin state gate: port dari logika src/main.cpp."""

    def __init__(self, auto_close_ms=10000):
        self.auto_close_ms = auto_close_ms
        self.state = "CLOSED"
        self.pos = 90.0
        self.open_since_ms = 0.0
        self.close_requested = False
        self.auth_result = False
        self.auth_until_ms = 0.0
        self.reject_until_ms = 0.0
        self.master_uid = None
        self.sim_dist = None
        self.dist = -1.0
        self.vehicle_near = False
        self.near_streak = 0
        self.last_dist_ms = 0.0
        self.lcd_row1 = "Gate: CLOSED"
        self.lcd_row2 = "SCAN MASTER CARD"
        self._now = 0.0
        self.logs = []

    # ---------- dukungan ----------
    def log(self, msg):
        self.logs.append(msg)
        if len(self.logs) > 500:
            del self.logs[:250]

    @staticmethod
    def _fmt_uid(uid):
        return " ".join("%02X" % b for b in uid)

    def _gen_uid(self):
        return tuple(random.randrange(256) for _ in range(4))

    # ---------- input (dipanggil GUI/selftest) ----------
    def set_sim_dist(self, value):
        self.sim_dist = value

    def press_open(self):
        self._open_gate()

    def scan_master(self):
        if self.master_uid is None:
            self.master_uid = self._gen_uid()
            self.log("> Master card set: UID: " + self._fmt_uid(self.master_uid))
            return
        self._auth(self.master_uid)

    def scan_other(self):
        uid = self._gen_uid()
        while uid == self.master_uid:
            uid = self._gen_uid()
        self._auth(uid)

    # ---------- logika (port main.cpp) ----------
    def _update_dist(self):
        s = self.sim_dist
        if s is None or s > MAX_VALID_CM:
            self.dist = -1.0
            self.near_streak = 0
            self.vehicle_near = False
            return
        self.dist = float(s)
        if self.dist <= VEHICLE_CM:
            self.near_streak += 1
            if self.near_streak >= NEAR_COUNT:
                self.vehicle_near = True
        else:
            self.near_streak = 0
            self.vehicle_near = False

    def _open_gate(self):
        if self.state in ("OPEN", "OPENING"):
            return
        if not self.vehicle_near:
            self.log("> NO VEHICLE - rejected")
            self.reject_until_ms = self._now + MSG_DURATION_MS
            return
        self.log("> GATE OPEN")
        self.state = "OPENING"

    def _auth(self, uid):
        if uid == self.master_uid:
            self.auth_result = True
            self.log("> ACCESS GRANTED")
        else:
            self.auth_result = False
            self.log("> UNAUTHORIZED: UID: " + self._fmt_uid(uid))
        self.auth_until_ms = self._now + RAUTH_DURATION_MS
        if self.auth_result:
            self._open_gate()

    def _start_closing(self):
        self.close_requested = False
        self.log("> GATE CLOSING")
        self.state = "CLOSING"

    def tick(self, now_ms, dt_ms):
        self._now = now_ms

        if now_ms - self.last_dist_ms >= DIST_INTERVAL_MS:
            self.last_dist_ms = now_ms
            self._update_dist()

        if self.state == "OPEN":
            if not self.close_requested and now_ms - self.open_since_ms >= self.auto_close_ms:
                self.close_requested = True
                self.log("> Auto-close armed")
            if self.close_requested and not self.vehicle_near:
                self._start_closing()

        elif self.state == "OPENING":
            self.pos = max(0.0, self.pos - dt_ms / STEP_DELAY_MS)
            if self.pos <= 0.0:
                self.state = "OPEN"
                self.pos = 0.0
                self.open_since_ms = now_ms

        elif self.state == "CLOSING":
            d = self.dist
            if d >= 0 and d < OBSTACLE_CM:
                self.log("> OBSTACLE! Reopen")
                self.state = "OPENING"
                self.close_requested = False
            else:
                self.pos = min(90.0, self.pos + dt_ms / STEP_DELAY_MS)
                if self.pos >= 90.0:
                    self.state = "CLOSED"
                    self.pos = 90.0
                    self.log("> GATE CLOSED")

        self._update_lcd()

    def _update_lcd(self):
        self.lcd_row1 = "Gate: " + self.state
        msg = None
        if self._now < self.reject_until_ms:
            msg = "NO VEHICLE!"
        elif self._now < self.auth_until_ms:
            msg = "ACCESS GRANTED" if self.auth_result else "UNAUTHORIZED"
        elif self.state == "OPEN" and self.close_requested and self.vehicle_near:
            msg = "WAIT VEHICLE!"
        elif self.state == "OPENING":
            msg = "OPENING..."
        elif self.state == "CLOSING":
            msg = "CLOSING..."
        if msg is not None:
            self.lcd_row2 = msg.ljust(16)[:16]
        else:
            v = "V:YES " if self.vehicle_near else "V:NO  "
            dd = "---" if self.dist < 0 else ("%dcm " % self.dist)
            self.lcd_row2 = (v + dd).ljust(16)[:16]


class GateSimApp:
    def __init__(self, root):
        self.root = root
        self.sys = GateSystem()
        self._last_tick = time.monotonic()

        root.title("Simulasi Smart Gate (ESP32) — pengganti LCD")
        root.configure(bg="#282c34")

        self._build_layout()
        self._last_id = root.after(0, self._loop)

    # ---------- layout ----------
    def _build_layout(self):
        pad = {"padx": 8, "pady": 4}

        top = ttk.Frame(self.root)
        top.pack(fill="x", **pad)
        ttk.Label(top, text="Simulasi Smart Gate — port src/main.cpp",
                  font=("DejaVu Sans", 14, "bold")).pack(side="left")

        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True, **pad)

        # Kiri: visual gate + status
        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(left, width=360, height=240, bg="#dce3ea",
                                highlightthickness=0)
        self.canvas.pack(pady=4)
        self.canvas.create_rectangle(0, 230, 360, 240, fill="#7a8494", outline="")
        self.canvas.create_oval(56, 184, 66, 194, fill="#4a5568", outline="")
        self.arm = self.canvas.create_line(0, 0, 0, 0, width=14, capstyle="round")
        self.state_tag = self.canvas.create_text(180, 20, font=("DejaVu Sans", 12, "bold"),
                                                 anchor="n")

        grid = ttk.Frame(left)
        grid.pack(fill="x", pady=4)
        self.lbl_state = self._row(grid, 0, "State")
        self.lbl_servo = self._row(grid, 1, "Servo")
        self.lbl_vehicle = self._row(grid, 2, "Kendaraan")
        self.lbl_dist = self._row(grid, 3, "Jarak")
        self.lbl_timer = self._row(grid, 4, "Timer tutup")
        self.lbl_master = self._row(grid, 5, "Master UID")

        # LCD 16x2 panel pengganti
        lcd_frame = ttk.LabelFrame(left, text="LCD 16x2 (diganti GUI)")
        lcd_frame.pack(fill="x", pady=4)
        self.lcd_row1 = tk.Label(lcd_frame, text="Gate: CLOSED", font=("Courier", 16, "bold"),
                                 fg="#00ff85", bg="#002b1a", anchor="w", width=16)
        self.lcd_row1.pack(fill="x", padx=4, pady=(4, 1))
        self.lcd_row2 = tk.Label(lcd_frame, text="SCAN MASTER CARD", font=("Courier", 16, "bold"),
                                 fg="#00ff85", bg="#002b1a", anchor="w", width=16)
        self.lcd_row2.pack(fill="x", padx=4, pady=(1, 4))

        # Kanan: kontrol + log
        right = ttk.Frame(main)
        right.pack(side="right", fill="y")

        ctrl = ttk.LabelFrame(right, text="Kontrol")
        ctrl.pack(fill="x", pady=4)

        self.dist_var = tk.DoubleVar(value=80)
        ttk.Label(ctrl, text="Jarak objek depan sensor (cm)").pack(anchor="w")
        self.dist_scale = ttk.Scale(ctrl, from_=0, to=100, variable=self.dist_var,
                                    command=lambda _v: self._dist_changed())
        self.dist_scale.pack(fill="x")
        self.dist_lbl = ttk.Label(ctrl, text="")
        self.dist_lbl.pack(anchor="w")
        self._dist_changed()

        ttk.Label(ctrl, text="(nilai > 60cm = tidak terdeteksi / noise)").pack(anchor="w", pady=(0, 6))

        ttk.Button(ctrl, text="Tap Kartu MASTER (RFID)",
                   command=self.sys.scan_master).pack(fill="x", pady=2)
        ttk.Button(ctrl, text="Tap Kartu ASING (RFID)",
                   command=self.sys.scan_other).pack(fill="x", pady=2)
        ttk.Button(ctrl, text="Tombol BUKA (cadangan)",
                   command=self.sys.press_open).pack(fill="x", pady=2)

        ttk.Label(ctrl, text="Auto-close:").pack(anchor="w", pady=(8, 0))
        self.ac_var = tk.StringVar(value="10 detik")
        ac = ttk.Combobox(ctrl, textvariable=self.ac_var, state="readonly", width=10,
                          values=["3 detik", "5 detik", "10 detik", "20 detik"])
        ac.pack(anchor="w")
        ac.bind("<<ComboboxSelected>>", self._ac_changed)

        log_frame = ttk.LabelFrame(right, text="Serial monitor (debug)")
        log_frame.pack(fill="both", expand=True, pady=4)
        self.log = scrolledtext.ScrolledText(log_frame, height=14, state="disabled",
                                             font=("DejaVu Sans Mono", 9))
        self.log.pack(fill="both", expand=True)

    def _row(self, parent, r, label):
        ttk.Label(parent, text=label, width=14).grid(row=r, column=0, sticky="w")
        val = ttk.Label(parent, text="-", font=("DejaVu Sans Mono", 10, "bold"))
        val.grid(row=r, column=1, sticky="w", padx=8)
        return val

    # ---------- interaksi ----------
    def _dist_changed(self):
        v = self.dist_scale.get()
        self.dist_lbl.config(text="%.0f cm" % v)
        sim = None if v > MAX_VALID_CM else v
        self.sys.set_sim_dist(sim)

    def _ac_changed(self, _e):
        mm = {"3 detik": 3000, "5 detik": 5000, "10 detik": 10000, "20 detik": 20000}
        self.sys.auto_close_ms = mm.get(self.ac_var.get(), 10000)
        self.sys.log("> Auto-close diubah ke " + self.ac_var.get())

    # ---------- loop ----------
    def _loop(self):
        now = time.monotonic()
        dt_ms = (now - self._last_tick) * 1000.0
        self._last_tick = now
        self.sys.tick(now * 1000.0, dt_ms)
        self._render()
        self.root.after(TICK_MS, self._loop)

    def _render(self):
        s = self.sys
        colors = {"CLOSED": "#e34c4c", "OPEN": "#3fb950", "OPENING": "#e3a04c",
                  "CLOSING": "#e3a04c"}
        color = colors.get(s.state, "#cccccc")

        rad = math.radians(s.pos)
        cx, cy, r = 61.0, 189.0, 130.0
        x2 = cx + r * math.sin(rad)
        y2 = cy - r * math.cos(rad)
        self.canvas.coords(self.arm, cx, cy, x2, y2)
        self.canvas.itemconfig(self.arm, fill=color)
        self.canvas.itemconfig(self.state_tag, text=s.state, fill=color)

        self.lbl_state.config(text=s.state)
        self.lbl_servo.config(text="%d deg" % round(s.pos))
        self.lbl_vehicle.config(text="V:YES" if s.vehicle_near else "V:NO")
        self.lbl_dist.config(text="---" if s.dist < 0 else "%.0f cm" % s.dist)
        if s.state == "OPEN":
            remain = max(0.0, s.auto_close_ms - (self._now_ms() - s.open_since_ms))
            self.lbl_timer.config(text="%.1f s" % (remain / 1000.0))
        else:
            self.lbl_timer.config(text="-")
        self.lbl_master.config(text="—" if s.master_uid is None
                               else GateSystem._fmt_uid(s.master_uid))

        self.lcd_row1.config(text=s.lcd_row1)
        self.lcd_row2.config(text=s.lcd_row2)

        if s.logs:
            new = list(s.logs)
            s.logs.clear()
            self.log.config(state="normal")
            for line in new:
                self.log.insert("end", line + "\n")
            self.log.see("end")
            self.log.config(state="disabled")

    def _now_ms(self):
        return self._last_tick * 1000.0


# ---------- selftest logika (tanpa GUI) ----------
def selftest():
    f = {}
    ok = True

    def check(name, cond):
        nonlocal ok
        f[name] = bool(cond)
        ok = ok and bool(cond)

    s = GateSystem()
    t = 0.0

    def run(ms):
        nonlocal t
        end = t + ms
        while t < end:
            t += TICK_MS
            s.tick(t, TICK_MS)

    # 0. Set master kartu pertama
    s.set_sim_dist(None)
    run(200)
    s.scan_master()
    run(200)
    check("master set", s.master_uid is not None)

    # 1. Tanpa kendaraan: buka ditolak + pesan NO VEHICLE
    s.press_open()
    run(200)
    check("buka ditolak tanpa kendaraan", s.state == "CLOSED" and
          s.lcd_row2.startswith("NO VEHICLE"))
    run(MSG_DURATION_MS)
    check("LCD normal lagi", s.lcd_row2.startswith("V:NO"))

    # 2. Kendaraan dekat → scan kartu master → gate membuka
    s.set_sim_dist(10)
    run(600)
    check("kendaraan terdeteksi", s.vehicle_near and s.lcd_row2.startswith("V:YES"))
    s.scan_master()
    run(200)
    check("gate mulai buka", s.state in ("OPENING", "OPEN"))
    run(2000)
    check("gate OPEN", s.state == "OPEN")

    # 3. Kartu asing ditolak (tetap OPEN)
    s.scan_other()
    run(200)
    check("kartu asing ditolak", s.auth_result is False and
          s.lcd_row2.startswith("UNAUTHORIZED"))
    run(RAUTH_DURATION_MS)
    check("gate tetap OPEN", s.state == "OPEN")

    # 4. Auto-close: kendaraan lewat → menutup penuh
    s.set_sim_dist(None)
    run(200)
    rem = s.auto_close_ms - (t - s.open_since_ms)
    run(max(0, rem) + 100)
    check("auto-close mulai menutup", s.state == "CLOSING")
    run(2000)
    check("gate CLOSED", s.state == "CLOSED")

    # 5. Halangan saat menutup → buka kembali
    s.set_sim_dist(10)
    run(600)
    s.scan_master()
    run(2500)
    check("buka untuk tes halangan", s.state == "OPEN")
    s.set_sim_dist(None)
    run(200)
    rem = s.auto_close_ms - (t - s.open_since_ms)
    run(max(0, rem) + 100)
    check("closing untuk tes halangan", s.state == "CLOSING")
    s.set_sim_dist(8)
    run(300)
    check("halangan terdeteksi saat menutup", s.state in ("OPENING", "OPEN"))
    run(2500)
    check("gate membuka kembali", s.state == "OPEN")

    print("==== SELFTEST ====")
    for name, passed in f.items():
        print(("PASS  " if passed else "FAIL  ") + name)
    print("RESULT: " + ("ALL PASS" if ok else "SOME FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    root = tk.Tk()
    GateSimApp(root)
    root.mainloop()