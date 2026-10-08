import hashlib
import secrets
import smtplib
import sqlite3
import time
from email.message import EmailMessage

from fastapi import Depends, HTTPException, Request
from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

from backend.config import settings
from backend.repositories import sqlite_repository
from backend.security import is_password_strong_enough, is_session_active, normalize_email

SMTP_EMAIL = settings.smtp_email
SMTP_APP_PASSWORD = settings.smtp_app_password

SESSION_COOKIE_NAME = "codex_session"
SESSION_TTL_SECONDS = settings.session_ttl_seconds
SESSION_COOKIE_SECURE = settings.session_cookie_secure

LOGIN_ATTEMPT_WINDOW_SECONDS = settings.login_attempt_window_seconds
MAX_LOGIN_ATTEMPTS = settings.max_login_attempts

DEFAULT_ROLE = "user"
ADMIN_ROLE = "admin"
ADMIN_EMAILS = {
    email.strip().lower()
    for email in (
        settings.admin_email.split(",")
    )
    if email.strip()
}

ROLE_PERMISSIONS = {
    DEFAULT_ROLE: {"research", "document_chat", "document_upload"},
    ADMIN_ROLE: {"*"},
}

password_hasher = PasswordHasher()
FAILED_LOGIN_ATTEMPTS = {}
OTP_EXPIRATION_SECONDS = 5 * 60


def init_db():
    sqlite_repository.initialize_admin_database()


# PASSWORD HELPERS

def hash_password(password):
    return password_hasher.hash(password)


def verify_password(password, stored_hash):
    if not stored_hash:
        return False

    if stored_hash.startswith("$argon2"):
        try:
            password_hasher.verify(stored_hash, password)
            return True
        except (VerifyMismatchError, InvalidHashError, VerificationError):
            return False

    legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return secrets.compare_digest(legacy_hash, stored_hash)


def normalize_role(role):
    if not role:
        return DEFAULT_ROLE

    normalized = role.strip().lower()
    if normalized not in {DEFAULT_ROLE, ADMIN_ROLE}:
        return None

    return normalized


def register_user(email, password, role=None):
    email = normalize_email(email)

    if not email or not password:
        return False, "Email and password are required."

    if not is_password_strong_enough(password):
        return False, "Password must be at least 8 characters, include upper and lower case, a number, and a symbol."

    normalized_role = normalize_role(role)
    if normalized_role is None:
        return False, "Invalid role. Supported roles are 'user' and 'admin'."

    try:
        sqlite_repository.create_user(
            email=email,
            password_hash=hash_password(password),
            role=normalized_role,
            created_at=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        )
        return True, "Account created successfully."
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."


def authenticate_user(email, password):
    email = normalize_email(email)
    user = sqlite_repository.get_user_by_email(email)

    if not user:
        return None

    stored_hash = user["password"]
    if not verify_password(password, stored_hash):
        return None

    if not stored_hash.startswith("$argon2"):
        sqlite_repository.update_user_password(user["id"], hash_password(password))

    return {"id": user["id"], "email": user["email"], "role": user["role"] or DEFAULT_ROLE}


def create_session(user_id, email):
    session_id = secrets.token_urlsafe(32)
    now = time.time()
    expires_at = now + SESSION_TTL_SECONDS
    sqlite_repository.create_session_record(session_id, user_id, email, now, expires_at)
    return session_id, expires_at


def invalidate_session(session_id):
    if not session_id:
        return
    sqlite_repository.delete_session_record(session_id)


def get_session(session_id):
    if not session_id:
        return None

    row = sqlite_repository.get_session_record(session_id)

    if not row:
        return None

    user_id = row["user_id"]
    email = row["email"]
    expires_at = row["expires_at"]

    if not is_session_active(expires_at):
        invalidate_session(session_id)
        return None

    return {"id": user_id, "email": email}


def get_user_role(user_id):
    stored_role = sqlite_repository.get_user_role_record(user_id)

    if not stored_role:
        return DEFAULT_ROLE

    return stored_role.strip().lower() if stored_role else DEFAULT_ROLE


def get_user_permissions(user_id):
    role = get_user_role(user_id)
    if role in ROLE_PERMISSIONS:
        return set(ROLE_PERMISSIONS[role])
    return set()


def verify_session(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required.")

    session["role"] = get_user_role(session["id"])
    session["permissions"] = get_user_permissions(session["id"])
    return session


def require_permissions(*required_permissions):
    required = {
        permission.strip().lower()
        for permission in required_permissions
        if permission and permission.strip()
    }

    def dependency(session: dict = Depends(verify_session)):
        if not required:
            return session
        if session.get("permissions") is None:
            session["permissions"] = get_user_permissions(session["id"])
        if "*" in session["permissions"]:
            return session
        missing = [permission for permission in required if permission not in session["permissions"]]
        if missing:
            raise HTTPException(status_code=403, detail="Insufficient permissions.")
        return session

    return dependency


def require_roles(*allowed_roles):
    allowed = {role.strip().lower() for role in allowed_roles if role.strip()}

    def dependency(session: dict = Depends(verify_session)):
        if not allowed:
            return session

        current_role = (session.get("role") or DEFAULT_ROLE).strip().lower()
        if current_role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient permissions.")
        return session

    return dependency


def verify_admin(session: dict = Depends(require_roles(ADMIN_ROLE))):
    return session


def get_login_attempt_key(ip_address, email):
    return f"{ip_address or 'unknown'}:{(email or '').strip().lower()}"


def is_login_attempt_allowed(ip_address, email):
    key = get_login_attempt_key(ip_address, email)
    now = time.time()
    attempts = FAILED_LOGIN_ATTEMPTS.get(key, [])
    attempts = [
        attempt_time for attempt_time in attempts if now - attempt_time < LOGIN_ATTEMPT_WINDOW_SECONDS
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
        attempt_time for attempt_time in attempts if now - attempt_time < LOGIN_ATTEMPT_WINDOW_SECONDS
    ]
    attempts.append(now)
    FAILED_LOGIN_ATTEMPTS[key] = attempts


def clear_login_attempts(ip_address, email):
    FAILED_LOGIN_ATTEMPTS.pop(get_login_attempt_key(ip_address, email), None)


def record_event(event_type, path=None, details=None, user_id=None, email=None, ip_address=None):
    sqlite_repository.insert_event(
        event_type=event_type,
        path=path,
        details=details,
        user_id=user_id,
        email=email,
        ip_address=ip_address,
        occurred_at=time.time(),
    )


def get_recent_events(limit=100):
    return sqlite_repository.get_recent_events(limit)


def user_exists(email):
    email = normalize_email(email)
    return sqlite_repository.user_exists(email)


def generate_otp():
    return str(secrets.randbelow(900000) + 100000)


def send_otp_email(email, otp):
    if not SMTP_EMAIL or not SMTP_APP_PASSWORD:
        raise RuntimeError("SMTP_EMAIL or SMTP_APP_PASSWORD is missing from .env")

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

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
        server.send_message(message)


def request_password_reset(email):
    email = normalize_email(email)

    if not email:
        return False, "Email is required."

    if not user_exists(email):
        return False, "No account exists with this email."

    otp = generate_otp()
    expiration = time.time() + OTP_EXPIRATION_SECONDS

    sqlite_repository.store_password_reset_otp(email, otp, expiration)

    try:
        send_otp_email(email, otp)
        return True, "OTP sent successfully."
    except Exception as error:
        print("OTP email error:", error)
        sqlite_repository.delete_password_reset_otp(email)
        return False, "Unable to send OTP. Please try again."


def verify_otp(email, otp):
    email = normalize_email(email)
    otp = str(otp).strip()
    stored_data = sqlite_repository.get_password_reset_otp(email)

    if not stored_data:
        return False, "No OTP request found."

    stored_otp = stored_data["otp"]
    expires = stored_data["expires"]

    if time.time() > expires:
        sqlite_repository.delete_password_reset_otp(email)
        return False, "OTP has expired."

    if otp != stored_otp:
        return False, "Invalid OTP."

    return True, "OTP verified successfully."


def reset_password(email, otp, new_password):
    email = normalize_email(email)
    otp = str(otp).strip()

    if not new_password:
        return False, "New password is required."

    if len(new_password) < 6:
        return False, "Password must be at least 6 characters."

    verified, message = verify_otp(email, otp)
    if not verified:
        return False, message

    updated = sqlite_repository.update_user_password_by_email(
        email,
        hash_password(new_password),
    )
    if updated == 0:
        return False, "User account not found."
    return True, "Password reset successfully."
