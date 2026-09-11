from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import os
import sqlite3
import time
from pathlib import Path
from datetime import datetime


# =========================================================
# BACKEND MODULES
# =========================================================

from backend.pipeline import run_research_pipeline

from backend.auth import (
    register_user,
    authenticate_user,
    request_password_reset,
    verify_otp,
    reset_password,
    create_session,
    get_session,
    invalidate_session,
    is_login_attempt_allowed,
    record_failed_login,
    clear_login_attempts,
    record_event,
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_SECURE,
    SESSION_TTL_SECONDS,
)

from backend.individual import (
    build_individual_index,
    answer_individual_question,
)


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "users.db"
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173"
    ).split(",")
    if origin.strip()
]
RATE_LIMIT_WINDOW_SECONDS = int(
    os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")
)
RATE_LIMIT_MAX_REQUESTS = int(
    os.getenv("RATE_LIMIT_MAX_REQUESTS", "120")
)
RATE_LIMIT_EXCLUDED_PATHS = {
    "/api",
    "/api/health",
    "/api/session",
}
REQUEST_BUCKETS = {}
RATE_LIMIT_WARMUP_BUCKETS = {}


# =========================================================
# ADMIN
# =========================================================

ADMIN_EMAIL = "codexproject9@gmail.com"


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="Nexus Research API",
    description="Multi-Agent AI Research System",
    version="1.0.0",
)


# =========================================================
# RATE LIMITING
# =========================================================

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):

    path = request.url.path

    if path in RATE_LIMIT_EXCLUDED_PATHS:
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    bucket = REQUEST_BUCKETS.setdefault(client_ip, [])

    bucket[:] = [
        timestamp
        for timestamp in bucket
        if now - timestamp < RATE_LIMIT_WINDOW_SECONDS
    ]

    if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
        record_event(
            event_type="rate_limit_hit",
            path=path,
            details={
                "ip_address": client_ip,
                "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
                "max_requests": RATE_LIMIT_MAX_REQUESTS,
            },
            ip_address=client_ip,
        )

        return JSONResponse(
            status_code=429,
            content={
                "success": False,
                "message": "Too many requests. Please try again later.",
            },
            headers={
                "Retry-After": str(RATE_LIMIT_WINDOW_SECONDS),
            },
        )

    bucket.append(now)

    return await call_next(request)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def initialize_admin_database():
    """
    Repairs the existing database without deleting existing users.
    """

    conn = get_db()
    cursor = conn.cursor()

    # -----------------------------------------------------
    # Check users table
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name='users'
        """
    )

    users_exists = cursor.fetchone()

    if users_exists:

        cursor.execute("PRAGMA table_info(users)")
        columns = [row["name"] for row in cursor.fetchall()]

        # Add created_at if old database doesn't have it
        if "created_at" not in columns:

            cursor.execute(
                """
                ALTER TABLE users
                ADD COLUMN created_at TEXT
                """
            )

            cursor.execute(
                """
                UPDATE users
                SET created_at = ?
                WHERE created_at IS NULL
                OR created_at = ''
                """,
                (datetime.now().isoformat(sep=" ", timespec="seconds"),),
            )

    # -----------------------------------------------------
    # Login activity table
    # -----------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS login_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            email TEXT NOT NULL,
            login_time TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


# Initialize database when backend starts
initialize_admin_database()


# =========================================================
# DATABASE HELPERS
# =========================================================

def sync_excel_safely():
    """
    Synchronize Excel if sync_excel exists in auth.py.
    The API will continue working even if Excel sync fails.
    """

    try:
        from backend.auth import sync_excel

        sync_excel()

    except ImportError:
        # sync_excel is not available in auth.py
        pass

    except Exception as e:
        print("Excel synchronization warning:", e)


# =========================================================
# REQUEST MODELS
# =========================================================

class ResearchRequest(BaseModel):
    topic: str


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


class IndividualQuestionRequest(BaseModel):
    question: str
    document_id: str


# =========================================================
# GENERAL API
# =========================================================

@app.get("/api")
def home():

    return {
        "message": "Nexus Research API is running"
    }


# =========================================================
# REGISTER
# =========================================================

@app.post("/api/register")
def register(request: AuthRequest):

    success, message = register_user(
        request.email,
        request.password
    )

    if success:

        # Update created_at for newly created user
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users
            SET created_at = ?
            WHERE email = ?
            AND (created_at IS NULL OR created_at = '')
            """,
            (
                datetime.now().isoformat(
                    sep=" ",
                    timespec="seconds"
                ),
                request.email.strip().lower(),
            ),
        )

        conn.commit()
        conn.close()

        sync_excel_safely()

    return {
        "success": success,
        "message": message
    }


# =========================================================
# LOGIN
# =========================================================

@app.post("/api/login")
def login(
    request: AuthRequest,
    request_obj: Request,
    response: Response,
):

    client_ip = (
        request_obj.client.host
        if request_obj.client
        else "unknown"
    )

    if not is_login_attempt_allowed(client_ip, request.email):

        return {
            "success": False,
            "message": "Too many failed login attempts. Please try again later."
        }

    user = authenticate_user(
        request.email,
        request.password
    )

    if not user:

        record_failed_login(client_ip, request.email)

        record_event(
            event_type="login_failed",
            path="/api/login",
            details={
                "email": request.email.strip().lower(),
                "ip_address": client_ip,
            },
            email=request.email.strip().lower(),
            ip_address=client_ip,
        )

        return {
            "success": False,
            "message": "Invalid email or password."
        }

    clear_login_attempts(client_ip, request.email)

    record_event(
        event_type="login_success",
        path="/api/login",
        details={
            "email": request.email.strip().lower(),
            "ip_address": client_ip,
        },
        user_id=user["id"],
        email=user["email"],
        ip_address=client_ip,
    )

    session_id, expires_at = create_session(
        user["id"],
        user["email"],
    )

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
        max_age=SESSION_TTL_SECONDS,
        path="/",
    )

    # -----------------------------------------------------
    # Get user ID
    # -----------------------------------------------------

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, email
        FROM users
        WHERE LOWER(email) = LOWER(?)
        LIMIT 1
        """,
        (request.email.strip(),)
    )

    db_user = cursor.fetchone()

    if db_user:

        # -------------------------------------------------
        # Record login
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO login_activity
            (
                user_id,
                email,
                login_time
            )
            VALUES (?, ?, ?)
            """,
            (
                db_user["id"],
                db_user["email"],
                datetime.now().isoformat(
                    sep=" ",
                    timespec="seconds"
                ),
            ),
        )

        conn.commit()

    conn.close()

    sync_excel_safely()

    return {
        "success": True,
        "message": "Login successful",
        "user": user,
        "session_expires_at": expires_at,
    }


# =========================================================
# SESSION ENDPOINTS
# =========================================================

@app.get("/api/session")
def session_endpoint(request: Request):

    session = get_session(
        request.cookies.get(SESSION_COOKIE_NAME)
    )

    if not session:

        return {
            "authenticated": False,
            "user": None,
        }

    return {
        "authenticated": True,
        "user": {
            "id": session["id"],
            "email": session["email"],
        },
    }


@app.post("/api/logout")
def logout(request: Request, response: Response):

    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    session = get_session(session_id)

    invalidate_session(session_id)

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
    )

    record_event(
        event_type="logout",
        path="/api/logout",
        details={
            "session_invalidated": bool(session),
        },
        user_id=session["id"] if session else None,
        email=session["email"] if session else None,
        ip_address=request.client.host if request.client else None,
    )

    return {
        "success": True,
        "message": "Logged out successfully.",
    }


# =========================================================
# FORGOT PASSWORD
# =========================================================

@app.post("/api/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest,
    request_obj: Request,
):

    success, message = request_password_reset(
        request.email
    )

    record_event(
        event_type="password_reset_requested",
        path="/api/forgot-password",
        details={
            "requested_email": request.email.strip().lower(),
            "success": success,
            "message": message,
        },
        email=request.email.strip().lower(),
        ip_address=request_obj.client.host if request_obj.client else None,
    )

    return {
        "success": success,
        "message": message
    }


# =========================================================
# VERIFY OTP
# =========================================================

@app.post("/api/verify-otp")
def verify_otp_endpoint(
    request: VerifyOTPRequest,
    request_obj: Request,
):

    success, message = verify_otp(
        request.email,
        request.otp
    )

    record_event(
        event_type="otp_verified",
        path="/api/verify-otp",
        details={
            "requested_email": request.email.strip().lower(),
            "success": success,
            "message": message,
        },
        email=request.email.strip().lower(),
        ip_address=request_obj.client.host if request_obj.client else None,
    )

    return {
        "success": success,
        "message": message
    }


# =========================================================
# RESET PASSWORD
# =========================================================

@app.post("/api/reset-password")
def reset_password_endpoint(
    request: ResetPasswordRequest,
    request_obj: Request,
):

    success, message = reset_password(
        request.email,
        request.otp,
        request.new_password
    )

    record_event(
        event_type="password_reset_completed",
        path="/api/reset-password",
        details={
            "requested_email": request.email.strip().lower(),
            "success": success,
            "message": message,
        },
        email=request.email.strip().lower(),
        ip_address=request_obj.client.host if request_obj.client else None,
    )

    return {
        "success": success,
        "message": message
    }


# =========================================================
# AUTH DEPENDENCIES
# =========================================================

def verify_session(request: Request):

    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    session = get_session(session_id)

    if not session:

        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )

    return session


def verify_admin(session: dict = Depends(verify_session)):

    if session["email"].strip().lower() != ADMIN_EMAIL.lower():

        raise HTTPException(
            status_code=403,
            detail="Administrator access required."
        )

    return session


# =========================================================
# NEXUS RESEARCH
# =========================================================

@app.post("/api/research")
def research(
    request: ResearchRequest,
    session: dict = Depends(verify_session),
):

    record_event(
        event_type="research_requested",
        path="/api/research",
        details={
            "topic": request.topic[:500],
        },
        user_id=session["id"],
        email=session["email"],
    )

    result = run_research_pipeline(
        request.topic
    )

    return result


# =========================================================
# INDIVIDUAL PDF UPLOAD
# =========================================================

@app.post("/api/individual/upload")
async def upload_individual_pdf(
    file: UploadFile = File(...),
    session: dict = Depends(verify_session),
):

    if (
        not file.filename
        or not file.filename.lower().endswith(".pdf")
    ):

        return {
            "success": False,
            "message": "Only PDF files are allowed."
        }

    pdf_bytes = await file.read()

    record_event(
        event_type="pdf_upload",
        path="/api/individual/upload",
        details={
            "filename": file.filename,
            "size_bytes": len(pdf_bytes),
        },
        user_id=session["id"],
        email=session["email"],
    )

    result = build_individual_index(
        pdf_bytes,
        file.filename
    )

    return result


# =========================================================
# INDIVIDUAL PDF CHAT
# =========================================================

@app.post("/api/individual/chat")
def individual_chat(
    request: IndividualQuestionRequest,
    session: dict = Depends(verify_session),
):

    if not request.question.strip():

        return {
            "success": False,
            "message": "Please enter a question."
        }

    record_event(
        event_type="document_chat",
        path="/api/individual/chat",
        details={
            "document_id": request.document_id,
            "question_length": len(request.question.strip()),
        },
        user_id=session["id"],
        email=session["email"],
    )

    result = answer_individual_question(
        request.question,
        request.document_id
    )

    return result


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.get("/api/admin/dashboard")
def admin_dashboard(session: dict = Depends(verify_admin)):

    # Make sure old DB is repaired
    initialize_admin_database()

    conn = get_db()
    cursor = conn.cursor()

    # -----------------------------------------------------
    # TOTAL USERS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM users
        """
    )

    total_users = cursor.fetchone()["total"]

    # -----------------------------------------------------
    # TOTAL LOGINS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM login_activity
        """
    )

    total_logins = cursor.fetchone()["total"]

    # -----------------------------------------------------
    # USERS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            id,
            email,
            created_at
        FROM users
        ORDER BY id DESC
        """
    )

    users = []

    for row in cursor.fetchall():

        users.append({
            "id": row["id"],
            "email": row["email"],
            "created_at": row["created_at"],
        })

    # -----------------------------------------------------
    # RECENT LOGINS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            id,
            user_id,
            email,
            login_time
        FROM login_activity
        ORDER BY id DESC
        LIMIT 100
        """
    )

    recent_logins = []

    for row in cursor.fetchall():

        recent_logins.append({
            "id": row["id"],
            "user_id": row["user_id"],
            "email": row["email"],
            "login_time": row["login_time"],
        })

    # -----------------------------------------------------
    # RECENT SECURITY EVENTS
    # -----------------------------------------------------

    cursor.execute(
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
        LIMIT 100
        """
    )

    recent_events = []

    for row in cursor.fetchall():

        recent_events.append({
            "id": row["id"],
            "event_type": row["event_type"],
            "user_id": row["user_id"],
            "email": row["email"],
            "ip_address": row["ip_address"],
            "path": row["path"],
            "details": row["details"],
            "occurred_at": row["occurred_at"],
        })

    conn.close()

    return {
        "success": True,
        "total_users": total_users,
        "total_logins": total_logins,
        "users": users,
        "recent_logins": recent_logins,
        "recent_events": recent_events,
    }


# =========================================================
# DELETE USER
# =========================================================

@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(
    user_id: int,
    session: dict = Depends(verify_admin)
):

    record_event(
        event_type="admin_user_deleted",
        path=f"/api/admin/users/{user_id}",
        details={
            "deleted_user_id": user_id,
        },
        user_id=session["id"],
        email=session["email"],
    )

    conn = get_db()
    cursor = conn.cursor()

    # -----------------------------------------------------
    # Find target user
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT id, email
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    )

    target = cursor.fetchone()

    if not target:

        conn.close()

        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    # -----------------------------------------------------
    # NEVER DELETE ADMIN
    # -----------------------------------------------------

    if target["email"].strip().lower() == ADMIN_EMAIL.lower():

        conn.close()

        raise HTTPException(
            status_code=403,
            detail="Administrator account cannot be deleted."
        )

    # -----------------------------------------------------
    # Delete user's login history
    # -----------------------------------------------------

    cursor.execute(
        """
        DELETE FROM login_activity
        WHERE user_id = ?
        """,
        (user_id,)
    )

    # -----------------------------------------------------
    # Delete user
    # -----------------------------------------------------

    cursor.execute(
        """
        DELETE FROM users
        WHERE id = ?
        """,
        (user_id,)
    )

    conn.commit()
    conn.close()

    sync_excel_safely()

    return {
        "success": True,
        "message": "User removed successfully."
    }


# =========================================================
# DELETE ONE LOGIN RECORD
# =========================================================

@app.delete("/api/admin/logins/{activity_id}")
def admin_delete_login(
    activity_id: int,
    session: dict = Depends(verify_admin)
):

    record_event(
        event_type="admin_login_record_deleted",
        path=f"/api/admin/logins/{activity_id}",
        details={
            "deleted_activity_id": activity_id,
        },
        user_id=session["id"],
        email=session["email"],
    )

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM login_activity
        WHERE id = ?
        """,
        (activity_id,)
    )

    deleted = cursor.rowcount

    conn.commit()
    conn.close()

    if deleted == 0:

        raise HTTPException(
            status_code=404,
            detail="Login record not found."
        )

    sync_excel_safely()

    return {
        "success": True,
        "message": "Login record removed."
    }


# =========================================================
# DELETE ALL LOGIN HISTORY
# =========================================================

@app.delete("/api/admin/logins")
def admin_clear_logins(
    session: dict = Depends(verify_admin)
):

    record_event(
        event_type="admin_login_history_cleared",
        path="/api/admin/logins",
        user_id=session["id"],
        email=session["email"],
    )

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM login_activity
        """
    )

    deleted = cursor.rowcount

    conn.commit()
    conn.close()

    sync_excel_safely()

    return {
        "success": True,
        "message": "All login history deleted.",
        "deleted": deleted,
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/api/health")
def health_check():

    return {
        "status": "healthy",
        "database": DB_PATH.name,
        "timestamp": datetime.now().isoformat(
            sep=" ",
            timespec="seconds"
        )
    }