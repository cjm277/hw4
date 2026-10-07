"""Accounts and sessions for Campus Customs: sign-up, log-in, log-out, and "who am I".

Passwords
- New accounts are hashed with Argon2id (argon2-cffi: random 16-byte salt, 64 MiB memory,
  3 passes). It is memory-hard, so GPU/ASIC guessing is expensive.
- Seed accounts use the professor's format `pbkdf2_sha256$<salt>$<hex digest>`
  (PBKDF2-HMAC-SHA256, 120,000 iterations, salt used as UTF-8 text). We verify those as-is.
- Plain-text passwords are never stored, logged, or returned.

Sessions
- On login/sign-up we create a random 256-bit token and send it in an HttpOnly cookie.
  Only the token's SHA-256 is stored (sessions table), so a DB leak can't hijack sessions.
"""

import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from collections import defaultdict, deque
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "campus_customs.db"

SESSION_COOKIE = "cc_session"
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
COOKIE_SECURE = False  # localhost is plain HTTP; set True when served over HTTPS.

MIN_PASSWORD, MAX_PASSWORD = 6, 128
MAX_NAME, MAX_EMAIL = 50, 254
LEGACY_PBKDF2_ITERATIONS = 120_000

MAX_FAILED_LOGINS = 5
LOCKOUT_WINDOW_SECONDS = 15 * 60

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LOGIN_FAILED = "Incorrect email or password."

hasher = PasswordHasher()
# Verified against when the email doesn't exist, so response time doesn't reveal who has an account.
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(16))

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------- Database ----------

@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )


# ---------- Passwords ----------

def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, stored: str) -> bool:
    if stored.startswith("$argon2"):
        try:
            return hasher.verify(stored, password)
        except (VerificationError, InvalidHashError):
            return False
    if stored.startswith("pbkdf2_sha256$"):
        parts = stored.split("$")
        if len(parts) != 3:
            return False
        _, salt, digest = parts
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), LEGACY_PBKDF2_ITERATIONS
        ).hex()
        return hmac.compare_digest(candidate, digest)
    return False


# ---------- Brute-force throttle (per client IP + email, in memory) ----------

_failed_logins: dict[str, deque[float]] = defaultdict(deque)


def _recent_failures(key: str) -> deque[float]:
    attempts = _failed_logins[key]
    cutoff = time.monotonic() - LOCKOUT_WINDOW_SECONDS
    while attempts and attempts[0] < cutoff:
        attempts.popleft()
    return attempts


# ---------- Sessions ----------

def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _start_session(conn: sqlite3.Connection, response: Response, user_id: int) -> None:
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (_token_hash(token), user_id, now + SESSION_TTL_SECONDS),
    )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/",
    )


def user_out(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "first_name": row["first_name"] or row["name"].split(" ")[0],
        "last_name": row["last_name"] or "",
        "email": row["email"],
        "member_since": row["created_at"],
    }


def current_user(request: Request) -> dict | None:
    """The logged-in user for this request, or None. Reused by the chat endpoints later."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    with db() as conn:
        row = conn.execute(
            """
            SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > ?
            """,
            (_token_hash(token), int(time.time())),
        ).fetchone()
    return user_out(row) if row else None


# ---------- Endpoints ----------

class SignupIn(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    confirm_password: str


class LoginIn(BaseModel):
    email: str
    password: str


def _clean_email(email: str) -> str:
    return email.strip().lower()


@router.post("/signup", status_code=201)
def signup(body: SignupIn, response: Response) -> dict:
    first, last, email = body.first_name.strip(), body.last_name.strip(), _clean_email(body.email)
    if not first or not last:
        raise HTTPException(400, "Please enter your first and last name.")
    if len(first) > MAX_NAME or len(last) > MAX_NAME:
        raise HTTPException(400, f"Names can be at most {MAX_NAME} characters.")
    if len(email) > MAX_EMAIL or not EMAIL_RE.match(email):
        raise HTTPException(400, "Please enter a valid email address.")
    if not MIN_PASSWORD <= len(body.password) <= MAX_PASSWORD:
        raise HTTPException(400, f"Password must be {MIN_PASSWORD}–{MAX_PASSWORD} characters.")
    if body.password != body.confirm_password:
        raise HTTPException(400, "Passwords don't match.")

    with db() as conn:
        if conn.execute("SELECT 1 FROM users WHERE lower(email) = ?", (email,)).fetchone():
            raise HTTPException(409, "An account with that email already exists. Try logging in.")
        try:
            cur = conn.execute(
                """
                INSERT INTO users (name, email, password_hash, first_name, last_name)
                VALUES (?, ?, ?, ?, ?)
                """,
                (f"{first} {last}", email, hash_password(body.password), first, last),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(409, "An account with that email already exists. Try logging in.")
        user_id = cur.lastrowid
        _start_session(conn, response, user_id)
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return user_out(row)


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response) -> dict:
    email = _clean_email(body.email)
    throttle_key = f"{request.client.host if request.client else '?'}|{email}"
    failures = _recent_failures(throttle_key)
    if len(failures) >= MAX_FAILED_LOGINS:
        raise HTTPException(429, "Too many failed attempts. Please wait 15 minutes and try again.")

    password = body.password[:MAX_PASSWORD]
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email) = ?", (email,)).fetchone()
        ok = verify_password(password, row["password_hash"] if row else DUMMY_HASH) and row is not None
        if not ok:
            failures.append(time.monotonic())
            raise HTTPException(401, LOGIN_FAILED)
        _failed_logins.pop(throttle_key, None)
        _start_session(conn, response, row["id"])
    return user_out(row)


@router.post("/logout")
def logout(request: Request, response: Response) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        with db() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(request: Request) -> dict:
    user = current_user(request)
    if user is None:
        raise HTTPException(401, "Not logged in.")
    return user
