import os
import uuid

import bcrypt
from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request

from db import db

oauth = OAuth()

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def google_enabled() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def base_url(request: Request) -> str:
    import config

    return config.public_base_url(str(request.base_url))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def public_user(row) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "display_name": row["display_name"],
        "balance": round(row["balance"], 2),
        "auth_provider": row["auth_provider"],
    }


def get_user_by_id(conn, user_id: str):
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def get_user_by_email(conn, email: str):
    return conn.execute(
        "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
    ).fetchone()


def get_user_by_google_id(conn, google_id: str):
    return conn.execute("SELECT * FROM users WHERE google_id = ?", (google_id,)).fetchone()


def create_local_user(conn, email: str, password: str, display_name: str) -> dict:
    email = email.lower().strip()
    if get_user_by_email(conn, email):
        raise HTTPException(400, "An account with this email already exists")

    user_id = f"u-{uuid.uuid4().hex[:10]}"
    conn.execute(
        """
        INSERT INTO users (id, email, display_name, password_hash, auth_provider, balance)
        VALUES (?, ?, ?, ?, 'local', 1000.0)
        """,
        (user_id, email, display_name.strip(), hash_password(password)),
    )
    row = get_user_by_id(conn, user_id)
    return public_user(row)


def create_google_user(conn, google_id: str, email: str, display_name: str) -> dict:
    email = email.lower().strip()
    existing = get_user_by_google_id(conn, google_id)
    if existing:
        return public_user(existing)

    by_email = get_user_by_email(conn, email)
    if by_email:
        if by_email["google_id"] and by_email["google_id"] != google_id:
            raise HTTPException(400, "Email already registered with another method")
        conn.execute(
            "UPDATE users SET google_id = ?, auth_provider = 'google' WHERE id = ?",
            (google_id, by_email["id"]),
        )
        row = get_user_by_id(conn, by_email["id"])
        return public_user(row)

    user_id = f"u-{uuid.uuid4().hex[:10]}"
    conn.execute(
        """
        INSERT INTO users (id, email, display_name, google_id, auth_provider, balance)
        VALUES (?, ?, ?, ?, 'google', 1000.0)
        """,
        (user_id, email, display_name.strip() or email.split("@")[0], google_id),
    )
    row = get_user_by_id(conn, user_id)
    return public_user(row)


def login_session(request: Request, user: dict) -> None:
    request.session["user_id"] = user["id"]


def logout_session(request: Request) -> None:
    request.session.clear()


def get_current_user(request: Request) -> dict:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(401, "Not authenticated. Please log in.")

    with db() as conn:
        row = get_user_by_id(conn, user_id)
        if not row:
            request.session.clear()
            raise HTTPException(401, "Session expired. Please log in again.")
        return public_user(row)


def optional_user(request: Request) -> dict | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    with db() as conn:
        row = get_user_by_id(conn, user_id)
        return public_user(row) if row else None
