"""
auth.py
-------
Password accounts and bearer tokens for the ATLAS API.

- Passwords are stored as salted scrypt hashes in users.password_hash.
  Accounts created before passwords existed have NULL there and cannot log in
  until an admin runs set_password.py for them.
- /auth/login and /auth/signup return a signed JWT (HS256 over AUTH_SECRET);
  every per-learner, session and admin endpoint requires it as
  `Authorization: Bearer <token>`.
- Admin rights are not baked into the token: require_admin re-checks the
  token's user_name against ADMIN_USERNAMES on every request, so removing a
  name takes effect immediately.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

load_dotenv()

PASSWORD_MIN_LENGTH = 8
TOKEN_TTL_SEC = 7 * 24 * 3600
LOGIN_MAX_FAILURES = 5
LOGIN_FAILURE_WINDOW_SEC = 15 * 60

# scrypt cost: 16 MiB of memory and ~50 ms per hash on a small cloud instance.
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1

AUTH_SECRET = os.environ.get("AUTH_SECRET", "")
if not AUTH_SECRET:
    # Fine for local dev; in production every restart would sign everyone out.
    AUTH_SECRET = secrets.token_urlsafe(32)
    print("WARN: AUTH_SECRET is not set; using a random per-process secret (tokens die on restart).")


@dataclass(frozen=True)
class AuthUser:
    user_id: str
    user_name: str


# ------------------------------------------------------------------ passwords
def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: Optional[str]) -> bool:
    try:
        scheme, n, r, p, salt, digest = (stored or "").split("$")
        if scheme != "scrypt":
            return False
        expected = _unb64(digest)
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=_unb64(salt), n=int(n), r=int(r), p=int(p), dklen=len(expected)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


# ------------------------------------------------------------------ tokens
def issue_token(user_id: str, user_name: str) -> str:
    now = int(time.time())
    claims = {"sub": user_id, "name": user_name, "iat": now, "exp": now + TOKEN_TTL_SEC}
    return jwt.encode(claims, AUTH_SECRET, algorithm="HS256")


_bearer = HTTPBearer(auto_error=False)


def current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)) -> AuthUser:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Sign in required.", headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = jwt.decode(
            credentials.credentials, AUTH_SECRET, algorithms=["HS256"], options={"require": ["sub", "exp"]}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Session expired or invalid. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return AuthUser(user_id=str(claims["sub"]), user_name=str(claims.get("name", "")))


def require_self(user_id: str, auth: AuthUser = Depends(current_user)) -> AuthUser:
    """Guard for /users/{user_id}/... routes: a learner may only touch their own data."""
    if user_id != auth.user_id:
        raise HTTPException(status_code=403, detail="You can only access your own account.")
    return auth


def admin_usernames() -> Set[str]:
    raw = os.environ.get("ADMIN_USERNAMES", "")
    return {u.strip() for u in raw.split(",") if u.strip()}


def require_admin(auth: AuthUser = Depends(current_user)) -> AuthUser:
    if auth.user_name not in admin_usernames():
        raise HTTPException(status_code=403, detail="Admin access required")
    return auth


# ------------------------------------------------------------------ login throttling
# In-memory, like the rest of the server's session state: keyed by client IP +
# username, so one attacker cannot lock a learner out from everywhere.
_LOGIN_FAILURES: Dict[str, List[float]] = {}


def check_login_throttle(key: str) -> None:
    now = time.time()
    recent = [t for t in _LOGIN_FAILURES.get(key, []) if now - t < LOGIN_FAILURE_WINDOW_SEC]
    if recent:
        _LOGIN_FAILURES[key] = recent
    else:
        _LOGIN_FAILURES.pop(key, None)
    if len(recent) >= LOGIN_MAX_FAILURES:
        raise HTTPException(status_code=429, detail="Too many failed sign-in attempts. Try again in a few minutes.")


def record_login_failure(key: str) -> None:
    _LOGIN_FAILURES.setdefault(key, []).append(time.time())


def clear_login_failures(key: str) -> None:
    _LOGIN_FAILURES.pop(key, None)
