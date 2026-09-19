#!/usr/bin/env python3
"""
GUI Smart Gate — terhubung ke ESP32 via serial (USB).

Desain bersih & responsif: layout menyesuaikan ukuran layar, informasi
padat namun jelas. Protokol ST (13 field):
  ST|<state>|<pos>|<dist>|<vehicle>|<lcdRow1>|<lcdRow2>|<masters>|<exitCm>|<rfidVer>|<lastUid>|<lastAuth>|<count>

Jalankan:
    python3.11 sim/gate_serial_gui.py
"""

import os
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import serial
import serial.tools.list_ports
from PIL import Image, ImageTk

from passage_log import PassageLog, ROOT

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

AUTO_CLOSE_S = 10.0
PLATE_VALIDATE_S = 14.0
POS_OPEN, POS_CLOSED = 30, 120

# ---- palet netral & bersih ----
WIN_BG = "#eef0f3"
CARD_BG = "#ffffff"
BORDER = "#dce0e5"
TEXT = "#20242a"
MUTED = "#5f6a76"
ACCENT = "#2f6fd0"
OK = "#16794c"
WARN = "#9a6b1f"
ERR = "#c0392b"
GRAY = "#8a94a0"


def list_ports():
    devices = [p.device for p in serial.tools.list_ports.comports()]
    usb = sorted(d for d in devices if "ttyUSB" in d or "ttyACM" in d or "rfcomm" in d)
    rest = sorted(d for d in devices if d not in usb and "ttyS" not in d)
    return usb + rest


class CaptureViewer:
    """Jendela riwayat capture: thumbnail dari data/captures + info dari gate.db."""
    def __init__(self, master, plog):
        self.plog = plog
        self._photos = []
        self.win = tk.Toplevel(master)
        self.win.title("Hasil Capture Kamera")
        self.win.configure(bg=WIN_BG)
        self.win.geometry("1000x600")
        self.win.minsize(720, 460)
        self._build()
        self.refresh()

    def _build(self):
        top = tk.Frame(self.win, bg=WIN_BG)
        top.pack(fill="x", padx=10, pady=(10, 4))
        tk.Label(top, text="Hasil Capture (data/captures) + riwayat access (gate.db)",
                 bg=WIN_BG, fg=TEXT, font=("DejaVu Sans", 11, "bold")).pack(side="left")
        self.lbl_count = tk.Label(top, text="", bg=WIN_BG, fg=MUTED,
                                  font=("DejaVu Sans", 9))
        self.lbl_count.pack(side="left", padx=10)
        ttk.Button(top, text="Segarkan", command=self.refresh).pack(side="right")

        body = tk.Frame(self.win, bg=WIN_BG)
        body.pack(fill="both", expand=True, padx=10, pady=(2, 10))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=CARD_BG, highlightbackground=BORDER,
                        highlightthickness=1)
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_rowconfigure(0, weight=1)
        self._canvas = tk.Canvas(left, bg=CARD_BG, highlightthickness=0)
        vsb = ttk.Scrollbar(left, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)
        self._grid_f = tk.Frame(self._canvas, bg=CARD_BG)
        self._grid_f.bind("<Configure>",
                          lambda e: self._canvas.configure(
                              scrollregion=self._canvas.bbox("all")))
        self._canvas.create_window((0, 0), window=self._grid_f, anchor="nw")

        right = tk.Frame(body, bg=CARD_BG, highlightbackground=BORDER,
                         highlightthickness=1)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)
        self.preview_lbl = tk.Label(right, text="Klik gambar di kiri untuk melihat",
                                    bg=CARD_BG, fg=MUTED, font=("DejaVu Sans", 10))
        self.preview_lbl.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self.meta_lbl = tk.Label(right, text="", bg=CARD_BG, fg=MUTED,
                                 font=("DejaVu Sans Mono", 9), justify="left",
                                 anchor="w", wraplength=380)
        self.meta_lbl.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))

    def refresh(self):
        for w in self._grid_f.winfo_children():
            w.destroy()
        self._photos = []
        if self.plog is None:
            tk.Label(self._grid_f, text="PassageLog tidak tersedia (%s)"
                     % getattr(self, "_plog_error", "?"), bg=CARD_BG, fg=ERR
                     ).pack(pady=20)
            return
        rows = self.plog.recent(40)
        self.lbl_count.config(text="%d catatan terakhir" % len(rows))
        if not rows:
            tk.Label(self._grid_f, text="Belum ada capture.",
                     bg=CARD_BG, fg=GRAY).pack(pady=20)
            return
        cols = 3
        for i, r in enumerate(rows):
            card = tk.Frame(self._grid_f, bg=CARD_BG, highlightbackground=BORDER,
                            highlightthickness=1)
            card.grid(row=i // cols, column=i % cols, sticky="nsew", padx=4, pady=4)
            self._grid_f.grid_columnconfigure(i % cols, weight=1)

            path = None
            rel = r.get("image_path")
            if rel:
                cand = ROOT / rel
                if cand.exists():
                    path = cand
            photo = None
            try:
                if path is not None:
                    im = Image.open(path)
                    im.thumbnail((150, 112))
                    photo = ImageTk.PhotoImage(im)
                    self._photos.append(photo)
                    img = tk.Label(card, image=photo, bg=CARD_BG, cursor="hand2")
                else:
                    img = tk.Label(card, text="(tanpa foto)", bg=CARD_BG, fg=GRAY,
                                   height=6, width=22)
            except Exception:
                img = tk.Label(card, text="(gambar rusak)", bg=CARD_BG, fg=ERR,
                               height=6, width=22)
            img.pack(padx=4, pady=(4, 0))
            txt = "%(ts)s\n%(method)s | %(uid)s\n%(plate)s\n%s" % (
                r, "IZIN" if r["allowed"] else "TOLAK")
            tk.Label(card, text=txt, bg=CARD_BG, fg=TEXT,
                     font=("DejaVu Sans Mono", 8), justify="left").pack(
                padx=4, pady=(0, 4))
            img.bind("<Button-1>", lambda e, rr=r, pth=path: self._show(rr, pth))

    def _show(self, r, path):
        self.preview_lbl.configure(image="", text="")
        if path is not None and path.exists():
            try:
                im = Image.open(path)
                im.thumbnail((540, 430))
                photo = ImageTk.PhotoImage(im)
                self.preview_lbl.configure(image=photo, text="")
                self.preview_lbl.image = photo
            except Exception as e:
                self.preview_lbl.configure(image="", text="Gagal buka: %s" % e)
        else:
            self.preview_lbl.configure(image="", text="(tidak ada foto)")
        self.meta_lbl.config(text="%s\nMetode: %s\nArah: %s\nUID: %s\nPlat: %s\n"
                             "Hasil: %s\ngate.db#%d"
                             % (r["ts"], r["method"], r["direction"],
                                r["uid"], r["plate"],
                                "IZIN" if r["allowed"] else "TOLAK",
                                r["id"]))


class GateSerialApp:
    def __init__(self, root):
        self.root = root
        self.ser = None
        self._buf = b""
        self._open_since_local = None
        self._app_start = time.monotonic()

        self.state = "CLOSED"
        self.pos = POS_CLOSED
        self.dist = -1
        self.vehicle_near = False
        self.lcd_row1 = "Gate: CLOSED"
        self.lcd_row2 = "SCAN MASTER CARD"
        self.master_uid = "-"
        self.master_count = 0
        self.exit_cm = -1
        self.rfid_ver = "0x00"
        self.rfid_last_uid = "-"
        self.rfid_last_auth = '-'
        self._rfid_last_uid_seen = None

        # validasi plat (RFID + ANPR dua-lapis)
        self._plate_pending = False
        self._plate_pending_until = 0.0

        # pelacak perubahan untuk Log Sistem
        self._prev_state = self.state
        self._prev_vehicle = False
        self._prev_row2 = None
        self._prev_masters = None
        self._syswin = None
        self._sys_text = None
        self._capwin = None
        self._last_st_ms = None
        self._heartbeat_off = False

        root.title("Gate Control")
        self._apply_styles()
        self._size_to_screen()

        self._anpr = None
        self._anpr_error = None
        self._anpr_q = queue.Queue()
        self._log_q = queue.Queue()
        try:
            from anpr.plate_service import AnprService
            self._anpr = AnprService()
        except Exception as e:
            self._anpr_error = str(e)

        self._plog = None
        self._plog_error = None
        try:
            self._plog = PassageLog()
        except Exception as e:
            self._plog_error = str(e)

        self._preview_lock = threading.Lock()
        self._preview_pil = None
        self._preview_bgr = None
        self._preview_seq = 0
        self._preview_img = None
        self._overlay = None
        self._preview_stop = False
        self._preview_w, self._preview_h = 368, 276
        self._cam_source_sync = ""
        if self._anpr is not None:
            threading.Thread(target=self._preview_loop, daemon=True).start()

        self._build_layout()
        self._poll()
        self.root.after(400, self._auto_connect)

    # ---------------------------------------------------------------- setup
    def _size_to_screen(self):
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        w = min(max(sw - 80, 760), 1260)
        h = min(max(sh - 120, 540), 820)
        self.root.geometry("%dx%d" % (w, h))
        self.root.minsize(760, 520)

    def _apply_styles(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=WIN_BG, foreground=TEXT)
        style.configure("TFrame", background=WIN_BG)
        style.configure("Card.TFrame", background=CARD_BG)
        style.configure("TLabel", background=WIN_BG, foreground=TEXT)
        style.configure("Card.TLabel", background=CARD_BG, foreground=TEXT)
        style.configure("Caption.TLabel", background=WIN_BG, foreground=MUTED)
        style.configure("CardCaption.TLabel", background=CARD_BG, foreground=MUTED)
        style.configure("Value.TLabel", font=("DejaVu Sans", 11, "bold"))
        style.configure("CardValue.TLabel", background=CARD_BG, font=("DejaVu Sans", 11, "bold"))
        style.configure("Big.TLabel", background=WIN_BG, font=("DejaVu Sans", 20, "bold"))
        style.configure("BigCard.TLabel", background=CARD_BG, font=("DejaVu Sans", 20, "bold"))

        style.configure("TButton", padding=(10, 6))
        style.configure("Primary.TButton", foreground="#ffffff", background=ACCENT,
                        padding=(12, 7), font=("DejaVu Sans", 10, "bold"))
        style.map("Primary.TButton",
                  background=[("active", "#3f7fd6"), ("pressed", "#22599e")])
        style.configure("TLabelframe", background=CARD_BG, bordercolor=BORDER,
                        relief="solid", borderwidth=1)
        style.configure("TLabelframe.Label", background=CARD_BG, foreground=TEXT,
                        font=("DejaVu Sans", 10, "bold"))

        style.configure("Clean.Horizontal.TProgressbar",
                        troughcolor="#e6e9ed", background=ACCENT,
                        bordercolor="#e6e9ed", lightcolor=ACCENT,
                        darkcolor=ACCENT, thickness=8)
        style.map("Clean.Horizontal.TProgressbar",
                  background=[("disabled", "#e6e9ed")])

        style.configure("Vertical.TScrollbar", background="#d7dbe1",
                        troughcolor=CARD_BG, bordercolor=CARD_BG,
                        arrowcolor=TEXT)

    def _card(self, parent, title):
        f = tk.Frame(parent, bg=CARD_BG, highlightbackground=BORDER,
                     highlightthickness=1)
        tk.Label(f, text=title, bg=CARD_BG, fg=MUTED, anchor="w",
                 font=("DejaVu Sans", 10, "bold")).pack(anchor="w",
                                                        padx=10, pady=(8, 2))
        return f

    # ---------------------------------------------------------------- layout
    def _build_layout(self):
        self.root.grid_rowconfigure(3, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self._build_header()
        self._build_status_row()
        self._build_display_strip()
        self._build_main()
        self._build_anpr_frame()

    def _build_display_strip(self):
        d = tk.Frame(self.root, bg=CARD_BG, highlightbackground=BORDER,
                     highlightthickness=1)
        d.grid(row=2, column=0, sticky="ew", padx=10, pady=(2, 2))
        d.grid_columnconfigure(0, weight=1)
        d.grid_columnconfigure(1, weight=1)
        tk.Label(d, text="Display firmware (baris 1):", bg=CARD_BG, fg=MUTED,
                 font=("DejaVu Sans", 10, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(6, 0))
        tk.Label(d, text="Display firmware (baris 2):", bg=CARD_BG, fg=MUTED,
                 font=("DejaVu Sans", 10, "bold")).grid(row=0, column=1, sticky="w", padx=10, pady=(6, 0))
        self.lbl_disp1 = tk.Label(d, text=self.lcd_row1, bg=CARD_BG, fg=TEXT,
                                  font=("DejaVu Sans Mono", 12, "bold"))
        self.lbl_disp1.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 6))
        self.lbl_disp2 = tk.Label(d, text=self.lcd_row2, bg=CARD_BG, fg=TEXT,
                                  font=("DejaVu Sans Mono", 12, "bold"))
        self.lbl_disp2.grid(row=1, column=1, sticky="w", padx=12, pady=(0, 6))

    def _build_header(self):
        h = tk.Frame(self.root, bg=WIN_BG)
        h.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))
        h.grid_columnconfigure(20, weight=1)

        tk.Label(h, bg=WIN_BG, text="Gate Control", fg=TEXT,
                 font=("DejaVu Sans", 15, "bold")).grid(row=0, column=0, sticky="w")
        self.lbl_conn = tk.Label(h, bg=WIN_BG, text="Terputus", fg=MUTED,
                                 font=("DejaVu Sans", 10))
        self.lbl_conn.grid(row=0, column=2, sticky="w", padx=12)

        self.port_var = tk.StringVar(value="")
        self.port_combo = ttk.Combobox(h, textvariable=self.port_var, width=16,
                                       state="readonly", values=list_ports())
        self.port_combo.grid(row=0, column=21, sticky="e", padx=3)
        ttk.Button(h, text="Refresh", width=8, command=self._refresh_ports)\
            .grid(row=0, column=22, sticky="e", padx=3)
        self.btn_conn = ttk.Button(h, text="Hubungkan", command=self._toggle_conn)
        self.btn_conn.grid(row=0, column=23, sticky="e", padx=3)

    def _build_status_row(self):
        row = tk.Frame(self.root, bg=WIN_BG)
        row.grid(row=1, column=0, sticky="ew", padx=10, pady=(2, 4))
        row.grid_columnconfigure(0, weight=1, minsize=300)
        row.grid_columnconfigure(1, weight=1, minsize=280)
        row.grid_columnconfigure(2, weight=1, minsize=300)

        # ---- GATE ----
        g = self._card(row, "Status Gerbang")
        g.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self.lbl_state = tk.Label(g, text="Tertutup", bg=CARD_BG, fg=OK,
                                  font=("DejaVu Sans", 20, "bold"))
        self.lbl_state.pack(anchor="w", padx=10)
        info = tk.Frame(g, bg=CARD_BG); info.pack(fill="x", padx=10, pady=(6, 4))
        self._pos_lbl = self._kv(info, 0, "Posisi", "120")
        self.bar_pos = self._mk_bar(g)
        self._auto_lbl = self._kv(info, 1, "Auto-tutup", "-")
        self._auto_bar = self._mk_bar(g)

        # ---- SENSOR ----
        s = self._card(row, "Sensor")
        s.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        self.lbl_kendaraan = tk.Label(s, text="Jalur kosong", bg=CARD_BG, fg=GRAY,
                                      font=("DejaVu Sans", 12, "bold"))
        self.lbl_kendaraan.pack(anchor="w", padx=10)
        self.lbl_dist = tk.Label(s, text="--- cm", bg=CARD_BG, fg=TEXT,
                                 font=("DejaVu Sans", 17, "bold"))
        self.lbl_dist.pack(anchor="w", padx=10, pady=(4, 0))
        self.bar_dist = self._mk_bar(s)
        exitf = tk.Frame(s, bg=CARD_BG); exitf.pack(anchor="w", padx=10, pady=(4, 6))
        tk.Label(exitf, text="Exit sensor: ", bg=CARD_BG, fg=MUTED,
                 font=("DejaVu Sans", 10)).pack(side="left")
        self.lbl_exit = tk.Label(exitf, text="--- cm", bg=CARD_BG, fg=TEXT,
                                 font=("DejaVu Sans", 10))
        self.lbl_exit.pack(side="left")

        # ---- RFID ----
        r = self._card(row, "RFID")
        r.grid(row=0, column=2, sticky="nsew", padx=4, pady=4)
        self.lbl_rfid = tk.Label(r, text="Tidak merespons", bg=CARD_BG, fg=ERR,
                                 font=("DejaVu Sans", 12, "bold"))
        self.lbl_rfid.pack(anchor="w", padx=10)
        self.lbl_ver = tk.Label(r, text="versi 0x00", bg=CARD_BG, fg=MUTED,
                                font=("DejaVu Sans", 10))
        self.lbl_ver.pack(anchor="w", padx=10, pady=(2, 0))
        masterf = tk.Frame(r, bg=CARD_BG); masterf.pack(anchor="w", padx=10, pady=(8, 0))
        tk.Label(masterf, text="Master:", bg=CARD_BG, fg=MUTED,
                 font=("DejaVu Sans", 10)).pack(side="left")
        self.lbl_master = tk.Label(masterf, text="-", bg=CARD_BG, fg=TEXT,
                                   font=("DejaVu Sans Mono", 11, "bold"))
        self.lbl_master.pack(side="left", padx=6)
        scanf = tk.Frame(r, bg=CARD_BG); scanf.pack(anchor="w", padx=10, pady=(8, 2))
        tk.Label(scanf, text="Scan:", bg=CARD_BG, fg=MUTED,
                 font=("DejaVu Sans", 10)).pack(side="left")
        self.lbl_scan = tk.Label(scanf, text="-", bg=CARD_BG, fg=GRAY,
                                 font=("DejaVu Sans Mono", 10))
        self.lbl_scan.pack(side="left", padx=6)
        self.lbl_count = tk.Label(r, text="", bg=CARD_BG, fg=MUTED,
                                  font=("DejaVu Sans", 9))
        self.lbl_count.pack(anchor="w", padx=10, pady=(2, 0))
        self.lbl_rfid_hint = tk.Label(r, text="", bg=CARD_BG, fg=ACCENT, wraplength=280,
                                      justify="left", font=("DejaVu Sans", 9, "bold"))
        self.lbl_rfid_hint.pack(anchor="w", padx=10, pady=(6, 0))
        tk.Label(r, text="Multi-master: kartu pertama otomatis,\ntambah lagi lewat tombol Tambah Master.\nSaat tap, kendaraan (sensor ENTRY) wajib ada\ndulu sebelum gerbang dibuka.",
                 bg=CARD_BG, fg=GRAY, font=("DejaVu Sans", 9), justify="left").pack(anchor="w", padx=10, pady=(6, 6))

    def _kv(self, parent, row, key, value):
        tk.Label(parent, text=key + ":", bg=CARD_BG, fg=MUTED,
                 font=("DejaVu Sans", 10)).grid(row=row, column=0, sticky="w")
        lv = tk.Label(parent, text=value, bg=CARD_BG, fg=TEXT,
                      font=("DejaVu Sans", 10, "bold"))
        lv.grid(row=row, column=1, sticky="w", padx=(8, 0), pady=1)
        return lv

    def _mk_bar(self, parent):
        b = ttk.Progressbar(parent, style="Clean.Horizontal.TProgressbar",
                            maximum=100, value=0)
        b.pack(fill="x", padx=10, pady=(2, 0))
        return b

    def _build_main(self):
        main = tk.Frame(self.root, bg=WIN_BG)
        main.grid(row=3, column=0, sticky="nsew", padx=10, pady=(2, 6))
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(0, weight=1)

        left = tk.Frame(main, bg=WIN_BG)
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        controls = tk.Frame(left, bg=WIN_BG)
        controls.grid(row=0, column=0, sticky="ew")
        buttons = [
            ("Buka Gate", self._send_open, "Primary.TButton"),
            ("Tutup Sekarang", self._send_close, "TButton"),
            ("Minta Tutup", self._send_reqclose, "TButton"),
            ("Test Buka", self._send_testopen, "TButton"),
            ("Test Tutup", self._send_testclosed, "TButton"),
        ]
        for i, (label, cmd, stl) in enumerate(buttons):
            b = ttk.Button(controls, text=label, command=cmd)
            if stl != "TButton":
                b.config(style=stl)
            b.grid(row=0, column=2 + i, sticky="ew", padx=3, pady=3)
            controls.grid_columnconfigure(2 + i, weight=1)
        buttons2 = [
            ("Lihat Capture", self._toggle_capture_viewer, "TButton"),
            ("Tambah Master", self._send_addmode, "TButton"),
            ("Hapus Master", self._send_delmode, "TButton"),
            ("Daftar Master", self._send_list, "TButton"),
            ("Hapus Semua", self._send_clear, "TButton"),
            ("Log Sistem", self._toggle_syslog, "TButton"),
        ]
        for i, (label, cmd, stl) in enumerate(buttons2):
            b = ttk.Button(controls, text=label, command=cmd)
            if stl != "TButton":
                b.config(style=stl)
            b.grid(row=1, column=2 + i, sticky="ew", padx=3, pady=(0, 3))
            controls.grid_columnconfigure(2 + i, weight=1)

        logf = tk.Frame(left, bg=CARD_BG, highlightbackground=BORDER,
                        highlightthickness=1)
        logf.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        logf.grid_rowconfigure(1, weight=1)
        logf.grid_columnconfigure(0, weight=1)
        tk.Label(logf, text="Log", bg=CARD_BG, fg=MUTED, anchor="w",
                 font=("DejaVu Sans", 10, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))
        logf.grid_columnconfigure(2, weight=1)
        ttk.Button(logf, text="Bersihkan", width=10,
                   command=self._log_clear).grid(row=0, column=3, sticky="e", padx=8, pady=(6, 0))
        txtbox = tk.Frame(logf, bg=CARD_BG)
        txtbox.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        txtbox.grid_rowconfigure(0, weight=1)
        txtbox.grid_columnconfigure(0, weight=1)
        self.log_w = tk.Text(txtbox, state="disabled", relief="flat", borderwidth=0,
                             bg=CARD_BG, fg=TEXT, font=("DejaVu Sans Mono", 9),
                             wrap="none", height=10)
        self.log_w.grid(row=0, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(txtbox, orient="vertical", command=self.log_w.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = ttk.Scrollbar(txtbox, orient="horizontal", command=self.log_w.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        self.log_w.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.log_w.tag_configure("ok", foreground=OK)
        self.log_w.tag_configure("err", foreground=ERR)
        self.log_w.tag_configure("warn", foreground=WARN)
        self.log_w.tag_configure("info", foreground=GRAY)

    def _build_anpr_frame(self):
        af = ttk.LabelFrame(self.root, text="ANPR (kamera) — alternatif selain RFID")
        af.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 8))
        af.grid_columnconfigure(0, weight=1)

        row0 = ttk.Frame(af)
        row0.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 2))
        self.anpr_on = tk.BooleanVar(value=False)
        ttk.Checkbutton(row0, text="Aktif ANPR", variable=self.anpr_on,
                        command=self._anpr_toggle).pack(side="left")
        ttk.Label(row0, text="Sumber:", style="Card.TLabel").pack(side="left", padx=(14, 2))
        from anpr.config import CAMERA_SOURCE
        self.anpr_source = tk.StringVar(value=CAMERA_SOURCE)
        self._cam_source_sync = CAMERA_SOURCE
        ttk.Entry(row0, textvariable=self.anpr_source, width=40).pack(side="left")
        self.btn_scan = ttk.Button(row0, text="Scan Plat", command=self._anpr_scan,
                                   state="disabled")
        self.btn_scan.pack(side="left", padx=10)

        self.lbl_anpr = ttk.Label(af, text=self._anpr_status_text(), style="CardCaption.TLabel",
                                  anchor="w")
        self.lbl_anpr.grid(row=1, column=0, sticky="ew", padx=8, pady=(2, 2))

        pv = ttk.Frame(af)
        pv.grid(row=2, column=0, sticky="ew", padx=8, pady=(2, 6))
        pv.grid_columnconfigure(0, weight=1)
        pv.grid_columnconfigure(1, weight=1)
        pv1 = tk.Frame(pv, bg="#f6f7f9", highlightbackground=BORDER, highlightthickness=1)
        pv1.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        pv2 = tk.Frame(pv, bg="#f6f7f9", highlightbackground=BORDER, highlightthickness=1)
        pv2.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        tk.Label(pv1, text="Kamera ANPR", bg="#f6f7f9", fg=MUTED,
                 font=("DejaVu Sans", 9, "bold")).pack(anchor="w", padx=6, pady=(4, 0))
        tk.Label(pv2, text="Hasil Capture (terakhir)", bg="#f6f7f9", fg=MUTED,
                 font=("DejaVu Sans", 9, "bold")).pack(anchor="w", padx=6, pady=(4, 0))
        self.preview_lbl = tk.Label(pv1, text="Kamera mati / belum terbuka", fg=GRAY,
                                    bg="#f6f7f9", font=("DejaVu Sans", 10))
        self.preview_lbl.pack(padx=4, pady=4, expand=True)
        self.preview_lbl2 = tk.Label(pv2, text="Belum ada capture", fg=GRAY,
                                     bg="#f6f7f9", font=("DejaVu Sans", 10))
        self.preview_lbl2.pack(padx=4, pady=4, expand=True)

    # ------------------------------------------------------------------ cam
    def _grab_worker(self, cam, attr_src_sync, attr_pil, attr_bgr=None, overlay=False):
        import cv2
        W, H = self._preview_w, self._preview_h
        while not self._preview_stop:
            src = getattr(self, attr_src_sync)
            if src and src != cam.source:
                cam.set_source(src)
            raw = cam.grab()
            if raw is None:
                time.sleep(0.5)
                self._err_cam(cam, attr_pil)
                continue
            try:
                small = cv2.resize(raw, (W, H), interpolation=cv2.INTER_AREA)
                if overlay and self._overlay:
                    with self._preview_lock:
                        ov = self._overlay
                    if ov:
                        small = self._draw_overlay(small, ov[0], ov[1])
                img = Image.fromarray(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))
            except Exception:
                time.sleep(0.3)
                continue
            with self._preview_lock:
                setattr(self, attr_pil, img)
                if attr_bgr:
                    setattr(self, attr_bgr, raw.copy())
                self._preview_seq += 1
            time.sleep(0.03)

    def _err_cam(self, cam, attr_pil):
        with self._preview_lock:
            setattr(self, attr_pil, None)
            err = cam.error()
        if err and getattr(self, "_last_cam_err", None) != err:
            self._last_cam_err = err
            self._log("[kamera] " + str(err), tag="warn")

    def _preview_loop(self):
        cam = self._anpr.cam
        self._gr_cam = threading.Thread(
            target=self._grab_worker,
            args=(cam, "_cam_source_sync", "_preview_pil", "_preview_bgr", True),
            daemon=True)
        self._gr_cam.start()
        self._last_capture_pil = None

    def _draw_overlay(self, frame, boxes, banner):
        import cv2
        W, H = self._preview_w, self._preview_h
        for x0, y0, x1, y1, chosen, text in boxes:
            a = (int(x0 * W), int(y0 * H))
            b = (int(x1 * W), int(y1 * H))
            color = (60, 160, 90) if chosen else (0, 150, 220)
            cv2.rectangle(frame, a, b, color, 2 if chosen else 1)
            cv2.putText(frame, text, (a[0], max(12, a[1] - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
        cv2.rectangle(frame, (4, 4), (W - 4, 24), (235, 237, 240), -1)
        cv2.putText(frame, banner, (8, 18), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (32, 36, 42), 1, cv2.LINE_AA)
        return frame

    def _update_preview(self):
        with self._preview_lock:
            pil = self._preview_pil
        if pil is not None and pil is not getattr(self, "_shown_pil", None):
            self._shown_pil = pil
            self._preview_img = ImageTk.PhotoImage(pil)
            self.preview_lbl.configure(image=self._preview_img, text="")

    def _anpr_status_text(self):
        if self._anpr_error:
            return "ANPR tidak bisa dimuat: " + str(self._anpr_error)
        if self._anpr is None:
            return "ANPR tidak tersedia"
        return self._anpr.ready_message()

    def _sync_camera_source(self):
        if self._anpr is None:
            return
        src = self.anpr_source.get().strip()
        if src:
            self._anpr.cam.set_source(src)

    def _anpr_toggle(self):
        if self._anpr is not None:
            if self.anpr_on.get():
                self._sync_camera_source()
                self._send("P")
                self._log("Validasi plat AKTIF — tap RFID wajib ada plat terdeteksi kamera.",
                          tag="warn")
            else:
                self._send("p")
                self._log("Validasi plat NONAKTIF — RFID normal (tanpa cek plat).",
                          tag="info")
            self.btn_scan.config(state="normal" if self.anpr_on.get() else "disabled")
            self.lbl_anpr.config(text=self._anpr_status_text())
        else:
            self.anpr_on.set(False)

    def _anpr_scan(self):
        if self._anpr is None or not self.anpr_on.get():
            return
        self._sync_camera_source()
        self.lbl_anpr.config(text="Menangkap frame + OCR...")
        threading.Thread(target=self._anpr_worker, daemon=True).start()

    def _anpr_worker(self):
        try:
            with self._preview_lock:
                frame = None if self._preview_bgr is None else self._preview_bgr.copy()
            if frame is None:
                result = {"ok": False, "plate": None, "score": 0.0,
                          "allowed": False, "msg": "tidak ada frame kamera",
                          "boxes": [], "w": 0, "h": 0}
            else:
                result = self._anpr.attempt(frame)
                boxes = []
                w = result.get("w") or frame.shape[1]
                h = result.get("h") or frame.shape[0]
                for x0, y0, x1, y1, text, score, chosen in result.get("boxes") or []:
                    boxes.append((x0 / w, y0 / h, x1 / w, y1 / h, chosen, text))
                result["_boxes_norm"] = boxes
        except Exception as e:
            result = {"ok": False, "plate": None, "score": 0.0,
                      "allowed": False, "msg": "error: %s" % e,
                      "boxes": [], "w": 0, "h": 0, "_boxes_norm": []}
        self._anpr_q.put(result)

    def _drain_anpr_queue(self):
        while True:
            try:
                item = self._anpr_q.get_nowait()
            except queue.Empty:
                return
            if (isinstance(item, tuple) and item and item[0] == "PLATE_VALIDATE"):
                self._plate_result(item[1])
            elif (isinstance(item, tuple) and item and item[0] == "CAPTURE"):
                self._show_capture(item[1])
            else:
                self._anpr_show(item)

    def _anpr_show(self, res):
        plate = res["plate"] or "-"
        status = "%s | %-10s | %.2f | %s" % (
            "OK" if res["ok"] else "GAGAL", plate, res["score"], res["msg"])
        self.lbl_anpr.config(text=status)
        self._log("[anpr] " + status, tag="ok" if res["ok"] else "err")
        banner = "%s | %d%% | %s" % (plate, int(res["score"] * 100), res["msg"])
        boxes = res.get("_boxes_norm") or []
        with self._preview_lock:
            self._overlay = (boxes, banner)
        if res["allowed"]:
            self._send("O")
            self._log("Buka gate via ANPR.", tag="ok")
        if res["ok"] and res["plate"]:
            threading.Thread(target=self._capture,
                             args=("anpr", "ANPR"),
                             kwargs={"plate": res["plate"],
                                     "allowed": bool(res["allowed"])},
                             daemon=True).start()

    def _anpr_auto_check(self):
        if self._anpr is None or not self.anpr_on.get():
            return
        if not self._anpr.can_auto():
            return
        threading.Thread(target=self._anpr_worker, daemon=True).start()

    # ------------------------------------------------------------ capture
    def _capture(self, prefix, method, uid=None, plate=None, allowed=True,
                 note=None):
        """Capture frame kamera + catat ke database (dipanggil di thread)."""
        if self._plog is None:
            self._log("[capture] PassageLog tidak aktif: %s" % self._plog_error,
                      tag="err")
            return None
        with self._preview_lock:
            frame = self._preview_bgr
            if frame is not None:
                frame = frame.copy()
        plog = PassageLog()
        try:
            img = plog.save_image(frame, prefix)
            plog.record(direction="ENTRY", method=method, uid=uid,
                        plate=plate, allowed=allowed,
                        image_path=img, note=note)
        finally:
            plog.close()
        if img:
            self._log("[capture] %s disimpan -> %s" % (prefix, img), tag="ok")
            self._anpr_q.put(("CAPTURE", img))
        else:
            self._log("[capture] %s: kamera tak tersedia (frame kosong)" % prefix,
                      tag="warn")
        return img

    def _show_capture(self, img_path):
        """Tampilkan gambar capture terakhir ke panel kanan (thread-aman)."""
        try:
            path = ROOT / img_path if not os.path.isabs(img_path) else img_path
            im = Image.open(path)
            im.thumbnail((368, 276))
            self._last_capture_pil = ImageTk.PhotoImage(im)
            self.preview_lbl2.configure(image=self._last_capture_pil, text="")
        except Exception as e:
            self.preview_lbl2.configure(image="", text="Capture: %s" % e)

    # -------------------------------------------- validasi plat (RFID + ANPR)
    def _trigger_plate_validation(self):
        """Kartu sah & ESP32 menahan buka ('V') → minta ANPR baca plat."""
        self._plate_pending = True
        self._plate_pending_until = self._now() + PLATE_VALIDATE_S
        if self._anpr is None:
            self._log("[plate] ANPR tidak tersedia — akses ditolak.", tag="err")
            self._send("N")
            self._plate_pending = False
            return
        if not self.anpr_on.get():
            self._log("[plate] ANPR nonaktif — akses ditolak.", tag="err")
            self._send("N")
            self._plate_pending = False
            return
        self._sync_camera_source()
        self._log("[plate] Kartu sah — validasi plat dari kamera...", tag="warn")
        threading.Thread(target=self._plate_worker, daemon=True).start()

    def _plate_worker(self):
        try:
            with self._preview_lock:
                frame = None if self._preview_bgr is None else self._preview_bgr.copy()
            if frame is None:
                result = {"ok": False, "plate": None, "allowed": False,
                          "msg": "tidak ada frame kamera"}
            else:
                result = self._anpr.attempt(frame)
        except Exception as e:
            result = {"ok": False, "plate": None, "allowed": False,
                      "msg": "error: %s" % e}
        self._anpr_q.put(("PLATE_VALIDATE", result))

    def _plate_result(self, res):
        if not self._plate_pending:
            return
        if self._now() > self._plate_pending_until:
            self._plate_pending = False
            self._send("N")
            self._log("[plate] Timeout validasi — akses ditolak.", tag="err")
            return
        self._plate_pending = False
        plate = res.get("plate")
        allowed = bool(res.get("allowed"))
        msg = res.get("msg", "")
        if plate and res.get("ok") and allowed:
            self._send("G")
            self._log("[plate] %s terverifikasi — GERBANG DIBUKA." % plate, tag="ok")
            threading.Thread(target=self._capture,
                             args=("anpr", "ANPR"),
                             kwargs={"plate": plate, "allowed": True,
                                     "note": "rfid+plat terverifikasi"},
                             daemon=True).start()
        else:
            self._send("N")
            alasan = plate if plate else "TIDAK ADA PLAT terdeteksi"
            self._log("[plate] %s (%s) — akses DITOLAK." % (alasan, msg), tag="err")
            threading.Thread(target=self._capture,
                             args=("anpr", "ANPR"),
                             kwargs={"plate": plate, "allowed": False,
                                     "note": "rfid+plat gagal: %s" % msg},
                             daemon=True).start()

    # ------------------------------------------------------------------ serial
    def _refresh_ports(self):
        ports = list_ports()
        self.port_combo["values"] = ports
        if ports:
            self.port_combo.current(0)

    def _toggle_conn(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.ser = None
            self._set_conn(False)
            self._log("Diputuskan dari serial.", tag="info")
            return
        port = self.port_var.get()
        if not port:
            self._log("Pilih port dulu.", tag="err")
            return
        try:
            self.ser = serial.Serial(port, 115200, timeout=0.1)
            self._set_conn(True)
            self._log("Terhubung ke " + port, tag="info")
        except Exception as e:
            self._log("Koneksi gagal: %s" % e, tag="err")

    def _set_conn(self, ok):
        self.lbl_conn.config(text="Terhubung" if ok else "Terputus",
                             fg=OK if ok else ERR)
        self.btn_conn.config(text="Putuskan" if ok else "Hubungkan")

    def _send(self, cmd):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(cmd.encode())
            except serial.SerialException:
                pass

    def _send_open(self):
        self._send("O"); self._log(">> buka", tag="info")

    def _send_close(self):
        self._send("C"); self._log(">> tutup", tag="info")

    def _send_reqclose(self):
        self._send("C"); self._log(">> minta tutup", tag="info")

    def _send_testopen(self):
        self._send("Z"); self._log(">> test buka", tag="info")

    def _send_testclosed(self):
        self._send("X"); self._log(">> test tutup", tag="info")

    def _send_addmode(self):
        self._send("A"); self._log(">> mode tambah master — tempel kartu baru", tag="warn")

    def _send_delmode(self):
        self._send("Q"); self._log(">> mode hapus master — tempel kartu yg dihapus", tag="warn")

    def _send_list(self):
        self._send("L"); self._log(">> minta daftar master", tag="info")

    def _send_clear(self):
        self._send("R"); self._log(">> hapus semua master", tag="warn")

    # ------------------------------------------------------------------ poll
    def _auto_connect(self):
        if self.ser and self.ser.is_open:
            return
        choices = list(self.port_combo["values"])
        usb = [p for p in choices if "USB" in p.upper()]
        if usb:
            self.port_var.set(usb[0])
            self._toggle_conn()
        elif self.port_var.get():
            self._toggle_conn()
        elif choices:
            self.port_combo.current(0)
            self._toggle_conn()
        else:
            self._log("Tidak ada port serial tersedia.", tag="info")

    def _poll(self):
        self._drain_log()
        if self.ser and self.ser.is_open:
            try:
                data = self.ser.read(1024)
                if data:
                    self._buf += data
                    while b"\n" in self._buf:
                        line, self._buf = self._buf.split(b"\n", 1)
                        self._on_line(line.decode(errors="replace").strip())
            except (serial.SerialException, OSError):
                self.ser = None
                self._set_conn(False)
                self._log("Koneksi serial terputus.", tag="warn")
        self._cam_source_sync = self.anpr_source.get().strip()
        self._update_preview()
        self._drain_anpr_queue()
        self._render_static()
        self.root.after(50, self._poll)

    def _on_line(self, line):
        if not line:
            return
        if line.startswith(">"):
            tag = "info"
            if ("UNAUTHORIZED" in line or "rejected" in line
                    or "TIDAK MERESPON" in line or "DENIED" in line
                    or "TIMEOUT" in line):
                tag = "err"
            elif ("gagal dibaca" in line or "MENUNGGU KENDARAAN" in line
                    or "TUNGGU KENDARAAN" in line or "mode" in line.lower()):
                tag = "warn"
            elif any(k in line for k in ("OPEN", "open", "CLOSED", "closed",
                                         "DITETAPKAN", "Ditambahkan", "GRANTED",
                                         "diangkat", "Dihapus", "dihapus")):
                tag = "ok"
            self._log(line, tag=tag)
            return
        if not line.startswith("ST|"):
            return
        p = line.split("|")
        if len(p) < 13:
            return
        self._last_st_ms = self._now()
        self.state = p[1]
        try:
            self.pos = int(p[2])
        except ValueError:
            pass
        try:
            self.dist = int(p[3])
        except ValueError:
            pass
        try:
            self.exit_cm = int(p[8])
        except ValueError:
            pass
        try:
            self.master_count = int(p[12])
        except ValueError:
            pass
        self.vehicle_near = p[4] == "1"
        self.lcd_row1 = p[5]
        self.lcd_row2 = p[6]
        self.master_uid = p[7]
        self.rfid_ver = p[9]
        self.rfid_last_uid = p[10]
        self.rfid_last_auth = p[11]

        # ---- Log Sistem: catat PERUBAHAN status/grafis/sensor/master ----
        if self.state != self._prev_state:
            self._log("[state] %s -> %s" % (self._prev_state, self.state),
                      tag="ok" if self.state in ("OPEN", "OPENING") else "info")
            self._prev_state = self.state
        if self.vehicle_near != self._prev_vehicle:
            self._log("[sensor] kendaraan %s (%d cm)" %
                      ("DETEKSI" if self.vehicle_near else "LOWONG", self.dist),
                      tag="ok" if self.vehicle_near else "info")
            self._prev_vehicle = self.vehicle_near
        r2 = self.lcd_row2.strip()
        msg_kw = ("NO VEHICLE", "TUNGGU", "ACCESS", "UNAUTHOR", "PASSED",
                  "WAIT", "OPENING", "CLOSING", "GRANTED")
        if (r2 and r2 != self._prev_row2 and any(k in r2 for k in msg_kw)):
            self._log("[display] %s" % r2, tag="info")
            self._prev_row2 = r2
        if self.master_uid != self._prev_masters:
            self._log("[master] daftar: %s (%d kartu)" % (self.master_uid, self.master_count),
                      tag="info")
            self._prev_masters = self.master_uid

        if self.rfid_last_uid != "-" and self.rfid_last_uid != self._rfid_last_uid_seen:
            self._rfid_last_uid_seen = self.rfid_last_uid
            outcomes = {'G': "GRANTED", 'D': "DENIED", 'P': "TUNGGU KENDARAAN",
                        'A': "JADI MASTER", 'R': "DIHAPUS", 'V': "MENUNGGU VALIDASI PLAT"}
            outcome = outcomes.get(self.rfid_last_auth, "SCAN")
            tag = "ok" if outcome in ("GRANTED", "JADI MASTER", "TUNGGU KENDARAAN", "MENUNGGU VALIDASI PLAT") else \
                ("warn" if outcome == "DIHAPUS" else "err")
            self._log("[rfid] kartu %s -> %s" % (self.rfid_last_uid, outcome), tag=tag)
            allowed = outcome in ("GRANTED", "TUNGGU KENDARAAN", "JADI MASTER")
            threading.Thread(target=self._capture,
                             args=("rfid", "RFID"),
                             kwargs={"uid": self.rfid_last_uid,
                                     "allowed": allowed},
                             daemon=True).start()

        # ---- Kadar validasi plat: 'V' dari ESP32 → minta ANPR baca plat ----
        if self.rfid_last_auth == 'V':
            if not self._plate_pending:
                self._trigger_plate_validation()
        elif self._plate_pending:
            self._plate_pending = False

        if (self.state == "CLOSED" and self.vehicle_near
                and self._anpr is not None and self.anpr_on.get()):
            self._anpr_auto_check()

        if self.state == "OPEN" and self._open_since_local is None:
            self._open_since_local = self._now()
        elif self.state != "OPEN":
            self._open_since_local = None

        self._render()

    # ---------------------------------------------------------------- render
    @staticmethod
    def _now():
        return time.monotonic()

    def _render(self):
        state_map = {"CLOSED": "Tertutup", "OPEN": "Terbuka",
                     "OPENING": "Membuka", "CLOSING": "Menutup"}
        color_map = {"CLOSED": ERR, "OPEN": OK, "OPENING": WARN, "CLOSING": WARN}
        self.lbl_state.config(text=state_map.get(self.state, self.state),
                              fg=color_map.get(self.state, TEXT))

        span = float(POS_CLOSED - POS_OPEN)
        frac = max(0.0, min(1.0, (self.pos - POS_OPEN) / span))
        fname = frac * 100.0
        self._pos_lbl.config(text="%d" % self.pos)
        self.bar_pos["value"] = fname

        now = self._now()
        if self.state == "OPEN" and self._open_since_local is not None:
            remain = max(0.0, (AUTO_CLOSE_S * 1000.0)
                         - (now - self._open_since_local) * 1000.0)
            self._auto_lbl.config(text="%.1f s" % (remain / 1000.0))
            self._auto_bar["value"] = (1.0 - remain / (AUTO_CLOSE_S * 1000.0)) * 100.0
        else:
            self._auto_lbl.config(text="-")
            self._auto_bar["value"] = 0.0

        self.lbl_kendaraan.config(
            text="Kendaraan terdeteksi" if self.vehicle_near else "Jalur kosong",
            fg=OK if self.vehicle_near else GRAY)
        if self.dist < 0:
            self.lbl_dist.config(text="--- cm")
            self.bar_dist["value"] = 0.0
        else:
            self.lbl_dist.config(text="%d cm" % self.dist)
            self.bar_dist["value"] = (1.0 - min(1.0, max(0.0, self.dist / 30.0))) * 100.0
        self.lbl_exit.config(text="%s" % ("--- cm" if self.exit_cm < 0 else "%d cm" % self.exit_cm))

        ok = self.rfid_ver not in ("0x00", "0xFF")
        self.lbl_rfid.config(text="Siap" if ok else "Tidak merespons",
                             fg=OK if ok else ERR)
        self.lbl_ver.config(text="versi %s" % self.rfid_ver)
        if self.master_uid in ("-", ""):
            self.lbl_master.config(text="-")
            self.lbl_count.config(text="")
        else:
            self.lbl_master.config(text=self.master_uid)
            self.lbl_count.config(text="total %d kartu terotorisasi" % self.master_count)

        self.lbl_disp1.config(text=self.lcd_row1)
        self.lbl_disp2.config(text=self.lcd_row2, fg=(WARN if "TUNGGU" in self.lcd_row2
                                                      or "PASSED" in self.lcd_row2 or "WAIT" in self.lcd_row2 else TEXT))

        # ---- panduan intuitif kartu RFID ----
        if not (self.ser and self.ser.is_open):
            hint, hf = "Hubungkan serial untuk mulai.", GRAY
        elif self.master_uid in ("-", ""):
            hint, hf = "Belum ada kartu! Tempel kartu pertama untuk mendaftarkan.", WARN
        elif self.rfid_last_auth == 'D':
            hint, hf = "Kartu %s DITOLAK — bukan terotorisasi." % self.rfid_last_uid, ERR
        elif self.rfid_last_auth == 'P':
            hint, hf = "Kartu diterima — MENUNGGU kendaraan di depan sensor.", WARN
        elif self.rfid_last_auth == 'V':
            hint, hf = "Kartu sah — validasi PLAT dari kamera berlangsung...", WARN
        elif self.vehicle_near:
            hint, hf = "Siap! Tempel kartu terotorisasi untuk membuka gerbang.", OK
        else:
            hint, hf = "Kartu terotorisasi dicek saat ada kendaraan di depan sensor.", ACCENT
        self.lbl_rfid_hint.config(text=hint, fg=hf)

        if self.rfid_last_uid == "-":
            txt, fg = "-", GRAY
        elif self.rfid_last_auth == 'G':
            txt, fg = "%s (GRANTED)" % self.rfid_last_uid, OK
        elif self.rfid_last_auth == 'V':
            txt, fg = "%s (VALIDASI PLAT)" % self.rfid_last_uid, WARN
        elif self.rfid_last_auth == 'P':
            txt, fg = "%s (TUNGGU KENDARAAN)" % self.rfid_last_uid, WARN
        elif self.rfid_last_auth == 'A':
            txt, fg = "%s (JADI MASTER)" % self.rfid_last_uid, OK
        elif self.rfid_last_auth == 'R':
            txt, fg = "%s (DIHAPUS)" % self.rfid_last_uid, WARN
        elif self.rfid_last_auth == 'D':
            txt, fg = "%s (DENIED)" % self.rfid_last_uid, ERR
        else:
            txt, fg = "%s (SCAN)" % self.rfid_last_uid, ACCENT
        self.lbl_scan.config(text=txt, fg=fg)

    # label helpers (pos / auto-close terseimpan saat build)
    def _render_static(self):
        now = self._now()
        if self.ser and self.ser.is_open:
            up = int(now - self._app_start)
            self._up_str = "%02d:%02d:%02d" % (up // 3600, (up % 3600) // 60, up % 60)
            # deteksi mati-nyala heartbeat (tidak ada ST dalam 1.5 detik)
            alive = self._last_st_ms is not None and (now - self._last_st_ms) < 1.5
            if alive:
                self._heartbeat_off = False
                self.lbl_conn.config(text="Terhubung (%s)" % self._up_str, fg=OK)
            else:
                was = self._heartbeat_off
                self._heartbeat_off = True
                self.lbl_conn.config(text="TIDAK MENERIMA DATA", fg=ERR)
                if not was:
                    self._log("Warning: ESP32 tidak mengirim ST selama 1.5s — cek kabel/power.", tag="warn")
        else:
            self._up_str = "-"
            self._heartbeat_off = False
            self.lbl_conn.config(text="Terputus", fg=ERR)

    def _log_clear(self):
        if self.log_w is not None:
            self.log_w.config(state="normal")
            self.log_w.delete("1.0", "end")
            self.log_w.config(state="disabled")

    def _log(self, msg, tag="info"):
        self._log_q.put((msg, tag))

    def _drain_log(self):
        while True:
            try:
                msg, tag = self._log_q.get_nowait()
            except queue.Empty:
                return
            self.log_w.config(state="normal")
            self.log_w.insert("end", msg + "\n", (tag,))
            self.log_w.see("end")
            self.log_w.config(state="disabled")
            self._sys_append(msg, tag)

    # ------------------------------------------------------------ log sistem
    def _toggle_capture_viewer(self):
        if self._capwin is not None and self._capwin.winfo_exists():
            self._capwin.destroy()
            self._capwin = None
            self._log("Jendela Capture ditutup.", tag="info")
            return
        self._capwin = CaptureViewer(self.root, self._plog)
        self._capwin.win.protocol("WM_DELETE_WINDOW",
                                  lambda: (self._capwin.win.destroy(),
                                           setattr(self, "_capwin", None)))
        self._log("Jendela Capture dibuka.", tag="info")

    def _toggle_syslog(self):
        if self._syswin is not None and self._syswin.winfo_exists():
            self._syswin.destroy()
            self._syswin = None
            self._log("Log Sistem ditutup.", tag="info")
            return
        w = tk.Toplevel(self.root)
        w.title("Log Sistem — riwayat lengkap sistem gate")
        w.configure(bg=WIN_BG)
        w.geometry("880x520")
        w.minsize(560, 320)
        top = tk.Frame(w, bg=WIN_BG)
        top.pack(fill="x", padx=10, pady=(10, 4))
        tk.Label(top, text="Log Sistem (seluruh kejadian: gerbang, sensor, RFID, tombol, display)",
                 bg=WIN_BG, fg=TEXT, font=("DejaVu Sans", 11, "bold")).pack(side="left")
        ttk.Button(top, text="Bersihkan", command=self._sys_clear).pack(side="right")
        tf = tk.Frame(w, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        tf.pack(fill="both", expand=True, padx=10, pady=(2, 10))
        self._sys_text = tk.Text(tf, state="disabled", relief="flat", borderwidth=0,
                                 bg=CARD_BG, fg=TEXT, font=("DejaVu Sans Mono", 9),
                                 wrap="none")
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self._sys_text.yview)
        self._sys_text.configure(yscrollcommand=vsb.set)
        self._sys_text.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        for tagg, color in (("ok", OK), ("err", ERR), ("warn", WARN), ("info", GRAY)):
            self._sys_text.tag_configure(tagg, foreground=color)
        self._syswin = w
        self._log("Log Sistem dibuka.", tag="info")

    def _sys_clear(self):
        if self._sys_text is not None:
            self._sys_text.config(state="normal")
            self._sys_text.delete("1.0", "end")
            self._sys_text.config(state="disabled")

    def _sys_append(self, msg, tag):
        if self._sys_text is None:
            return
        if not (self._syswin is not None and self._syswin.winfo_exists()):
            self._sys_text = None
            return
        self._sys_text.config(state="normal")
        self._sys_text.insert("end", msg + "\n", (tag,))
        self._sys_text.see("end")
        self._sys_text.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    GateSerialApp(root)
    root.mainloop()