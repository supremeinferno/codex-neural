import sqlite3
import hashlib
import secrets
import time
import smtplib

from pathlib import Path
from email.message import EmailMessage
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta


# =========================================================
# ENVIRONMENT
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

# Loads software-eng/.env
load_dotenv(BASE_DIR.parent / ".env")

SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")


# =========================================================
# DATABASE
# =========================================================

DB_PATH = Path(os.getenv("CODEX_DATABASE_PATH", str(BASE_DIR / "users.db")))


def get_connection():
    return sqlite3.connect(DB_PATH)


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

    # Opaque, revocable sessions. Only a hash of the bearer token is stored.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL
        )
        """
    )

    # OTP table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS password_reset_otps (
            email TEXT PRIMARY KEY,
            otp TEXT NOT NULL,
            expires REAL NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    # Older databases were created without the attempts column
    otp_columns = [row[1] for row in conn.execute("PRAGMA table_info(password_reset_otps)")]
    if "attempts" not in otp_columns:
        conn.execute("ALTER TABLE password_reset_otps ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0")

    conn.commit()
    conn.close()



def create_session(user_id):
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat(timespec="seconds")
    conn = get_connection()
    conn.execute(
        "INSERT INTO auth_sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (token_hash, user_id, expires_at),
    )
    conn.commit()
    conn.close()
    return token


def get_user_for_session(token):
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    conn = get_connection()
    row = conn.execute(
        """SELECT users.id, users.email FROM auth_sessions
           JOIN users ON users.id = auth_sessions.user_id
           WHERE auth_sessions.token_hash = ? AND auth_sessions.expires_at > ?""",
        (token_hash, datetime.utcnow().isoformat(timespec="seconds")),
    ).fetchone()
    conn.close()
    return {"id": row[0], "email": row[1]} if row else None


def revoke_session(token):
    if not token:
        return
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    conn = get_connection()
    conn.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_hash,))
    conn.commit()
    conn.close()


# =========================================================
# PASSWORD
# =========================================================

# Stored format: pbkdf2_sha256$<iterations>$<salt hex>$<hash hex>
PASSWORD_HASH_ITERATIONS = 600_000

MIN_PASSWORD_LENGTH = 6


def hash_password(password, salt=None, iterations=PASSWORD_HASH_ITERATIONS):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        iterations,
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def _legacy_hash(password):
    # Accounts created before salted hashing stored a plain SHA-256 digest.
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password, stored):
    if stored.startswith("pbkdf2_sha256$"):
        _, iterations, salt, _ = stored.split("$")
        candidate = hash_password(password, salt, int(iterations))
    else:
        candidate = _legacy_hash(password)
    return secrets.compare_digest(candidate, stored)


def needs_rehash(stored):
    return not stored.startswith(f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}$")


# =========================================================
# REGISTER
# =========================================================

def register_user(email, password):

    email = email.strip().lower()

    if not email or not password:
        return False, "Email and password are required."

    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."

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

    try:
        user = conn.execute(
            """
            SELECT id, email, password
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

        if not user or not verify_password(password, user[2]):
            return None

        # Upgrade legacy SHA-256 hashes the next time the user signs in
        if needs_rehash(user[2]):
            conn.execute(
                "UPDATE users SET password = ? WHERE id = ?",
                (hash_password(password), user[0]),
            )
            conn.commit()

        return {
            "id": user[0],
            "email": user[1],
        }

    finally:
        conn.close()


# =========================================================
# OTP SETTINGS
# =========================================================

OTP_EXPIRATION_SECONDS = 5 * 60

# After this many wrong guesses the OTP is discarded and a new one must be requested
OTP_MAX_ATTEMPTS = 5


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
    if not secrets.compare_digest(otp, stored_otp):

        conn = get_connection()

        try:
            conn.execute(
                """
                UPDATE password_reset_otps
                SET attempts = attempts + 1
                WHERE email = ?
                """,
                (email,),
            )

            conn.execute(
                """
                DELETE FROM password_reset_otps
                WHERE email = ? AND attempts >= ?
                """,
                (email, OTP_MAX_ATTEMPTS),
            )

            conn.commit()

        finally:
            conn.close()

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

    if len(new_password) < MIN_PASSWORD_LENGTH:
        return (
            False,
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
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