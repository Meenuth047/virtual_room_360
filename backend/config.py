import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
DB_PATH = DATA_DIR / "app.db"

DATA_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

# Session cookie settings
SESSION_COOKIE_NAME = "session_token"
SESSION_TTL_HOURS = int(os.environ.get("SESSION_TTL_HOURS", "72"))

# Image / upload limits (configurable per spec section 4)
MIN_IMAGES = int(os.environ.get("MIN_IMAGES", "8"))
RECOMMENDED_MIN_IMAGES = int(os.environ.get("RECOMMENDED_MIN_IMAGES", "15"))
RECOMMENDED_MAX_IMAGES = int(os.environ.get("RECOMMENDED_MAX_IMAGES", "30"))
MAX_IMAGES = int(os.environ.get("MAX_IMAGES", "40"))

MAX_FILE_SIZE_MB = int(os.environ.get("MAX_FILE_SIZE_MB", "15"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Resize very large source images before processing to keep memory usage low
MAX_SOURCE_DIMENSION = int(os.environ.get("MAX_SOURCE_DIMENSION", "2000"))

# CORS - adjust for your deployment
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:8000").split(",")
