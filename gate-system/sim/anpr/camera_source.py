class CameraSource:
    def __init__(self, source=None, width=None, height=None, fps=None):
        self.source = source
        self.cap_width = width
        self.cap_height = height
        self.cap_fps = fps
        self._cap = None
        self._err = None

    def error(self):
        return self._err

    def available(self):
        try:
            import cv2  # noqa: F401
            return True
        except ImportError:
            return False

    def _is_rtsp(self):
        return isinstance(self.source, str) and self.source.lower().startswith(("rtsp://", "rtmp://", "http://"))

    def _open(self):
        try:
            import cv2
        except ImportError:
            self._err = "opencv (cv2) belum terpasang"
            self._cap = None
            return
        try:
            idx = int(self.source)
            self._cap = cv2.VideoCapture(idx)
        except (TypeError, ValueError):
            self._cap = cv2.VideoCapture(self.source)
        if not self._cap.isOpened():
            self._cap = None
            return
        # Kurangi buffer akumulasi (sumber utama delay RTSP): ambil frame terbaru.
        try:
            if self._is_rtsp():
                self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass
        if self.cap_width:
            try:
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cap_width)
            except Exception:
                pass
        if self.cap_height:
            try:
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cap_height)
            except Exception:
                pass
        if self.cap_fps:
            try:
                self._cap.set(cv2.CAP_PROP_FPS, self.cap_fps)
            except Exception:
                pass

    def grab(self):
        if self._cap is None or not self._cap.isOpened():
            self._open()
            if self._cap is None:
                self._err = "kamera tidak dapat dibuka (%r)" % (self.source,)
                return None
        ok, frame = self._cap.read()
        if not ok:
            self._err = "gagal membaca frame dari kamera"
            self.release()
            return None
        self._err = None
        return frame

    def set_source(self, source):
        if source == self.source:
            return
        self.release()
        self.source = source
        self._err = None

    def release(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None
