import os
import logging
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

from . import config

logger = logging.getLogger("panorama.email")

# In-memory store for development/testing only
_dev_otp_store: dict[str, str] = {}


def _get_smtp_settings():
    # Reload .env so changes are picked up immediately
    load_dotenv(config.BASE_DIR / ".env", override=False)
    host = os.environ.get("SMTP_HOST", config.SMTP_HOST)
    port_val = os.environ.get("SMTP_PORT", str(config.SMTP_PORT or 465))
    try:
        port = int(port_val)
    except (ValueError, TypeError):
        port = 465
    username = os.environ.get("SMTP_USERNAME", config.SMTP_USERNAME)
    password = os.environ.get("SMTP_PASSWORD", config.SMTP_PASSWORD)
    from_addr = os.environ.get("SMTP_FROM", config.SMTP_FROM or "noreply@360rooms.local")
    use_tls = os.environ.get("SMTP_USE_TLS", str(config.SMTP_USE_TLS)).lower() in ("true", "1", "yes")
    use_ssl = os.environ.get("SMTP_USE_SSL", str(config.SMTP_USE_SSL)).lower() in ("true", "1", "yes")
    env = os.environ.get("ENVIRONMENT", config.ENVIRONMENT)
    try:
        ttl = int(os.environ.get("OTP_TTL_MINUTES", str(config.OTP_TTL_MINUTES or 10)))
    except (ValueError, TypeError):
        ttl = 10

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "from": from_addr,
        "use_tls": use_tls,
        "use_ssl": use_ssl,
        "environment": env,
        "ttl": ttl,
    }


def send_otp_email(to_email: str, otp: str) -> bool:
    """Send a 6-digit OTP to the specified email address via SMTP.
    Follows all security requirements:
    - Never logs the plaintext OTP in production
    - Uses SMTP environment configuration
    - Automatically falls back to port 465 SSL if port 587 STARTTLS times out
    """
    settings = _get_smtp_settings()
    host = settings["host"]
    port = settings["port"]
    username = settings["username"]
    password = settings["password"]
    from_email = settings["from"]
    use_ssl = settings["use_ssl"]
    use_tls = settings["use_tls"]
    environment = settings["environment"]
    ttl = settings["ttl"]

    subject = "Password Reset OTP"
    body = (
        "Your password reset OTP is:\n\n"
        f"{otp}\n\n"
        f"This OTP expires in {ttl} minutes.\n\n"
        "If you did not request a password reset, you can safely ignore this email.\n"
    )

    if not host:
        if environment != "production":
            _dev_otp_store[to_email.lower()] = otp
            logger.warning(
                "SMTP_HOST not set in .env! Email could not be sent to %s. "
                "[DEV MODE OTP]: %s (Configure SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD in .env to receive real emails)",
                to_email,
                otp,
            )
        else:
            logger.warning("SMTP_HOST not configured; cannot deliver password reset email.")
        return True

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg.set_content(body)

    def _attempt_send(h, p, ssl_mode, tls_mode):
        if ssl_mode or p == 465:
            server = smtplib.SMTP_SSL(h, p, timeout=10)
        else:
            server = smtplib.SMTP(h, p, timeout=10)

        with server:
            if tls_mode and not (ssl_mode or p == 465):
                server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(msg)
        return True

    try:
        _attempt_send(host, port, use_ssl, use_tls)
        logger.info("Password reset OTP email sent successfully to %s", to_email)
        return True
    except Exception as e:
        logger.warning("Primary SMTP attempt to %s via port %d failed: %s", to_email, port, str(e))
        # If port 587 or STARTTLS timed out or failed, try port 465 with SSL automatically
        if not use_ssl and port != 465:
            try:
                logger.info("Attempting automatic fallback to port 465 (SSL) for %s...", host)
                _attempt_send(host, 465, ssl_mode=True, tls_mode=False)
                logger.info("Fallback to port 465 succeeded! Email delivered to %s", to_email)
                return True
            except Exception as e2:
                logger.error("Fallback to port 465 also failed for %s: %s", to_email, str(e2))
        return False


def get_dev_otp_for_test(email: str) -> str | None:
    """Retrieve last sent OTP in non-production environment for testing purposes."""
    settings = _get_smtp_settings()
    if settings["environment"] == "production":
        return None
    return _dev_otp_store.get(email.lower())
