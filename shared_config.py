"""Shared config between store and admin apps."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "orders.db"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
ADMIN_PASSWORD = "streampack2026"
MOZ_TZ_HOURS = 2
