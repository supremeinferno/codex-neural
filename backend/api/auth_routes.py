from __future__ import annotations

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from backend.repositories.sqlite_repository import record_login_activity
from backend.auth import (
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_SECURE,
    SESSION_TTL_SECONDS,
    authenticate_user,
    clear_login_attempts,
    create_session,
    get_session,
    invalidate_session,
    is_login_attempt_allowed,
    record_event,
    record_failed_login,
    register_user,
    request_password_reset,
    reset_password,
    verify_otp,
)

router = APIRouter()


def sync_excel_safely():
    try:
        from backend.auth import sync_excel

        sync_excel()
    except ImportError:
        pass
    except Exception as error:
        print("Excel synchronization warning:", error)


class AuthRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class VerifyOTPRequest(BaseModel):
    email: str
    otp: str


class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    new_password: str


@router.get("/api")
def home():
    return {"message": "Nexus Research API is running"}


@router.post("/api/register")
def register(request: AuthRequest):
    success, message = register_user(request.email, request.password, role="user")
    if success:
        sync_excel_safely()
    return {"success": success, "message": message}


@router.post("/api/login")
def login(request: AuthRequest, request_obj: Request, response: Response):
    client_ip = request_obj.client.host if request_obj.client else "unknown"

    if not is_login_attempt_allowed(client_ip, request.email):
        return {
            "success": False,
            "message": "Too many failed login attempts. Please try again later.",
        }

    user = authenticate_user(request.email, request.password)
    if not user:
        record_failed_login(client_ip, request.email)
        record_event(
            event_type="login_failed",
            path="/api/login",
            details={"email": request.email.strip().lower(), "ip_address": client_ip},
            email=request.email.strip().lower(),
            ip_address=client_ip,
        )
        return {"success": False, "message": "Invalid email or password."}

    clear_login_attempts(client_ip, request.email)
    record_login_activity(user["id"], user["email"])
    sync_excel_safely()
    record_event(
        event_type="login_success",
        path="/api/login",
        details={"email": request.email.strip().lower(), "ip_address": client_ip},
        user_id=user["id"],
        email=user["email"],
        ip_address=client_ip,
    )

    session_id, expires_at = create_session(user["id"], user["email"])
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
        max_age=SESSION_TTL_SECONDS,
        path="/",
    )

    return {
        "success": True,
        "message": "Login successful",
        "user": user,
        "session_expires_at": expires_at,
    }


@router.get("/api/session")
def session_endpoint(request: Request):
    session = get_session(request.cookies.get(SESSION_COOKIE_NAME))
    if not session:
        return {"authenticated": False, "user": None}

    return {
        "authenticated": True,
        "user": {"id": session["id"], "email": session["email"]},
    }


@router.post("/api/logout")
def logout(request: Request, response: Response):
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    session = get_session(session_id)
    invalidate_session(session_id)
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    record_event(
        event_type="logout",
        path="/api/logout",
        details={"session_invalidated": bool(session)},
        user_id=session["id"] if session else None,
        email=session["email"] if session else None,
        ip_address=request.client.host if request.client else None,
    )
    return {"success": True, "message": "Logged out successfully."}


@router.post("/api/forgot-password")
def forgot_password(request: ForgotPasswordRequest, request_obj: Request):
    success, message = request_password_reset(request.email)
    record_event(
        event_type="password_reset_requested",
        path="/api/forgot-password",
        details={"requested_email": request.email.strip().lower(), "success": success, "message": message},
        email=request.email.strip().lower(),
        ip_address=request_obj.client.host if request_obj.client else None,
    )
    return {"success": success, "message": message}


@router.post("/api/verify-otp")
def verify_otp_endpoint(request: VerifyOTPRequest, request_obj: Request):
    success, message = verify_otp(request.email, request.otp)
    record_event(
        event_type="otp_verified",
        path="/api/verify-otp",
        details={"requested_email": request.email.strip().lower(), "success": success, "message": message},
        email=request.email.strip().lower(),
        ip_address=request_obj.client.host if request_obj.client else None,
    )
    return {"success": success, "message": message}


@router.post("/api/reset-password")
def reset_password_endpoint(request: ResetPasswordRequest, request_obj: Request):
    success, message = reset_password(request.email, request.otp, request.new_password)
    record_event(
        event_type="password_reset_completed",
        path="/api/reset-password",
        details={"requested_email": request.email.strip().lower(), "success": success, "message": message},
        email=request.email.strip().lower(),
        ip_address=request_obj.client.host if request_obj.client else None,
    )
    return {"success": success, "message": message}
