from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
PLATE_DB = DATA_DIR / "plat_izin.json"

CAMERA_SOURCE = "0"  # sementara: kamera bawaan laptop (webcam index 0); ganti rtsp://... untuk CCTV nanti
CAMERA_SOURCE_2 = ""            # kamera tampilan ke-2 (bukan ANPR): isi "1","2", atau rtsp://... ; kosong = mati (hindari rebutan webcam dengan ANPR)
RTSP_TCP = True                 # gunakan RTP over TCP (stabil untuk CCTV di LAN / seperti VLC --rtsp-tcp)
AUTO_COOLDOWN_S = 6.0           # jeda minimal antar percobaan auto-scan
MANUAL_COOLDOWN_S = 2.0         # jeda minimal antar scan manual
MIN_SCORE = 0.60                # ambang kepercayaan OCR (0..1)
PLATE_REGEX = r"^[A-Z]{1,2}-?\d{1,4}-?[A-Z]{1,3}$"

# Mode simulasi (tanpa kamera & OCR) untuk uji alur auto-trigger → kirim 'O'.
# Set False + install deps (sim/requirements-anpr.txt) untuk kamera asli.
MOCK_ANPR = False
MOCK_PLATE = "B1234CD"

CHAR_CONFUSION = {
    "0": "ODQ",
    "1": "ILT",
    "2": "Z",
    "5": "S",
    "6": "G",
    "8": "B",
    "B": "8",
    "D": "0O",
    "O": "0Q",
    "I": "1",
    "S": "5",
    "Q": "0O",
    "Z": "2",
}