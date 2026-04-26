"""
auth_service.py
JWT-based authentication for Intelli-Credit.
No external libraries beyond PyJWT and bcrypt.
"""

import sqlite3
import hashlib
import hmac
import os
import json
import time
import base64
import re


# Secret key — in production, load from environment variable
SECRET_KEY = os.environ.get("IC_SECRET_KEY", "intelli-credit-dev-secret-change-in-prod")
TOKEN_EXPIRY_HOURS = 24


# ─── Simple JWT (no PyJWT dependency) ────────────────────────────────────────

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * (pad % 4))


def create_token(user_id: int, username: str) -> str:
    header  = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url_encode(json.dumps({
        "sub": user_id,
        "username": username,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRY_HOURS * 3600,
    }).encode())

    sig_input = f"{header}.{payload}".encode()
    sig = hmac.new(SECRET_KEY.encode(), sig_input, hashlib.sha256).digest()
    signature = _b64url_encode(sig)

    return f"{header}.{payload}.{signature}"


def verify_token(token: str) -> dict | None:
    """Returns payload dict if valid, None if expired/invalid."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header, payload, signature = parts
        sig_input = f"{header}.{payload}".encode()
        expected_sig = hmac.new(SECRET_KEY.encode(), sig_input, hashlib.sha256).digest()
        expected_b64 = _b64url_encode(expected_sig)

        if not hmac.compare_digest(signature, expected_b64):
            return None

        data = json.loads(_b64url_decode(payload))
        if data.get("exp", 0) < time.time():
            return None

        return data

    except Exception:
        return None


# ─── Password hashing (stdlib only) ──────────────────────────────────────────

def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    if salt is None:
        salt = _b64url_encode(os.urandom(16))
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        iterations=260_000,
    )
    return _b64url_encode(key), salt


def _verify_password(password: str, stored_hash: str, salt: str) -> bool:
    computed, _ = _hash_password(password, salt)
    return hmac.compare_digest(computed, stored_hash)


# ─── DB helpers ───────────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "intelli_credit.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_tables():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    NOT NULL UNIQUE,
                email         TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,
                password_salt TEXT    NOT NULL,
                full_name     TEXT,
                role          TEXT    DEFAULT 'analyst',
                created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
                last_login    TEXT
            )
        """)
        conn.commit()


# ─── Public API ───────────────────────────────────────────────────────────────

def validate_password_strength(password: str) -> str | None:
    """Returns error message or None if password is acceptable."""
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter"
    if not re.search(r"\d", password):
        return "Password must contain at least one number"
    return None


def register_user(username: str, email: str, password: str, full_name: str = "") -> dict:
    username  = username.strip().lower()
    email     = email.strip().lower()
    full_name = full_name.strip()

    if not username or not email or not password:
        return {"success": False, "error": "Username, email and password are required"}

    if not re.match(r"^[a-z0-9_]{3,30}$", username):
        return {"success": False, "error": "Username: 3–30 chars, letters/numbers/underscore only"}

    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        return {"success": False, "error": "Invalid email address"}

    pw_error = validate_password_strength(password)
    if pw_error:
        return {"success": False, "error": pw_error}

    pw_hash, pw_salt = _hash_password(password)

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (username, email, password_hash, password_salt, full_name) "
                "VALUES (?, ?, ?, ?, ?)",
                (username, email, pw_hash, pw_salt, full_name)
            )
            conn.commit()
            user_id = conn.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()["id"]

        token = create_token(user_id, username)
        return {
            "success": True,
            "token": token,
            "user": {"id": user_id, "username": username,
                     "email": email, "full_name": full_name, "role": "analyst"},
        }

    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return {"success": False, "error": "Username already taken"}
        if "email" in str(e):
            return {"success": False, "error": "Email already registered"}
        return {"success": False, "error": "Registration failed"}


def login_user(username: str, password: str) -> dict:
    username = username.strip().lower()

    if not username or not password:
        return {"success": False, "error": "Username and password required"}

    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT id, username, email, full_name, role, password_hash, password_salt "
                "FROM users WHERE username = ? OR email = ?",
                (username, username)
            ).fetchone()

        if not row:
            return {"success": False, "error": "Invalid username or password"}

        if not _verify_password(password, row["password_hash"], row["password_salt"]):
            return {"success": False, "error": "Invalid username or password"}

        # Update last login
        with get_db() as conn:
            conn.execute(
                "UPDATE users SET last_login = datetime('now') WHERE id = ?", (row["id"],)
            )
            conn.commit()

        token = create_token(row["id"], row["username"])
        return {
            "success": True,
            "token": token,
            "user": {
                "id": row["id"], "username": row["username"],
                "email": row["email"], "full_name": row["full_name"],
                "role": row["role"],
            },
        }

    except Exception as e:
        return {"success": False, "error": f"Login error: {e}"}


def get_user_from_token(token: str) -> dict | None:
    payload = verify_token(token)
    if not payload:
        return None
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT id, username, email, full_name, role FROM users WHERE id = ?",
                (payload["sub"],)
            ).fetchone()
        return dict(row) if row else None
    except Exception:
        return None