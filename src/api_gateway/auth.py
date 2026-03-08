"""JWT authentication utilities for the API Gateway."""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SECRET_KEY: str = os.getenv("JWT_SECRET", "change-me-in-production")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS: int = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

# bcrypt enforces a 72-byte maximum for passwords.
_BCRYPT_MAX_PASSWORD_BYTES = 72


def _encode_password(password: str) -> bytes:
    """Encode *password* as UTF-8 and truncate to 72 bytes for bcrypt.

    Truncation is done at a character boundary so that multi-byte UTF-8
    sequences are never split in the middle.
    """
    encoded = password.encode("utf-8")
    if len(encoded) <= _BCRYPT_MAX_PASSWORD_BYTES:
        return encoded
    # Decode back with errors="ignore" to drop any incomplete trailing
    # multi-byte sequence, then re-encode to get a valid 72-byte prefix.
    return encoded[:_BCRYPT_MAX_PASSWORD_BYTES].decode("utf-8", errors="ignore").encode("utf-8")


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if *plain_password* matches its stored hash."""
    return bcrypt.checkpw(_encode_password(plain_password), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """Return the bcrypt hash of *password*."""
    return bcrypt.hashpw(_encode_password(password), bcrypt.gensalt()).decode("utf-8")


# Fake user store – replace with a real database in production.
# The hash below is a pre-computed bcrypt hash of "secret" to avoid
# paying the bcrypt cost on every application startup.
_ADMIN_PASSWORD_HASH = "$2b$12$kmocYXIyLlFHj77nGqhjFemzaURy899kQqjneriImACBY9/wwp5Yu"

FAKE_USERS_DB: dict = {
    "admin": {
        "username": "admin",
        "hashed_password": _ADMIN_PASSWORD_HASH,
        "disabled": False,
    }
}


# ---------------------------------------------------------------------------
# User lookup
# ---------------------------------------------------------------------------


def get_user(username: str) -> Optional[dict]:
    """Return user dict from the fake DB or None if not found."""
    return FAKE_USERS_DB.get(username)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Verify credentials and return the user dict, or None on failure."""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


# ---------------------------------------------------------------------------
# Token creation / validation
# ---------------------------------------------------------------------------


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create and return a signed JWT access token.

    Args:
        data: Payload data to embed in the token.
        expires_delta: Custom expiry duration; defaults to
            ACCESS_TOKEN_EXPIRE_HOURS if not provided.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token.

    Args:
        token: Encoded JWT string.

    Returns:
        Decoded payload dict, or None if the token is invalid / expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
