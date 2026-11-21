"""Email and password sign-in with a signed cookie. Standard library hashing."""
import hashlib
import os
import re
import secrets
import sqlite3

from itsdangerous import BadSignature, URLSafeTimedSerializer

SECRET = os.environ.get("ORBIT_SECRET") or secrets.token_hex(32)
_signer = URLSafeTimedSerializer(SECRET, salt="orbit-session")
COOKIE = "orbit_session"
COOKIE_MAX_AGE = 30 * 24 * 3600  # a sign-in lasts thirty days, then the cookie is refused
EMAIL_MAX, PASSWORD_MAX = 254, 200
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_NO_USER_SALT = secrets.token_bytes(16)  # hashed against when the email is unknown, so both answers take as long


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)


def create_user(conn: sqlite3.Connection, email: str, password: str) -> int:
    email = email.strip().lower()
    if len(email) > EMAIL_MAX or not _EMAIL.match(email):
        raise ValueError("enter a real email address")
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    if len(password) > PASSWORD_MAX:
        raise ValueError(f"password must be at most {PASSWORD_MAX} characters")
    salt = secrets.token_bytes(16)
    cur = conn.execute(
        "INSERT INTO users (email, pw_hash, pw_salt) VALUES (?, ?, ?)",
        (email, _hash(password, salt), salt),
    )
    return int(cur.lastrowid)


def check_login(conn: sqlite3.Connection, email: str, password: str) -> int | None:
    row = conn.execute(
        "SELECT id, pw_hash, pw_salt FROM users WHERE email = ?", (email.strip().lower(),)
    ).fetchone()
    if len(password) > PASSWORD_MAX:
        return None
    if row is None:
        _hash(password, _NO_USER_SALT)  # same work as a real check: the reply time does not say whether the email exists
        return None
    if secrets.compare_digest(_hash(password, row["pw_salt"]), row["pw_hash"]):
        return int(row["id"])
    return None


def make_cookie(user_id: int) -> str:
    return _signer.dumps({"uid": user_id})


def read_cookie(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(_signer.loads(value, max_age=COOKIE_MAX_AGE)["uid"])
    except (BadSignature, KeyError, ValueError, TypeError):
        return None
