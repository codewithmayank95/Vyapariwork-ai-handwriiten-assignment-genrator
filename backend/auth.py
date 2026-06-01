from __future__ import annotations

from pathlib import Path
from typing import Optional

from config import SETTINGS


class AuthError(Exception):
    pass


def verify_firebase_token(firebase_token: str | None) -> Optional[str]:
    """
    Optional Firebase Auth verification.

    - If FIREBASE_CREDENTIALS_PATH is configured and firebase-admin is installed,
      verifies the token and returns user_id (uid).
    - Otherwise returns None (guest mode).
    """
    if not firebase_token:
        return None

    if not SETTINGS.firebase_credentials_path:
        return None

    creds_path = Path(SETTINGS.firebase_credentials_path)
    if not creds_path.exists():
        return None

    try:
        import firebase_admin  # type: ignore
        from firebase_admin import auth as fb_auth  # type: ignore
        from firebase_admin import credentials  # type: ignore
    except Exception:
        return None

    # Initialize app once
    if not firebase_admin._apps:
        cred = credentials.Certificate(str(creds_path))
        firebase_admin.initialize_app(cred)

    try:
        decoded = fb_auth.verify_id_token(firebase_token)
        uid = decoded.get("uid")
        if not uid:
            raise AuthError("Invalid Firebase token (uid missing).")
        return str(uid)
    except Exception as e:
        raise AuthError(f"Firebase token verification failed: {e}") from e

