# TODO

## Immediate (v0.1.x)

### Backend
- [ ] Add integration tests for serial bridge
- [ ] Implement ticket validation via RFID link (associate token with UID)
- [ ] Add ANPR plate capture integration
- [ ] Implement passage logging from ESP32 to database
- [ ] Add rate limiting for API endpoints
- [ ] Add request logging middleware
- [ ] Implement database backup script
- [ ] Add health check endpoint with serial status

### Frontend
- [ ] Add dark mode toggle in header
- [ ] Implement keyboard shortcuts (e.g., O=open, C=close)
- [ ] Add sound notifications for gate events
- [ ] Improve mobile layout for gate cards
- [ ] Add print-friendly ticket view
- [ ] Implement offline queue for commands
- [ ] Add PWA manifest and service worker
- [ ] Add charts for passage analytics (Recharts)

### Documentation
- [ ] API documentation with Swagger/OpenAPI
- [ ] ESP32 firmware integration guide
- [ ] Deployment guide for Raspberry Pi
- [ ] Troubleshooting FAQ

## Short-term (v0.2.0)

### Features
- [ ] Multi-gate support (more than 2 gates)
- [ ] Ticket templates (pre-defined configurations)
- [ ] Bulk ticket generation (CSV import)
- [ ] Email/SMS notifications for ticket expiry
- [ ] Visitor management (check-in/out with photos)
- [ ] Shift scheduling for guards
- [ ] Audit log for all admin actions
- [ ] Two-factor authentication (TOTP)

### Integrations
- [ ] MQTT bridge for IoT integration
- [ ] Home Assistant integration
- [ ] Slack/Discord webhooks for alerts
- [ ] Prometheus metrics endpoint
- [ ] Grafana dashboard templates

### Hardware
- [ ] Support for ESP32-CAM (ANPR images)
- [ ] Support for multiple RFID readers per gate
- [ ] Support for barrier/boom gate actuators
- [ ] Battery/UPS monitoring
- [ ] Environmental sensors (temp/humidity)

## Medium-term (v0.3.0)

### Advanced Features
- [ ] License plate recognition (ANPR) dashboard
- [ ] Vehicle type classification
- [ ] Parking duration tracking
- [ ] Revenue tracking for paid parking
- [ ] Subscription/membership management
- [ ] Mobile app (React Native/Expo)
- [ ] Kiosk mode for self-service

### Scalability
- [ ] PostgreSQL read replicas
- [ ] Redis caching layer
- [ ] Horizontal scaling with load balancer
- [ ] Multi-tenant architecture
- [ ] API rate limiting per tenant

## Long-term (v1.0.0)

### Platform
- [ ] Plugin system for custom integrations
- [ ] White-label branding
- [ ] Marketplace for extensions
- [ ] Multi-language support (i18n)
- [ ] Advanced reporting engine
- [ ] AI-powered anomaly detection

### Hardware Abstraction
- [ ] Support for different gate controllers
- [ ] Generic sensor abstraction layer
- [ ] Firmware update management (OTA)
- [ ] Device provisioning workflow

## Technical Debt

### Code Quality
- [ ] Increase test coverage to >80%
- [ ] Add E2E tests with Playwright
- [ ] Implement API versioning
- [ ] Add database migration rollback tests
- [ ] Improve TypeScript strictness

### Performance
- [ ] Virtual scrolling for large tables
- [ ] WebSocket message batching
- [ ] Database query optimization
- [ ] CDN for static assets
- [ ] Image optimization for captures

### Security
- [ ] Security audit
- [ ] Penetration testing
- [ ] GDPR compliance features
- [ ] Data retention policies
- [ ] Encryption at rest for sensitive data

## Ideas / Nice to Have

- [ ] Voice commands for gate control
- [ ] AR visualization for gate status
- [ ] Predictive maintenance alerts
- [ ] Integration with access control systems
- [ ] Visitor pre-registration portal
- [ ] QR code on receipt printers
- [ ] Facial recognition (privacy-compliant)
- [ ] Blockchain-based ticket verification