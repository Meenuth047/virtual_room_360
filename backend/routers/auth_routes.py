from datetime import datetime, timedelta
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr

from .. import config, email_service, security
from ..auth import get_current_user
from ..db import db_cursor, seed_default_categories

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResendOtpRequest(BaseModel):
    email: EmailStr


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    reset_token: str
    new_password: str
    confirm_password: str


def _set_session_cookie(response: Response, token: str):
    response.set_cookie(
        key=config.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # set True when served over HTTPS in production
        max_age=config.SESSION_TTL_HOURS * 3600,
        path="/",
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response):
    name = payload.name.strip()
    email = payload.email.strip().lower()

    if not name:
        raise HTTPException(status_code=400, detail="Name is required.")

    pw_error = security.validate_password_strength(payload.password)
    if pw_error:
        raise HTTPException(status_code=400, detail=pw_error)

    with db_cursor() as cur:
        cur.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="An account with this email already exists.")

    password_hash = security.hash_password(payload.password)

    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        user_id = cur.lastrowid

    seed_default_categories(user_id)

    token = security.generate_session_token()
    expires = security.session_expiry()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires.isoformat()),
        )

    _set_session_cookie(response, token)
    return {"id": user_id, "name": name, "email": email}


@router.post("/login")
def login(payload: LoginRequest, response: Response):
    email = payload.email.strip().lower()

    with db_cursor() as cur:
        cur.execute(
            "SELECT id, name, email, password_hash, is_active FROM users WHERE email = ?",
            (email,),
        )
        user = cur.fetchone()

    # Generic error message - never reveal whether the email exists
    invalid_msg = "Invalid email or password."

    if user is None:
        raise HTTPException(status_code=401, detail=invalid_msg)

    if not security.verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail=invalid_msg)

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Account disabled.")

    token = security.generate_session_token()
    expires = security.session_expiry()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user["id"], expires.isoformat()),
        )

    _set_session_cookie(response, token)
    return {"id": user["id"], "name": user["name"], "email": user["email"]}


@router.post("/logout")
def logout(
    response: Response,
    user=Depends(get_current_user),
    session_token: str | None = Cookie(default=None, alias=config.SESSION_COOKIE_NAME),
):
    if session_token:
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM sessions WHERE token = ?", (session_token,))
    response.delete_cookie(config.SESSION_COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
def me(user=Depends(get_current_user)):
    return user


# Rate-limiting tracking (email -> list of request timestamps) to prevent enumeration via timing/status
_request_tracker: dict[str, list[datetime]] = {}


def _enforce_rate_limit(email: str, cur=None, user_id: int | None = None):
    now = security.utc_now()
    history = _request_tracker.get(email, [])
    # Keep only requests within the last hour
    history = [t for t in history if (now - t).total_seconds() < 3600]
    _request_tracker[email] = history

    if history:
        last_req = history[-1]
        elapsed = (now - last_req).total_seconds()
        if elapsed < config.OTP_COOLDOWN_SECONDS:
            remaining = int(config.OTP_COOLDOWN_SECONDS - elapsed) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {remaining} seconds before requesting another OTP.",
            )

    if len(history) >= config.OTP_MAX_REQUESTS_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Maximum OTP requests exceeded. Please try again later.",
        )

    # Also check database record if cur and user_id are supplied
    if cur and user_id:
        cur.execute(
            "SELECT last_requested_at FROM password_reset_tokens WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
        row = cur.fetchone()
        if row and row["last_requested_at"]:
            try:
                db_last_req = datetime.fromisoformat(row["last_requested_at"])
                db_elapsed = (now - db_last_req).total_seconds()
                if db_elapsed < config.OTP_COOLDOWN_SECONDS:
                    remaining = int(config.OTP_COOLDOWN_SECONDS - db_elapsed) + 1
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Please wait {remaining} seconds before requesting another OTP.",
                    )
            except (ValueError, TypeError):
                pass


def _record_rate_limit(email: str):
    now = security.utc_now()
    if email not in _request_tracker:
        _request_tracker[email] = []
    _request_tracker[email].append(now)


def _generate_and_save_otp(cur, user_id: int, email: str):
    # Invalidate any existing unused reset tokens for this user
    cur.execute(
        "UPDATE password_reset_tokens SET used = 1 WHERE user_id = ? AND used = 0",
        (user_id,),
    )

    otp = security.generate_otp()
    otp_hash = security.hash_otp(otp)
    expires_at = security.otp_expiry().isoformat()
    now_str = security.utc_now().isoformat()

    cur.execute(
        "INSERT INTO password_reset_tokens (user_id, otp_hash, expires_at, attempts, used, created_at, last_requested_at) "
        "VALUES (?, ?, ?, 0, 0, ?, ?)",
        (user_id, otp_hash, expires_at, now_str, now_str),
    )

    # Deliver OTP via SMTP
    email_service.send_otp_email(email, otp)


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest):
    email = payload.email.strip().lower()
    standard_msg = {"message": "If an account exists for this email, a password reset OTP has been sent."}

    # Enforce rate limit across all requests to prevent enumeration & abuse
    _enforce_rate_limit(email)

    with db_cursor() as cur:
        cur.execute("SELECT id, is_active FROM users WHERE email = ?", (email,))
        user = cur.fetchone()

    _record_rate_limit(email)

    if user and user["is_active"]:
        with db_cursor(commit=True) as cur:
            _generate_and_save_otp(cur, user["id"], email)

    return standard_msg


@router.post("/resend-otp")
def resend_otp(payload: ResendOtpRequest):
    email = payload.email.strip().lower()

    # Enforce rate limit
    _enforce_rate_limit(email)

    with db_cursor() as cur:
        cur.execute("SELECT id, is_active FROM users WHERE email = ?", (email,))
        user = cur.fetchone()

    _record_rate_limit(email)

    if user and user["is_active"]:
        with db_cursor(commit=True) as cur:
            _generate_and_save_otp(cur, user["id"], email)
        return {"message": "A new OTP has been sent to your email."}

    return {"message": "If an account exists for this email, a password reset OTP has been sent."}


@router.post("/verify-otp")
def verify_otp(payload: VerifyOtpRequest):
    email = payload.email.strip().lower()
    otp = payload.otp.strip()

    if len(otp) != 6 or not otp.isdigit():
        raise HTTPException(status_code=400, detail="Invalid OTP format. Must be a 6-digit number.")

    invalid_msg = "Invalid or expired OTP."

    with db_cursor() as cur:
        cur.execute("SELECT id, is_active FROM users WHERE email = ?", (email,))
        user = cur.fetchone()

    if not user or not user["is_active"]:
        raise HTTPException(status_code=400, detail=invalid_msg)

    user_id = user["id"]

    with db_cursor(commit=True) as cur:
        cur.execute(
            "SELECT id, otp_hash, expires_at, attempts, used FROM password_reset_tokens "
            "WHERE user_id = ? AND used = 0 ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
        token_row = cur.fetchone()

        if not token_row:
            raise HTTPException(status_code=400, detail=invalid_msg)

        # Check expiration
        expires_at = datetime.fromisoformat(token_row["expires_at"])
        if expires_at < security.utc_now():
            cur.execute("UPDATE password_reset_tokens SET used = 1 WHERE id = ?", (token_row["id"],))
            cur.connection.commit()
            raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

        # Check max attempts
        if token_row["attempts"] >= config.OTP_MAX_ATTEMPTS:
            cur.execute("UPDATE password_reset_tokens SET used = 1 WHERE id = ?", (token_row["id"],))
            cur.connection.commit()
            raise HTTPException(
                status_code=400,
                detail="Maximum verification attempts exceeded. Please request a new OTP.",
            )

        # Verify OTP with Argon2id
        if not security.verify_otp(otp, token_row["otp_hash"]):
            new_attempts = token_row["attempts"] + 1
            if new_attempts >= config.OTP_MAX_ATTEMPTS:
                cur.execute("UPDATE password_reset_tokens SET attempts = ?, used = 1 WHERE id = ?", (new_attempts, token_row["id"]))
                cur.connection.commit()
                raise HTTPException(
                    status_code=400,
                    detail="Invalid OTP. Maximum verification attempts exceeded. Please request a new OTP.",
                )
            else:
                cur.execute("UPDATE password_reset_tokens SET attempts = ? WHERE id = ?", (new_attempts, token_row["id"]))
                cur.connection.commit()
                remaining = config.OTP_MAX_ATTEMPTS - new_attempts
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid OTP. {remaining} attempt{'s' if remaining != 1 else ''} remaining.",
                )

        # OTP verified! Generate secure reset token
        reset_token = security.generate_reset_token()
        reset_token_hash = security.hash_reset_token(reset_token)
        cur.execute(
            "UPDATE password_reset_tokens SET reset_token_hash = ? WHERE id = ?",
            (reset_token_hash, token_row["id"]),
        )

    return {"reset_token": reset_token, "message": "OTP verified successfully."}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest):
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    pw_error = security.validate_password_strength(payload.new_password)
    if pw_error:
        raise HTTPException(status_code=400, detail=pw_error)

    email = payload.email.strip().lower()
    token_hash = security.hash_reset_token(payload.reset_token)

    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id, is_active FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        if not user or not user["is_active"]:
            raise HTTPException(status_code=400, detail="Invalid or expired reset session. Please start over.")

        user_id = user["id"]

        cur.execute(
            "SELECT id, expires_at FROM password_reset_tokens "
            "WHERE user_id = ? AND used = 0 AND reset_token_hash = ?",
            (user_id, token_hash),
        )
        token_row = cur.fetchone()

        if not token_row:
            raise HTTPException(status_code=400, detail="Invalid or expired reset session. Please start over.")

        expires_at = datetime.fromisoformat(token_row["expires_at"])
        if expires_at < security.utc_now():
            cur.execute("UPDATE password_reset_tokens SET used = 1 WHERE id = ?", (token_row["id"],))
            cur.connection.commit()
            raise HTTPException(status_code=400, detail="Reset session has expired. Please start over.")

        # Hash new password with Argon2id
        password_hash = security.hash_password(payload.new_password)

        # 1. Update password in SQLite users table
        cur.execute(
            "UPDATE users SET password_hash = ?, updated_at = datetime('now') WHERE id = ?",
            (password_hash, user_id),
        )

        # 2. Mark this token as used and invalidate all active reset tokens for this user
        cur.execute(
            "UPDATE password_reset_tokens SET used = 1 WHERE user_id = ?",
            (user_id,),
        )

        # 3. Invalidate existing authenticated sessions
        cur.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    return {"message": "Password reset successfully. Please log in with your new password."}
