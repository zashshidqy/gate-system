# Gate Dashboard

Staff Dashboard for Smart Gate System with Ticket Token Support

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- ESP32 boards connected via USB

### Development

One command (creates venv / installs deps if missing):

```bash
cd gate-dashboard
./dev.sh
# or: npm run dev
```

Or start the two processes yourself:

```bash
# Backend — must bind IPv4 so the Vite proxy can reach it
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend (in another terminal)
cd frontend
npm install
npm run dev
```

Default login (fresh DB only):

- Username: `admin`
- Password: `admin1234`

Change this password after first login. ESP32 serial ports are optional in development — missing `/dev/ttyUSB*` will not crash the API.

### Docker

```bash
# Set required environment variables
export JWT_SECRET="your-super-secret-key-min-32-chars"
export SERIAL_PORT_ENTRY=/dev/ttyUSB0
export SERIAL_PORT_EXIT=/dev/ttyUSB1

docker-compose up -d
```

### Access

- Frontend: http://localhost:5173 (dev) or http://localhost (docker)
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## Project Structure

```
gate-dashboard/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # REST endpoints
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   ├── websocket/      # WebSocket manager
│   │   └── dependencies.py # Auth dependencies
│   ├── alembic/            # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # React + TypeScript frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── context/        # React contexts
│   │   ├── api/            # API client
│   │   └── types/          # TypeScript types
│   ├── package.json
│   └── Dockerfile
├── docs/                   # Documentation
│   ├── README.md
│   ├── CHANGELOG.md
│   ├── REQUIREMENTS.md
│   └── TODO.md
└── docker-compose.yml
```

## Features

- 🔴 Real-time gate monitoring (ENTRY/EXIT)
- 🎫 Ticket token management with QR codes
- 🏷️ RFID authorized card management
- 📊 Passage history with analytics
- 👥 User management with RBAC
- 🔐 JWT authentication
- 📱 Responsive design (mobile-friendly)
- 🐳 Docker support

## Documentation

- [Full Documentation](docs/README.md)
- [Requirements](docs/REQUIREMENTS.md)
- [Changelog](docs/CHANGELOG.md)
- [TODO](docs/TODO.md)