"""Main FastAPI application"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import init_db, SessionLocal
from .api import (
    auth_router,
    gates_router,
    tickets_router,
    rfid_router,
    passages_router,
    dashboard_router,
    users_router,
    printer_router,
)
from .services.serial_bridge import SerialBridge
from .websocket.manager import ws_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()
serial_bridge: SerialBridge = None


def seed_default_admin() -> None:
    """Create a default admin if the users table is empty. Does not overwrite existing users."""
    from .models.user import User, UserRole
    from .api.auth import get_password_hash

    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            admin = User(
                username="admin",
                hashed_password=get_password_hash("admin1234"),
                full_name="Administrator",
                role=UserRole.ADMIN,
                active=True,
            )
            db.add(admin)
            db.commit()
            logger.info("Created default admin user 'admin' (change this password).")
    except Exception:
        db.rollback()
        logger.exception("Failed to seed default admin user")
        raise
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global serial_bridge
    logger.info("Starting Gate Dashboard...")

    # Initialize database
    init_db()
    seed_default_admin()
    logger.info("Database initialized")

    # Start serial bridge
    serial_bridge = SerialBridge(ws_manager)
    try:
        await serial_bridge.start()
        logger.info("Serial bridge started")
    except Exception as e:
        logger.error(f"Failed to start serial bridge: {e}")

    # Make serial_bridge available to routes
    import sys
    from .api import gates
    gates.serial_bridge = serial_bridge

    yield

    # Shutdown
    logger.info("Shutting down...")
    if serial_bridge:
        await serial_bridge.stop()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Gate Dashboard API",
    description="Staff Dashboard for Smart Gate System with Ticket Token Support",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(gates_router)
app.include_router(tickets_router)
app.include_router(rfid_router)
app.include_router(passages_router)
app.include_router(dashboard_router)
app.include_router(users_router)
app.include_router(printer_router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "serial_connected": {
            unit: serial_bridge.is_connected(unit) if serial_bridge else False
            for unit in ("ENTRY", "EXIT")
        },
    }


@app.get("/")
async def root():
    return {
        "name": "Gate Dashboard API",
        "version": "0.1.0",
        "docs": "/docs",
    }