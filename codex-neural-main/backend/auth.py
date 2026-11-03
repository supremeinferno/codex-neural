import sqlite3
import hashlib
import secrets
import time
import smtplib

from pathlib import Path
from email.message import EmailMessage
from dotenv import load_dotenv
import os


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

DB_PATH = BASE_DIR / "users.db"


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

    conn.commit()
    conn.close()


# =========================================================
# PASSWORD
# =========================================================

def hash_password(password):
    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


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
        SELECT id, email
        FROM users
        WHERE email = ?
        AND password = ?
        """,
        (
            email,
            hash_password(password),
        ),
    ).fetchone()

    conn.close()

    if user:
        return {
            "id": user[0],
            "email": user[1],
        }

    return None


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