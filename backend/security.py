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


def utc_now() -> datetime:
    """Return current UTC time as naive datetime for consistent SQLite storage."""
    from datetime import timezone
    return datetime.now(timezone.utc).replace(tzinfo=None)


def session_expiry() -> datetime:
    return utc_now() + timedelta(hours=config.SESSION_TTL_HOURS)


def generate_otp() -> str:
    """Generate a cryptographically secure 6-digit numeric OTP."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(otp: str) -> str:
    """Hash OTP using Argon2id."""
    return hash_password(otp)


def verify_otp(otp: str, otp_hash: str) -> bool:
    """Verify OTP against its Argon2id hash."""
    return verify_password(otp, otp_hash)


def otp_expiry() -> datetime:
    """Calculate expiry datetime for OTP."""
    return utc_now() + timedelta(minutes=config.OTP_TTL_MINUTES)


def generate_reset_token() -> str:
    """Generate a cryptographically secure random reset token."""
    return secrets.token_urlsafe(32)


def hash_reset_token(token: str) -> str:
    """Hash a reset token using SHA-256."""
    import hashlib
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def safe_filename(original_name: str, fallback_ext: str = ".jpg") -> str:
    """Generate a random, safe filename, preserving a validated extension.
    Never trust user-provided filenames directly (prevents path traversal)."""
    ext = ""
    if "." in original_name:
        ext = "." + original_name.rsplit(".", 1)[-1].lower()
    if ext not in config.ALLOWED_IMAGE_EXTENSIONS:
        ext = fallback_ext
    return f"{secrets.token_hex(16)}{ext}"
