import sqlite3
import hashlib
import secrets
import time
import smtplib
import json

from pathlib import Path
from email.message import EmailMessage
from dotenv import load_dotenv
import os

from fastapi import Depends, HTTPException, Request

from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerifyMismatchError,
    VerificationError,
)


# =========================================================
# ENVIRONMENT
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

# Loads software-eng/.env
load_dotenv(BASE_DIR.parent / ".env")

SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")

SESSION_COOKIE_NAME = "codex_session"
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "604800"))
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"

LOGIN_ATTEMPT_WINDOW_SECONDS = int(os.getenv("LOGIN_ATTEMPT_WINDOW_SECONDS", "900"))
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))

ADMIN_EMAILS = {
    email.strip().lower()
    for email in (
        os.getenv(
            "ADMIN_EMAILS",
            os.getenv("ADMIN_EMAIL", "codexproject9@gmail.com"),
        )
        .split(",")
    )
    if email.strip()
}

password_hasher = PasswordHasher()
FAILED_LOGIN_ATTEMPTS = {}


# =========================================================
# DATABASE
# =========================================================

DB_PATH = BASE_DIR / "users.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()

    # Users table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """
    )

    # OTP table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS password_reset_otps (
            email TEXT PRIMARY KEY,
            otp TEXT NOT NULL,
            expires REAL NOT NULL
        )
        """
    )

    # Session table for server-side session persistence
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL,
            last_seen REAL NOT NULL
        )
        """
    )

    # Security event log for tracking incidents and audit actions
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            user_id INTEGER,
            email TEXT,
            ip_address TEXT,
            path TEXT,
            details TEXT,
            occurred_at REAL NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


# =========================================================
# PASSWORD
# =========================================================

def hash_password(password):
    return password_hasher.hash(password)


def verify_password(password, stored_hash):
    if not stored_hash:
        return False

    if stored_hash.startswith("$argon2"):
        try:
            password_hasher.verify(stored_hash, password)
            return True
        except (
            VerifyMismatchError,
            InvalidHashError,
            VerificationError,
        ):
            return False

    legacy_hash = hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()

    return secrets.compare_digest(legacy_hash, stored_hash)


# =========================================================
# REGISTER
# =========================================================

def register_user(email, password):

    email = email.strip().lower()

    if not email or not password:
        return False, "Email and password are required."

    conn = get_connection()

    try:
        conn.execute(
            """
            INSERT INTO users (email, password)
            VALUES (?, ?)
            """,
            (
                email,
                hash_password(password),
            ),
        )

        conn.commit()

        return True, "Account created successfully."

    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."

    finally:
        conn.close()


# =========================================================
# LOGIN
# =========================================================

def authenticate_user(email, password):

    email = email.strip().lower()

    conn = get_connection()

    user = conn.execute(
        """
        SELECT id, email, password
        FROM users
        WHERE email = ?
        """,
        (email,),
    ).fetchone()

    conn.close()

    if not user:
        return None

    stored_hash = user["password"]

    if not verify_password(password, stored_hash):
        return None

    if not stored_hash.startswith("$argon2"):
        conn = get_connection()

        try:
            conn.execute(
                """
                UPDATE users
                SET password = ?
                WHERE id = ?
                """,
                (
                    hash_password(password),
                    user["id"],
                ),
            )
            conn.commit()
        finally:
            conn.close()

    return {
        "id": user["id"],
        "email": user["email"],
    }


# =========================================================
# SESSION MANAGEMENT
# =========================================================

def create_session(user_id, email):
    session_id = secrets.token_urlsafe(32)
    now = time.time()
    expires_at = now + SESSION_TTL_SECONDS

    conn = get_connection()

    try:
        conn.execute(
            """
            INSERT INTO sessions (
                session_id,
                user_id,
                email,
                created_at,
                expires_at,
                last_seen
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                user_id,
                email,
                now,
                expires_at,
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return session_id, expires_at


def invalidate_session(session_id):
    if not session_id:
        return

    conn = get_connection()

    try:
        conn.execute(
            """
            DELETE FROM sessions
            WHERE session_id = ?
            """,
            (session_id,),
        )
        conn.commit()
    finally:
        conn.close()


def get_session(session_id):
    if not session_id:
        return None

    conn = get_connection()

    row = conn.execute(
        """
        SELECT user_id, email, expires_at
        FROM sessions
        WHERE session_id = ?
        """,
        (session_id,),
    ).fetchone()

    conn.close()

    if not row:
        return None

    user_id = row["user_id"]
    email = row["email"]
    expires_at = row["expires_at"]

    if expires_at < time.time():
        invalidate_session(session_id)
        return None

    return {
        "id": user_id,
        "email": email,
    }


def verify_session(request: Request):

    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    session = get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    return session


def is_admin_session(session):

    if not session:
        return False

    return session.get("email", "").strip().lower() in ADMIN_EMAILS


def verify_admin(session: dict = Depends(verify_session)):

    if not is_admin_session(session):
        raise HTTPException(
            status_code=403,
            detail="Administrator access required.",
        )

    return session


# =========================================================
# RATE LIMITING
# =========================================================

def get_login_attempt_key(ip_address, email):
    return f"{ip_address or 'unknown'}:{(email or '').strip().lower()}"


def is_login_attempt_allowed(ip_address, email):
    key = get_login_attempt_key(ip_address, email)
    now = time.time()

    attempts = FAILED_LOGIN_ATTEMPTS.get(key, [])
    attempts = [
        attempt_time
        for attempt_time in attempts
        if now - attempt_time < LOGIN_ATTEMPT_WINDOW_SECONDS
    ]

    if len(attempts) >= MAX_LOGIN_ATTEMPTS:
        FAILED_LOGIN_ATTEMPTS[key] = attempts
        return False

    return True


def record_failed_login(ip_address, email):
    key = get_login_attempt_key(ip_address, email)
    now = time.time()

    attempts = FAILED_LOGIN_ATTEMPTS.get(key, [])
    attempts = [
        attempt_time
        for attempt_time in attempts
        if now - attempt_time < LOGIN_ATTEMPT_WINDOW_SECONDS
    ]

    attempts.append(now)
    FAILED_LOGIN_ATTEMPTS[key] = attempts


def clear_login_attempts(ip_address, email):
    key = get_login_attempt_key(ip_address, email)
    FAILED_LOGIN_ATTEMPTS.pop(key, None)


# =========================================================
# EVENT TRACKING
# =========================================================

def record_event(
    event_type,
    path=None,
    details=None,
    user_id=None,
    email=None,
    ip_address=None,
):

    conn = get_connection()

    try:
        conn.execute(
            """
            INSERT INTO events (
                event_type,
                user_id,
                email,
                ip_address,
                path,
                details,
                occurred_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                user_id,
                email,
                ip_address,
                path,
                json.dumps(details, default=str)
                if details is not None
                else None,
                time.time(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_events(limit=100):

    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT
                id,
                event_type,
                user_id,
                email,
                ip_address,
                path,
                details,
                occurred_at
            FROM events
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]


# =========================================================
# OTP SETTINGS
# =========================================================

OTP_EXPIRATION_SECONDS = 5 * 60


# =========================================================
# CHECK USER
# =========================================================

def user_exists(email):

    email = email.strip().lower()

    conn = get_connection()

    user = conn.execute(
        """
        SELECT id
        FROM users
        WHERE email = ?
        """,
        (email,),
    ).fetchone()

    conn.close()

    return user is not None


# =========================================================
# GENERATE OTP
# =========================================================

def generate_otp():

    return str(
        secrets.randbelow(900000) + 100000
    )


# =========================================================
# SEND OTP EMAIL
# =========================================================

def send_otp_email(email, otp):

    if not SMTP_EMAIL or not SMTP_APP_PASSWORD:
        raise RuntimeError(
            "SMTP_EMAIL or SMTP_APP_PASSWORD is missing from .env"
        )

    message = EmailMessage()

    message["Subject"] = "CODEX Password Reset OTP"
    message["From"] = SMTP_EMAIL
    message["To"] = email

    message.set_content(
        f"""
Hello,

You requested to reset your CODEX Research password.

Your verification OTP is:

{otp}

This OTP is valid for 5 minutes.

If you did not request a password reset,
you can safely ignore this email.

Regards,
CODEX Research
        """.strip()
    )

    with smtplib.SMTP(
        "smtp.gmail.com",
        587,
        timeout=30,
    ) as server:

        server.starttls()

        server.login(
            SMTP_EMAIL,
            SMTP_APP_PASSWORD,
        )

        server.send_message(message)


# =========================================================
# REQUEST PASSWORD RESET
# =========================================================

def request_password_reset(email):

    email = email.strip().lower()

    if not email:
        return False, "Email is required."

    # Check account
    if not user_exists(email):
        return False, "No account exists with this email."

    # Generate OTP
    otp = generate_otp()

    # OTP expires after 5 minutes
    expiration = (
        time.time()
        + OTP_EXPIRATION_SECONDS
    )

    conn = get_connection()

    try:

        # Remove previous OTP
        conn.execute(
            """
            DELETE FROM password_reset_otps
            WHERE email = ?
            """,
            (email,),
        )

        # Store new OTP
        conn.execute(
            """
            INSERT INTO password_reset_otps
            (email, otp, expires)
            VALUES (?, ?, ?)
            """,
            (
                email,
                otp,
                expiration,
            ),
        )

        conn.commit()

    finally:
        conn.close()

    # Send OTP
    try:

        send_otp_email(
            email,
            otp,
        )

        return True, "OTP sent successfully."

    except Exception as error:

        print("OTP email error:", error)

        # Remove OTP if email failed
        conn = get_connection()

        try:
            conn.execute(
                """
                DELETE FROM password_reset_otps
                WHERE email = ?
                """,
                (email,),
            )

            conn.commit()

        finally:
            conn.close()

        return (
            False,
            "Unable to send OTP. Please try again."
        )


# =========================================================
# VERIFY OTP
# =========================================================

def verify_otp(email, otp):

    email = email.strip().lower()
    otp = str(otp).strip()

    conn = get_connection()

    try:

        stored_data = conn.execute(
            """
            SELECT otp, expires
            FROM password_reset_otps
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

    finally:
        conn.close()

    # OTP does not exist
    if not stored_data:
        return False, "No OTP request found."

    stored_otp = stored_data[0]
    expires = stored_data[1]

    # Check expiration
    if time.time() > expires:

        conn = get_connection()

        try:
            conn.execute(
                """
                DELETE FROM password_reset_otps
                WHERE email = ?
                """,
                (email,),
            )

            conn.commit()

        finally:
            conn.close()

        return False, "OTP has expired."

    # Check OTP
    if otp != stored_otp:
        return False, "Invalid OTP."

    return True, "OTP verified successfully."


# =========================================================
# RESET PASSWORD
# =========================================================

def reset_password(
    email,
    otp,
    new_password,
):

    email = email.strip().lower()
    otp = str(otp).strip()

    # Validate password
    if not new_password:
        return False, "New password is required."

    if len(new_password) < 6:
        return (
            False,
            "Password must be at least 6 characters."
        )

    # Verify OTP
    verified, message = verify_otp(
        email,
        otp,
    )

    if not verified:
        return False, message

    conn = get_connection()

    try:

        result = conn.execute(
            """
            UPDATE users
            SET password = ?
            WHERE email = ?
            """,
            (
                hash_password(new_password),
                email,
            ),
        )

        # User doesn't exist
        if result.rowcount == 0:
            conn.rollback()

            return (
                False,
                "User account not found."
            )

        # Delete OTP after successful reset
        conn.execute(
            """
            DELETE FROM password_reset_otps
            WHERE email = ?
            """,
            (email,),
        )

        conn.commit()

        return True, "Password reset successfully."

    finally:
        conn.close()


# =========================================================
# INITIALIZE DATABASE
# =========================================================

init_db()