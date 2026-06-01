"""Auto-config for Render — no manual env vars required for email login."""

import hashlib
import os


def is_production() -> bool:
    return bool(os.environ.get("RENDER")) or os.environ.get("ENV") == "production"


def session_secret_key() -> str:
    """Stable secret on Render without user configuration."""
    key = os.environ.get("SECRET_KEY", "").strip()
    # Common mistake: Google client secret pasted as SECRET_KEY
    if key and not key.startswith("GOCSPX-"):
        return key

    service_id = os.environ.get("RENDER_SERVICE_ID", "predictx")
    return hashlib.sha256(f"{service_id}:predictx-v1".encode()).hexdigest()


def public_base_url(request_base: str = "") -> str:
    for name in ("BASE_URL", "RENDER_EXTERNAL_URL"):
        value = os.environ.get(name, "").strip()
        if value:
            return value.rstrip("/")
    if request_base:
        return request_base.rstrip("/")
    return "http://localhost:8000"


def admin_emails() -> set[str]:
    raw = os.environ.get("ADMIN_EMAIL", "").strip()
    if not raw:
        return set()
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def is_admin(email: str | None) -> bool:
    if not email:
        return False
    admins = admin_emails()
    return bool(admins) and email.lower() in admins
