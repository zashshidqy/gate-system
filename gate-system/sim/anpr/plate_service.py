import threading
import time

from . import config
from .camera_source import CameraSource
from .plate_db import PlateDb
from .plate_ocr import PlateOCR


class AnprService:
    def __init__(self):
        self.db = PlateDb()
        self.cam = CameraSource(config.CAMERA_SOURCE)
        self.ocr = PlateOCR()
        self.lock = threading.Lock()
        self._last_attempt = 0.0
        self.auto_cooldown = config.AUTO_COOLDOWN_S
        self.manual_cooldown = config.MANUAL_COOLDOWN_S
        self.is_mock = config.MOCK_ANPR

    def ready(self):
        if self.is_mock:
            return True
        return self.ocr.available() and self.cam.available()

    def ready_message(self):
        if self.is_mock:
            return "[mock] ANPR SIMULASI aktif (plat: %s) — tanpa kamera/OCR" % config.MOCK_PLATE
        msg = self.ocr.available_message()
        if not self.cam.available():
            msg += "\n[camera] opencv (cv2) belum terpasang"
        elif self.cam.error():
            msg += "\n[camera] " + self.cam.error()
        return msg

    def can_attempt(self, cooldown):
        return (time.monotonic() - self._last_attempt) >= cooldown

    def can_auto(self):
        return self.can_attempt(self.auto_cooldown)

    def attempt(self, frame=None):
        with self.lock:
            self._last_attempt = time.monotonic()
            if self.is_mock:
                return self._mock_result()
            if frame is None:
                frame = self.cam.grab()
                if frame is None:
                    return {
                        "ok": False,
                        "plate": None,
                        "score": 0.0,
                        "allowed": False,
                        "msg": "tidak ada frame kamera",
                    }
            plate, score = self.ocr.recognize(frame)
            res = {
                "ok": True,
                "plate": plate,
                "score": score,
                "allowed": False,
                "msg": "plat tidak terdeteksi",
                "boxes": self.ocr.last_boxes,
                "w": frame.shape[1],
                "h": frame.shape[0],
            }
            if not plate:
                return res
            if score < config.MIN_SCORE:
                res["msg"] = "plat diragukan (score %.2f < %.2f)" % (score, config.MIN_SCORE)
                return res
            variant = self.db.allowed(plate)
            res["allowed"] = variant is not None
            res["msg"] = "IZIN (%s)" % variant if variant else "TIDAK TERDAFTAR"
            return res

    def _mock_result(self):
        plate = config.MOCK_PLATE
        variant = self.db.allowed(plate)
        allowed = variant is not None
        return {
            "ok": True,
            "plate": plate,
            "score": 1.0,
            "allowed": allowed,
            "msg": "IZIN (%s) [mock]" % variant if allowed else "TIDAK TERDAFTAR [mock]",
        }