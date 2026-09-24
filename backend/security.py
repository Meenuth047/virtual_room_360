import re
import secrets
from datetime import datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

from . import config

_hasher = PasswordHasher()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def validate_password_strength(password: str) -> str | None:
    """Returns an error message if invalid, else None."""
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"[0-9]", password):
        return "Password must contain both letters and numbers."
    return None


def validate_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email))


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def session_expiry() -> datetime:
    return datetime.utcnow() + timedelta(hours=config.SESSION_TTL_HOURS)


def safe_filename(original_name: str, fallback_ext: str = ".jpg") -> str:
    """Generate a random, safe filename, preserving a validated extension.
    Never trust user-provided filenames directly (prevents path traversal)."""
    ext = ""
    if "." in original_name:
        ext = "." + original_name.rsplit(".", 1)[-1].lower()
    if ext not in config.ALLOWED_IMAGE_EXTENSIONS:
        ext = fallback_ext
    return f"{secrets.token_hex(16)}{ext}"
