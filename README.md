# Gate Project

This repository contains two main components:

## 📁 Structure

```
gate/
├── gate-system/          # ESP32 Firmware & Hardware (PlatformIO)
│   ├── src/              # Source code (entry/exit gates)
│   ├── lib/              # Libraries (buzzer, gate_controller, rfid_reader, etc.)
│   ├── sim/              # Simulation & GUI tools (Python/Tkinter)
│   ├── data/             # Database & captured images
│   ├── docs/             # Hardware documentation
│   ├── platformio.ini    # PlatformIO configuration
│   └── README.md         # ESP32 system documentation
│
├── gate-dashboard/       # Staff Dashboard Web Application
│   ├── backend/          # FastAPI + Python (REST API + WebSocket)
│   ├── frontend/         # React + TypeScript + Vite
│   ├── docs/             # Dashboard documentation
│   └── docker-compose.yml
│
└── .git/                 # Git repository
```

## 🚀 Quick Start

### ESP32 Firmware (gate-system)
```bash
cd gate-system
pio run -e esp32doit-devkit-v1 -t upload   # Upload to ENTRY unit
pio run -e esp32-exit -t upload              # Upload to EXIT unit
```

### Dashboard (gate-dashboard)
```bash
# Backend
cd gate-dashboard/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd gate-dashboard/frontend
npm install
npm run dev
```

## 🔗 Integration

The dashboard connects to ESP32 units via USB serial:
- **ENTRY** gate: `/dev/ttyUSB0` (configurable in `.env`)
- **EXIT** gate: `/dev/ttyUSB1` (configurable in `.env`)

Protocol: 115200 baud, ASCII `ST|...` status every 300ms, single-char commands (`O`, `C`, `A`, `Q`, `L`, `R`, `X`, `Z`).