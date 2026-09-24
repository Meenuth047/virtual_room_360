from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr

from .. import config, security
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
