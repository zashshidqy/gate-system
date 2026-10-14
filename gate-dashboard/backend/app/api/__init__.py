from .auth import router as auth_router
from .gates import router as gates_router
from .tickets import router as tickets_router
from .rfid import router as rfid_router
from .passages import router as passages_router
from .dashboard import router as dashboard_router
from .users import router as users_router
from .printer import router as printer_router

__all__ = [
    "auth_router",
    "gates_router",
    "tickets_router",
    "rfid_router",
    "passages_router",
    "dashboard_router",
    "users_router",
    "printer_router",
]