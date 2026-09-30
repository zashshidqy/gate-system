# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure
- FastAPI backend with serial bridge
- React + TypeScript frontend with Vite
- Real-time WebSocket communication
- Ticket token management with QR codes
- RFID authorized card management
- Passage history with filtering and export
- User authentication and role-based access control
- Dashboard with real-time gate monitoring

## [0.1.0] - 2026-09-28

### Added
- Core backend API (FastAPI)
- Serial bridge for ESP32 communication
- WebSocket manager for real-time updates
- Database models (Passages, Tickets, RFID Cards, Users)
- JWT authentication
- Ticket validation engine
- QR code generation
- Dashboard page with gate status cards
- Tickets page with CRUD operations
- RFID page with hardware sync
- Passages page with filters and CSV export
- Settings page with user management
- Responsive UI with Tailwind CSS + shadcn/ui
- Docker Compose for development

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- JWT-based authentication with bcrypt password hashing
- Role-based access control (Admin, Guard, Staff)
- CORS configuration