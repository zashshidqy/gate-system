#!/usr/bin/env python3
"""
Passage log (add-on #1 & #2) — database akses gate.

Setiap "kejadian akses" (tap RFID / scan plat ANPR / buka manual) dicatat ke
SQLite `data/gate.db` dan (bila kamera tersedia) gambar di `data/captures/`.

- add-on #1 "Capture saat tap RFID (gambar + input plat)"
- add-on #2 "database (recommend ai)"  → SQLite; AI = modul ANPR (sim/anpr)
"""

import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "gate.db"
CAPTURE_DIR = DATA_DIR / "captures"

SCHEMA = """
CREATE TABLE IF NOT EXISTS passages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,            -- waktu kejadian (ISO)
    direction TEXT NOT NULL,     -- ENTRY / EXIT
    method TEXT NOT NULL,        -- RFID / ANPR / MANUAL
    uid TEXT,                    -- UID kartu (RFID) atau '-'
    plate TEXT,                  -- plat nomor / '-'
    allowed INTEGER NOT NULL,    -- 1 = diizinkan / 0 = ditolak
    image_path TEXT,             -- path gambar capture / NULL
    note TEXT                    -- keterangan / NULL
);
CREATE INDEX IF NOT EXISTS idx_passages_ts ON passages(ts);
CREATE INDEX IF NOT EXISTS idx_passages_method ON passages(method);
"""


class PassageLog:
    def __init__(self, db_path=None, capture_dir=None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.capture_dir = Path(capture_dir) if capture_dir else CAPTURE_DIR
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = None
        self.open()

    def open(self):
        import sqlite3
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.executescript(SCHEMA)
        # WAL: baca & tulis aman berbarengan (kamera/ANPR menulis di thread)
        try:
            self._conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.Error:
            pass

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------ capture
    def save_image(self, frame, prefix="capture"):
        """Simpan frame (numpy BGR) ke data/captures/ + return path relatif."""
        if frame is None:
            return None
        try:
            import cv2  # lazy — tidak wajib kalau kamera tidak dipakai
        except ImportError:
            return None
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        name = "%s_%s.jpg" % (prefix, time.strftime("%Y%m%d_%H%M%S"))
        path = self.capture_dir / name
        try:
            ok = cv2.imwrite(str(path), frame)
        except Exception:
            ok = False
        if not ok:
            return None
        try:
            return str(path.relative_to(ROOT))  # "captures/xx.jpg"
        except ValueError:
            return str(path)

    # ------------------------------------------------------------ record
    def record(self, direction="ENTRY", method="RFID", uid=None, plate=None,
               allowed=True, image_path=None, note=None, ts=None):
        if self._conn is None:
            self.open()
        ts = ts or time.strftime("%Y-%m-%d %H:%M:%S")
        cur = self._conn.execute(
            "INSERT INTO passages"
            " (ts, direction, method, uid, plate, allowed, image_path, note)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (ts, direction, method, uid or "-", (plate or "-").upper(),
             1 if allowed else 0, image_path, note))
        self._conn.commit()
        return cur.lastrowid

    # ------------------------------------------------------------ query
    def recent(self, n=50, method=None, allowed=None, q=None):
        """n catatan terakhir, bisa difilter (method / allowed / kata kunci)."""
        if self._conn is None:
            self.open()
        sql = ("SELECT id, ts, direction, method, uid, plate, allowed,"
               " image_path, note FROM passages")
        conds, args = [], []
        if method:
            conds.append("method = ?")
            args.append(method)
        if allowed is not None:
            conds.append("allowed = ?")
            args.append(1 if allowed else 0)
        if q:
            conds.append("(uid LIKE ? OR plate LIKE ? OR note LIKE ?)")
            like = "%" + q + "%"
            args += [like, like, like]
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(n)
        rows = self._conn.execute(sql, args).fetchall()
        cols = ("id", "ts", "direction", "method", "uid", "plate",
                "allowed", "image_path", "note")
        return [dict(zip(cols, r)) for r in rows]

    def count(self):
        if self._conn is None:
            self.open()
        return self._conn.execute("SELECT COUNT(*) FROM passages").fetchone()[0]

    def clear(self):
        if self._conn is None:
            self.open()
        self._conn.execute("DELETE FROM passages")
        self._conn.commit()


def selftest():
    """Uji cepat PassageLog tanpa GUI."""
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    log = PassageLog(str(tmp / "gate.db"), str(tmp / "captures"))
    rid = log.record(direction="ENTRY", method="RFID", uid="A4B3C2D1",
                     plate="B1234CD", allowed=True, note="selftest")
    assert rid == 1, rid
    rid = log.record(direction="EXIT", method="ANPR", uid="-",
                     plate="D1ABC", allowed=True)
    rows = log.recent(5)
    assert len(rows) == 2, rows
    assert rows[0]["plate"] == "D1ABC"
    # jalur gambar (tanpa cv2 terpasang → None, tidak crash)
    log.save_image(None)
    print("==== PASSAGE LOG SELFTEST ====")
    for r in log.recent(5):
        print("  %(id)d %(ts)s %(direction)s %(method)s %(uid)s %(plate)s" % r)
    print("RESULT: ALL PASS")
    log.close()
    return 0

    
if __name__ == "__main__":
    raise SystemExit(selftest())