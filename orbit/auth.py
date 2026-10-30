"""Email and password sign-in with a signed cookie. Standard library hashing."""
import hashlib
import os
import secrets
import sqlite3

from itsdangerous import BadSignature, URLSafeSerializer

SECRET = os.environ.get("ORBIT_SECRET") or secrets.token_hex(32)
_signer = URLSafeSerializer(SECRET, salt="orbit-session")
COOKIE = "orbit_session"


def token_key(token: str) -> str:
    """What Orbit stores for a host token: its SHA-256, never the token itself.

    A token is 24 random bytes, so a plain hash is enough; a copy of orbit.db cannot be used
    to impersonate a host.
    """
    return "sha256:" + hashlib.sha256(token.encode()).hexdigest()


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)


def create_user(conn: sqlite3.Connection, email: str, password: str) -> int:
    email = email.strip().lower()
    if "@" not in email:
        raise ValueError("enter a real email address")
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
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
    if row is None:
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
        return int(_signer.loads(value)["uid"])
    except (BadSignature, KeyError, ValueError, TypeError):
        return None
