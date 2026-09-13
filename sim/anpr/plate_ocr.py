from . import config
from .plate_db import PlateDb


class PlateOCR:
    def __init__(self):
        self._engine = None
        self._mode = None
        self._err = None
        self.last_boxes = []
        self._last_rows = []
        self._win = []

    def available(self):
        try:
            import paddleocr  # noqa: F401
            return True
        except ImportError:
            return False

    def available_message(self):
        if self.available():
            return "PaddleOCR terpasang"
        return ("PaddleOCR belum terpasang — jalankan:\n"
                "pip install -r sim/requirements-anpr.txt")

    def _ensure_engine(self):
        if self._engine is not None:
            return True
        try:
            from paddleocr import PaddleOCR
            self._engine = PaddleOCR(lang="en")
            if hasattr(self._engine, "ocr"):
                self._mode = "v2"
            elif hasattr(self._engine, "predict"):
                self._mode = "v3"
            else:
                self._err = "API paddleocr tidak dikenal"
                self._engine = None
                return False
            return True
        except Exception as e:
            self._err = "gagal memuat PaddleOCR: %s" % e
            self._engine = None
            return False

    def recognize(self, frame):
        self.last_boxes = []
        out = self._recognize_raw(frame)
        result = self._best_plate(out)
        for item in self._win:
            t, s, r = item
            self.last_boxes.append((r[0], r[1], r[2], r[3], t, s, True))
        for item in self._last_rows:
            t, s, r = item
            if item in self._win:
                continue
            self.last_boxes.append((r[0], r[1], r[2], r[3], t, s, False))
        return result

    def _recognize_raw(self, frame):
        if not self._ensure_engine():
            return []
        try:
            if self._mode == "v2":
                res = self._engine.ocr(frame, cls=True)
                return self._extract_v2(res)
            res = self._engine.predict(frame)
            return self._extract_v3(res)
        except Exception as e:
            self._err = "OCR ragu: %s" % e
            return []

    @staticmethod
    def _box(pts):
        if not pts:
            return None
        try:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
        except (TypeError, IndexError):
            return None
        return (min(xs), min(ys), max(xs), max(ys))

    def _extract_v2(self, res):
        out = []
        if not res:
            return out
        for page in res:
            if page is None:
                continue
            for item in page:
                if not item or len(item) < 2:
                    continue
                t, s = item[1]
                if isinstance(t, str):
                    out.append((t, float(s), self._box(item[0])))
        return out

    def _extract_v3(self, res):
        out = []
        if not res:
            return out
        for page in res:
            data = getattr(page, "json", None) or page
            items = data.get("res", []) if isinstance(data, dict) else []
            for item in items:
                if not isinstance(item, dict):
                    continue
                texts = item.get("rec_texts") or item.get("text") or []
                scores = item.get("rec_scores") or item.get("score") or []
                polys = item.get("dt_polys") or item.get("det_polys") or item.get("rec_polys") or []
                if isinstance(texts, str):
                    pts = polys[0] if polys else None
                    out.append((texts, float(scores if not isinstance(scores, list) else 0.0),
                                self._box(pts)))
                    continue
                for i, t in enumerate(texts):
                    s = scores[i] if isinstance(scores, list) and i < len(scores) else 0.0
                    pts = polys[i] if isinstance(polys, list) and i < len(polys) else None
                    out.append((t, float(s), self._box(pts)))
        return out

    @staticmethod
    def _rows(items):
        pos = [it for it in items if it[2]]
        nopos = [it for it in items if not it[2]]
        if not pos:
            return [nopos] if nopos else []
        hs = sorted((it[2][3] - it[2][1]) for it in pos)
        med_h = hs[len(hs) // 2] or 10
        tol = max(10, 0.5 * med_h)
        rows = []
        for it in sorted(pos, key=lambda x: ((x[2][1] + x[2][3]) / 2, x[2][0])):
            x0, y0, x1, y1 = it[2]
            cy = (y0 + y1) / 2
            if rows and abs(rows[-1][0] - cy) <= tol:
                rows[-1][1].append(it)
            else:
                rows.append([cy, [it]])
        key = lambda it: (it[2] is None, it[2][0] if it[2] else 0.0)
        out = [sorted(r[1], key=key) for r in rows]
        if nopos:
            out.append(nopos)
        return out

    def _best_plate(self, raw):
        self._last_rows = []
        self._win = []
        rows = self._rows(raw)
        cands = []
        for ri, row in enumerate(rows):
            segs = row
            n = len(segs)
            for i in range(n):
                parts_txt = ""
                min_s = 1.0
                for j in range(i, n):
                    parts_txt += segs[j][0] or ""
                    min_s = min(min_s, segs[j][1])
                    p = PlateDb.normalize(parts_txt)
                    if p and PlateDb.is_valid(p):
                        cands.append((p, min_s, j - i + 1, ri, i, j))
        if cands:
            cands.sort(key=lambda x: (x[1], x[2]), reverse=True)
            _, _, _, ri, i, j = cands[0]
            self._last_rows = [it for r in rows for it in r]
            self._win = rows[ri][i:j + 1]
            return cands[0][0], cands[0][1]
        if raw:
            raw.sort(key=lambda x: x[1], reverse=True)
            if isinstance(raw[0][2], tuple):
                self._last_rows = raw
                self._win = [raw[0]]
            return PlateDb.normalize(raw[0][0]), raw[0][1]
        return None, 0.0