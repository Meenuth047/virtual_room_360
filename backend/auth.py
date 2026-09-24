from datetime import datetime

from fastapi import Cookie, HTTPException, status

from . import config
from .db import db_cursor


def get_current_user(session_token: str | None = Cookie(default=None, alias=config.SESSION_COOKIE_NAME)):
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    with db_cursor() as cur:
        cur.execute(
            "SELECT sessions.user_id, sessions.expires_at, users.id, users.name, users.email, users.is_active "
            "FROM sessions JOIN users ON users.id = sessions.user_id "
            "WHERE sessions.token = ?",
            (session_token,),
        )
        row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    expires_at = datetime.fromisoformat(row["expires_at"])
    if expires_at < datetime.utcnow():
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM sessions WHERE token = ?", (session_token,))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    if not row["is_active"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    return {"id": row["id"], "name": row["name"], "email": row["email"]}
