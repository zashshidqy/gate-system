# Gate Dashboard - Quick Start Guide

## What's New

This is a completely rebuilt Gate Dashboard with:
- **Stable connections** with automatic reconnection and retry logic
- **Modern, clean UI** that works on all devices
- **Better error handling** with clear user feedback
- **Real-time monitoring** with connection quality indicators
- **Complete feature set** for ticket and RFID card management

---

## Installation & Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- ESP32 boards connected to `/dev/ttyUSB0` and `/dev/ttyUSB1`

### 1. Backend Setup

```bash
cd gate-dashboard/backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set your SERIAL_PORT paths
```

### 2. Frontend Setup

```bash
cd gate-dashboard/frontend

# Install dependencies
npm install

# Build for production (optional)
npm run build
```

---

## Running the Application

### One command
```bash
cd gate-dashboard
./dev.sh
```

Creates `.venv`, installs Python/npm deps if missing, runs migrations, then starts both processes on IPv4.

### Start Backend
```bash
cd gate-dashboard/backend
source .venv/bin/activate
alembic upgrade head  # Initialize database
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Bind `--host 127.0.0.1` (not `localhost`) so the Vite proxy does not hit IPv6 `ECONNREFUSED`. Missing ESP32 serial ports are logged and ignored — `/health` and `/auth/*` still work.

### Start Frontend (in another terminal)
```bash
cd gate-dashboard/frontend
npm run dev
```

### Access Dashboard
- **Frontend**: http://localhost:5173
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Default login (fresh DB only)
- Username: `admin`
- Password: `admin1234`

Created automatically when the users table is empty. Change this password after first login.

---

## Key Features

### 🚪 Gate Control
- Real-time monitoring of ENTRY and EXIT gates
- One-click open/close buttons
- Servo position display
- Vehicle detection alerts
- LCD display emulation

### 🎫 Ticket Management
- Create tickets with custom validity periods
- Generate and view QR codes
- Track ticket usage
- Filter by type and status
- Copy codes easily

### 🏷️ RFID Card Management
- Add authorized cards with labels
- Toggle active/inactive status
- Sync cards to hardware
- Search and filter cards
- Edit card information

### 📊 Passage History
- View all gate passages
- Filter by date, direction, method, status
- Export to CSV
- Real-time updates

### 📱 Responsive Design
- Works on desktop, tablet, and mobile
- Touch-friendly controls
- Adaptive layout
- Dark/light mode support

---

## Connection Indicators

### Header Status Bar
- **Live Badge**: Shows WebSocket connection status
- **Gate Indicators**: Green (connected) / Red (offline)
- **Signal Quality**: Excellent / Good / Poor / Offline
- **User Profile**: Current user and logout option

### Dashboard Connection
- Auto-reconnects if WebSocket drops
- Shows 3 reconnection attempts before warning
- Exponential backoff prevents connection flooding
- Clear error messages

---

## API Usage Examples

### Get Gate Status
```bash
curl http://localhost:8000/gates/status
```

### Send Command to ENTRY Gate
```bash
curl -X POST "http://localhost:8000/gates/command?unit=ENTRY&command=O" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Create Ticket
```bash
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "type": "SINGLE_ENTRY",
    "max_uses": 1,
    "valid_until": "2026-12-31T23:59:59"
  }'
```

### List RFID Cards
```bash
curl "http://localhost:8000/rfid?page=1&page_size=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Troubleshooting

### WebSocket Connection Issues

**Problem**: "Offline" status in header
**Solutions**:
1. Check if backend is running: `curl http://localhost:8000/health`
2. Check browser console (F12) for error messages
3. Verify CORS configuration in `.env`
4. Try a different browser or incognito mode

### Gate Not Responding

**Problem**: Gates show "Disconnected"
**Solutions**:
1. Check USB connections: `ls /dev/ttyUSB*`
2. Verify permissions: `sudo usermod -a -G dialout $USER`
3. Check baud rate (should be 115200)
4. Restart backend service

### API Errors

**Problem**: "Failed to send command"
**Solutions**:
1. Check authentication token
2. Verify gate unit name (ENTRY or EXIT)
3. Check command is valid (O, C, A, Q, L, R, X, Z)
4. Check backend logs for detailed errors

### Frontend Not Loading

**Problem**: Blank page or "Cannot GET /"
**Solutions**:
1. Check frontend is running: `npm run dev`
2. Clear browser cache: Ctrl+Shift+Delete
3. Check console for JavaScript errors
4. Verify API base URL in network tab

---

## Database

The application uses SQLite by default for development.

### Reset Database
```bash
cd gate-dashboard/backend
rm gate.db
alembic upgrade head
```

### Backup Database
```bash
cp gate-dashboard/backend/gate.db gate.db.backup
```

---

## Performance Tips

1. **Clear Filters**: Fewer filters = faster queries
2. **Use Pagination**: Don't request all records at once
3. **Browser Cache**: Enable browser caching for static assets
4. **Connection Quality**: Stay near WiFi/Ethernet for stable WebSocket

---

## Security

### Default Credentials
On a fresh database the API seeds:
- Username: `admin`
- Password: `admin1234`

Change this password after first login. Existing users are never overwritten.

### JWT Token
- Stored in browser localStorage
- 480-minute expiration (configurable)
- Required for all API requests
- Automatically cleared on 401 response

### CORS
Configure allowed origins in `.env`:
```
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

## Docker Deployment

### Build Images
```bash
cd gate-dashboard
docker-compose build
```

### Run with Docker
```bash
export JWT_SECRET="your-super-secret-key-32-chars-min"
export SERIAL_PORT_ENTRY=/dev/ttyUSB0
export SERIAL_PORT_EXIT=/dev/ttyUSB1
docker-compose up -d
```

### View Logs
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

---

## Keyboard Shortcuts

- **Ctrl/Cmd + K**: Focus search (in tables)
- **Escape**: Close modals and dialogs
- **Enter**: Submit forms

---

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Android)

---

## Environment Variables

### Backend (.env)
```
# Serial Ports
SERIAL_PORT_ENTRY=/dev/ttyUSB0
SERIAL_PORT_EXIT=/dev/ttyUSB1
SERIAL_BAUDRATE=115200

# Database
DATABASE_URL=sqlite:///./gate.db

# JWT
JWT_SECRET=your-super-secret-key-change-in-production-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Logging
APP_ENV=development
LOG_LEVEL=INFO
```

---

## Support & Documentation

- **API Documentation**: http://localhost:8000/docs
- **Design System**: See `COLOR_PALETTE.md`
- **README**: See `README.md` for project overview

---

## Common Tasks

### Add a New RFID Card
1. Go to "RFID Cards" page
2. Click "Add Card" button
3. Enter card UID (hex format)
4. Add label (optional)
5. Click "Save"

### Create a Ticket
1. Go to "Tickets" page
2. Click "Create Ticket" button
3. Select ticket type
4. Set validity date (optional)
5. Set max uses (optional)
6. Click "Create"
7. View QR code to print or share

### Export Passage History
1. Go to "Passages" page
2. Apply filters as needed
3. Click "Export CSV" button
4. File downloads automatically

### Check Gate Connection
1. Look at header status bar
2. Green dot = connected
3. Red dot = disconnected
4. Signal indicator shows quality

---

## Next Steps

1. ✅ Start backend and frontend
2. ✅ Login to dashboard
3. ✅ Verify gate connections
4. ✅ Test gate open/close commands
5. ✅ Add test RFID cards
6. ✅ Create test tickets
7. ✅ Review passage history

---

## Getting Help

### Check Logs
**Backend logs** show serial communication and API errors
**Frontend logs** show WebSocket and network issues

### Enable Debug Mode
Set `LOG_LEVEL=DEBUG` in `.env` for detailed backend logs

### Browser DevTools
- Network tab: Check API calls and WebSocket
- Console tab: JavaScript errors and warnings
- Application tab: Local storage and session data

---

## Performance Metrics

- **Dashboard Load**: < 2 seconds
- **API Response**: < 500ms (with retry)
- **WebSocket Latency**: < 100ms
- **Database Query**: < 50ms

---

Good luck with the Gate Dashboard! 🚀
