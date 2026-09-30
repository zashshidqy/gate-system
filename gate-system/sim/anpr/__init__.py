import os

from . import config

# Paksa OpenCV/ffmpeg memakai RTP over TCP untuk RTSP (setara VLC --rtsp-tcp).
# Lebih stabil untuk CCTV LAN dibanding UDP default yang sering terputus.
if config.RTSP_TCP:
    os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")
