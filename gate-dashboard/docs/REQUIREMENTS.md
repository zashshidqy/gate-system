# Requirements

## Functional Requirements

### 1. Gate Monitoring
- [x] Real-time display of ENTRY and EXIT gate status
- [x] Servo position indicator (0-105°)
- [x] Vehicle detection status (approach/exit sensors)
- [x] RFID reader status and version
- [x] LCD display content (row1, row2)
- [x] Master card count and list
- [x] Connection status indicators
- [x] Manual open/close controls via WebSocket

### 2. Ticket Token System
- [x] Create ticket tokens with unique codes (format: GATE-XXXXXX)
- [x] Ticket types: Single Entry, Multi Day, VIP, Staff
- [x] Configurable validity period (from/to datetime)
- [x] Configurable max uses per token
- [x] QR code generation (PNG base64 + JSON payload)
- [x] Token validation at gate (ENTRY/EXIT)
- [x] Usage tracking (timestamp, gate, direction, method)
- [x] Token revocation (soft delete)
- [x] List/filter/search tokens with pagination
- [x] QR code modal with download/copy

### 3. RFID Card Management
- [x] Add authorized cards (UID + label + note)
- [x] List cards with pagination and filters
- [x] Edit card details (label, note, active status)
- [x] Delete cards from database
- [x] Hardware sync initiation (ADD_MASTER/DEL_MASTER commands)
- [x] Master card list request from ESP32

### 4. Passage History
- [x] Paginated passage list
- [x] Filters: gate (ENTRY/EXIT), method (RFID/ANPR/MANUAL/QR), date range, status
- [x] Search by UID, plate, note
- [x] CSV export with filters
- [x] Statistics summary (total, allowed, denied, by direction/method)
- [x] Hourly breakdown for charts

### 5. User Management & Auth
- [x] JWT authentication (login/register)
- [x] Role-based access: Admin, Guard, Staff
- [x] First user auto-becomes Admin
- [x] User CRUD (Admin only)
- [x] Password change
- [x] Token refresh handling
- [x] Protected routes

### 6. Dashboard & Analytics
- [x] Overview stats (24h passages, active tickets, RFID cards)
- [x] Passage breakdown by direction/method
- [x] Hourly passage chart data
- [x] Ticket type distribution
- [x] Expiring tickets alert
- [x] Recent passages table
- [x] Recent RFID additions

### 7. Real-time Communication
- [x] WebSocket connection to backend
- [x] Gate status broadcasts (GATE_STATUS events)
- [x] Debug log broadcasts (GATE_LOG events)
- [x] Ticket events (TICKET_CREATED, TICKET_REVOKED)
- [x] RFID events (CARD_ADDED, CARD_REMOVED)
- [x] Auto-reconnection with exponential backoff

## Non-Functional Requirements

### Performance
- [x] WebSocket updates every 300ms (matches ESP32)
- [x] TanStack Query caching (5s stale time)
- [x] Pagination for large datasets
- [x] Lazy loading of modals

### Security
- [x] bcrypt password hashing (12 rounds)
- [x] JWT tokens with 8-hour expiry
- [x] HTTPS-ready (secure cookies in production)
- [x] CORS restricted to configured origins
- [x] Input validation with Pydantic
- [x] SQL injection prevention via ORM

### Usability
- [x] Responsive design (desktop/tablet/mobile)
- [x] Dark mode support (CSS variables)
- [x] Loading states and skeletons
- [x] Toast notifications for actions
- [x] Confirmation dialogs for destructive actions
- [x] Keyboard navigation support
- [x] Accessible components (Radix UI primitives)

### Reliability
- [x] Serial port auto-reconnect
- [x] WebSocket auto-reconnect (3s delay)
- [x] Graceful degradation when serial disconnected
- [x] Database connection pooling
- [x] Error boundaries (React)

### Maintainability
- [x] TypeScript strict mode
- [x] ESLint + Prettier
- [x] Ruff for Python formatting
- [x] Modular component structure
- [x] Comprehensive documentation

## Technical Requirements

### Backend
- [x] Python 3.11+
- [x] FastAPI 0.115+
- [x] SQLAlchemy 2.0+
- [x] SQLite (dev) / PostgreSQL (prod)
- [x] Alembic migrations
- [x] pyserial-asyncio for serial
- [x] python-jose for JWT
- [x] passlib[bcrypt] for passwords
- [x] qrcode[pil] for QR generation

### Frontend
- [x] React 18.3+
- [x] TypeScript 5.5+
- [x] Vite 5.4+
- [x] Tailwind CSS 3.4+
- [x] React Router 6.26+
- [x] TanStack Query 5.56+
- [x] Recharts 2.12+
- [x] lucide-react for icons
- [x] react-hot-toast for notifications

### Infrastructure
- [x] Docker Compose for local dev
- [x] Nginx reverse proxy config (docs)
- [x] systemd service example (docs)
- [x] Environment-based configuration