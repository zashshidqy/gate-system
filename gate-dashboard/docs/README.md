# Gate Dashboard

Staff Dashboard for Smart Gate System with Ticket Token Support

## Overview

This dashboard provides a web-based interface for managing the dual-gate ESP32 system:
- Real-time gate status monitoring (ENTRY/EXIT)
- Ticket token management with QR codes
- RFID authorized card management
- Passage history and analytics
- User management with role-based access control

## Architecture

```
┌─────────────┐     Serial (USB)      ┌──────────────────┐
│  ESP32 x2   │ ◄──────────────────►  │  FastAPI Server  │
│  (ENTRY/    │   ST|... / O/C/A/Q...  │  - Serial bridge │
│   EXIT)     │                       │  - REST API      │
└─────────────┘                       │  - WebSocket hub │
                                      └────────┬─────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    ▼                          ▼                          ▼
             ┌─────────────┐           ┌─────────────┐           ┌─────────────┐
             │  Dashboard  │           │  Dashboard  │           │  Dashboard  │
             │  (Guard)    │           │  (Admin)    │           │  (Mobile)   │
             │  React PWA  │           │  React PWA  │           │  React PWA  │
             └─────────────┘           └─────────────┘           └─────────────┘
```

## Tech Stack

### Backend
- **FastAPI** - Modern async Python web framework
- **SQLAlchemy** - ORM with SQLite/PostgreSQL support
- **Pydantic** - Data validation
- **python-jose** - JWT authentication
- **pyserial-asyncio** - Async serial communication
- **qrcode** - QR code generation
- **Alembic** - Database migrations

### Frontend
- **React 18** + **TypeScript**
- **Vite** - Fast build tool
- **Tailwind CSS** - Utility-first styling
- **shadcn/ui** - Accessible component library
- **TanStack Query** - Server state management
- **React Router** - Client-side routing
- **Recharts** - Data visualization
- **Zustand** - Lightweight state management

## Prerequisites

- Python 3.11+
- Node.js 18+
- ESP32 boards connected via USB
- SQLite (default) or PostgreSQL

## Quick Start

### 1. Backend Setup

```bash
cd gate-dashboard/backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your serial ports and JWT secret

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd gate-dashboard/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 3. Access Dashboard

Open http://localhost:5173 in your browser.

Default login (first user becomes admin):
- Create account via registration page

## Configuration

### Environment Variables (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `SERIAL_PORT_ENTRY` | Serial port for ENTRY gate | `/dev/ttyUSB0` |
| `SERIAL_PORT_EXIT` | Serial port for EXIT gate | `/dev/ttyUSB1` |
| `SERIAL_BAUDRATE` | Serial baud rate | `115200` |
| `DATABASE_URL` | Database connection string | `sqlite:///./gate.db` |
| `JWT_SECRET` | JWT signing secret (min 32 chars) | **Required** |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry | `480` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:5173` |
| `APP_ENV` | Environment | `development` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Serial Port Detection

On Linux:
```bash
# List available ports
ls /dev/ttyUSB* /dev/ttyACM*

# Check permissions
sudo usermod -a -G dialout $USER
# Log out and back in
```

On Windows:
- Ports appear as `COM3`, `COM4`, etc.
- Update `.env` accordingly

## Features

### 1. Real-time Gate Monitoring
- Live servo position, sensor readings, vehicle detection
- WebSocket push updates (300ms interval)
- Manual open/close controls
- Connection status indicators

### 2. Ticket Token System
- Create tokens with types: Single Entry, Multi Day, VIP, Staff
- Configurable validity period and max uses
- QR code generation for mobile scanning
- Validation at gate (ENTRY/EXIT)
- Usage tracking and analytics

### 3. RFID Card Management
- Add/remove authorized cards
- Sync with ESP32 hardware
- Label cards for identification
- Active/inactive status

### 4. Passage History
- Filter by gate, method, date range, status
- Export to CSV
- Real-time statistics dashboard

### 5. User Management
- Role-based access: Admin, Guard, Staff
- JWT authentication with refresh
- Password management

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login
- `POST /api/auth/register` - Register (first user = admin)
- `GET /api/auth/me` - Current user

### Gates
- `GET /api/gates/status` - Gate connection status
- `POST /api/gates/command` - Send command (O/C/A/Q/L/R/X/Z)
- `WS /api/gates/ws` - Real-time status WebSocket

### Tickets
- `POST /api/tickets` - Create ticket
- `GET /api/tickets` - List tickets (paginated, filtered)
- `GET /api/tickets/{id}` - Get ticket
- `PATCH /api/tickets/{id}` - Update ticket
- `DELETE /api/tickets/{id}` - Revoke ticket
- `POST /api/tickets/validate` - Validate ticket at gate
- `GET /api/tickets/{id}/qr` - Get QR code

### RFID
- `POST /api/rfid` - Add authorized card
- `GET /api/rfid` - List cards
- `PATCH /api/rfid/{id}` - Update card
- `DELETE /api/rfid/{id}` - Remove card
- `POST /api/rfid/sync-to-hardware/{unit}` - Sync to ESP32

### Passages
- `GET /api/passages` - List passages (paginated, filtered)
- `GET /api/passages/stats/summary` - Statistics
- `GET /api/passages/export/csv` - Export CSV

### Users (Admin only)
- `POST /api/users` - Create user
- `GET /api/users` - List users
- `PATCH /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Deactivate user

## Development

### Running Tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm run lint
```

### Database Migrations

```bash
cd backend
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Code Style

```bash
# Backend
ruff check .
ruff format .

# Frontend
npm run lint
```

## Deployment

### Docker Compose (Development)

```bash
cd gate-dashboard
docker-compose up -d
```

### Production Deployment

1. **Backend**: Use Gunicorn + Uvicorn workers
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

2. **Frontend**: Build static files
```bash
npm run build
# Serve dist/ with nginx
```

3. **Database**: Use PostgreSQL
```env
DATABASE_URL=postgresql://user:pass@localhost/gate_dashboard
```

4. **Reverse Proxy**: Nginx configuration
```nginx
server {
    listen 80;
    server_name gate.example.com;

    location / {
        root /var/www/gate-dashboard/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Troubleshooting

### Serial Connection Issues
1. Check port permissions: `sudo usermod -a -G dialout $USER`
2. Verify baud rate matches ESP32 (115200)
3. Check `dmesg | grep tty` for port detection
4. Ensure no other process is using the port

### WebSocket Not Connecting
1. Check CORS configuration
2. Verify proxy passes WebSocket upgrade headers
3. Check browser console for errors

### Database Locked (SQLite)
- SQLite doesn't handle concurrent writes well
- Migrate to PostgreSQL for production

## License

MIT License - See LICENSE file for details