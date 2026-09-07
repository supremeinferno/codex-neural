from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sqlite3
from pathlib import Path


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
)

from backend.individual import (
    build_individual_index,
    answer_individual_question,
)


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

DATABASE_PATH = BASE_DIR / "users.db"

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
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# DATABASE HELPER
# =========================================================

def get_db():

    conn = sqlite3.connect(str(DATABASE_PATH))

    conn.row_factory = sqlite3.Row

    return conn


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
        "success": True,
        "message": "Nexus Research API is running",
    }


# =========================================================
# AUTHENTICATION
# =========================================================

@app.post("/api/register")
def register(request: AuthRequest):

    success, message = register_user(
        request.email,
        request.password,
    )

    return {
        "success": success,
        "message": message,
    }


@app.post("/api/login")
def login(request: AuthRequest):

    user = authenticate_user(
        request.email,
        request.password,
    )

    if user:

        # -------------------------------------------------
        # RECORD LOGIN ACTIVITY
        # -------------------------------------------------

        conn = get_db()
        cursor = conn.cursor()

        user_id = None

        # authenticate_user may return a dictionary
        if isinstance(user, dict):
            user_id = user.get("id")

        cursor.execute(
            """
            INSERT INTO login_activity
            (
                user_id,
                email,
                login_time
            )
            VALUES (?, ?, datetime('now', 'localtime'))
            """,
            (
                user_id,
                request.email.strip().lower(),
            ),
        )

        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": "Login successful",
            "user": user,
        }

    return {
        "success": False,
        "message": "Invalid email or password.",
    }


# =========================================================
# FORGOT PASSWORD
# =========================================================

@app.post("/api/forgot-password")
def forgot_password(request: ForgotPasswordRequest):

    success, message = request_password_reset(
        request.email,
    )

    return {
        "success": success,
        "message": message,
    }


# =========================================================
# VERIFY OTP
# =========================================================

@app.post("/api/verify-otp")
def verify_otp_endpoint(request: VerifyOTPRequest):

    success, message = verify_otp(
        request.email,
        request.otp,
    )

    return {
        "success": success,
        "message": message,
    }


# =========================================================
# RESET PASSWORD
# =========================================================

@app.post("/api/reset-password")
def reset_password_endpoint(
    request: ResetPasswordRequest,
):

    success, message = reset_password(
        request.email,
        request.otp,
        request.new_password,
    )

    return {
        "success": success,
        "message": message,
    }


# =========================================================
# NEXUS RESEARCH
# =========================================================

@app.post("/api/research")
def research(request: ResearchRequest):

    result = run_research_pipeline(
        request.topic,
    )

    return result


# =========================================================
# INDIVIDUAL PDF ANALYZER
# =========================================================

@app.post("/api/individual/upload")
async def upload_individual_pdf(
    file: UploadFile = File(...),
):

    if (
        not file.filename
        or not file.filename.lower().endswith(".pdf")
    ):

        return {
            "success": False,
            "message": "Only PDF files are allowed.",
        }

    pdf_bytes = await file.read()

    result = build_individual_index(
        pdf_bytes,
        file.filename,
    )

    return result


# =========================================================
# INDIVIDUAL PDF CHAT
# =========================================================

@app.post("/api/individual/chat")
def individual_chat(
    request: IndividualQuestionRequest,
):

    if not request.question.strip():

        return {
            "success": False,
            "message": "Please enter a question.",
        }

    result = answer_individual_question(
        request.question,
        request.document_id,
    )

    return result


# =========================================================
# ADMIN AUTHORIZATION
# =========================================================

def verify_admin(email: str):

    if not email:

        raise HTTPException(
            status_code=401,
            detail="Administrator email is required.",
        )

    if email.strip().lower() != ADMIN_EMAIL.lower():

        raise HTTPException(
            status_code=403,
            detail="Administrator access required.",
        )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.get("/api/admin/dashboard")
def admin_dashboard(email: str):

    verify_admin(email)

    conn = get_db()

    cursor = conn.cursor()

    # -----------------------------------------------------
    # TOTAL USERS
    # -----------------------------------------------------

    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )

    total_users = cursor.fetchone()[0]


    # -----------------------------------------------------
    # TOTAL LOGINS
    # -----------------------------------------------------

    cursor.execute(
        "SELECT COUNT(*) FROM login_activity"
    )

    total_logins = cursor.fetchone()[0]


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
        ORDER BY created_at DESC
        """
    )

    users = [

        {
            "id": row["id"],
            "email": row["email"],
            "created_at": row["created_at"],
        }

        for row in cursor.fetchall()
    ]


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
        ORDER BY login_time DESC
        """
    )

    recent_logins = [

        {
            "id": row["id"],
            "user_id": row["user_id"],
            "email": row["email"],
            "login_time": row["login_time"],
        }

        for row in cursor.fetchall()
    ]


    conn.close()


    return {

        "success": True,

        "total_users": total_users,

        "total_logins": total_logins,

        "users": users,

        "recent_logins": recent_logins,

    }


# =========================================================
# REMOVE USER
# =========================================================

@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(
    user_id: int,
    email: str,
):

    verify_admin(email)

    conn = get_db()

    cursor = conn.cursor()


    # -----------------------------------------------------
    # FIND TARGET USER
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT email
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    )

    user = cursor.fetchone()


    if user is None:

        conn.close()

        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )


    # -----------------------------------------------------
    # NEVER DELETE ADMIN
    # -----------------------------------------------------

    if user["email"].strip().lower() == ADMIN_EMAIL.lower():

        conn.close()

        raise HTTPException(
            status_code=403,
            detail="Administrator account cannot be deleted.",
        )


    # -----------------------------------------------------
    # DELETE LOGIN HISTORY OF USER
    # -----------------------------------------------------

    cursor.execute(
        """
        DELETE FROM login_activity
        WHERE user_id = ?
        """,
        (user_id,),
    )


    # -----------------------------------------------------
    # DELETE USER
    # -----------------------------------------------------

    cursor.execute(
        """
        DELETE FROM users
        WHERE id = ?
        """,
        (user_id,),
    )


    conn.commit()

    conn.close()


    return {

        "success": True,

        "message": "User removed successfully.",

    }


# =========================================================
# DELETE ONE LOGIN RECORD
# =========================================================

@app.delete("/api/admin/logins/{activity_id}")
def admin_delete_login(
    activity_id: int,
    email: str,
):

    verify_admin(email)

    conn = get_db()

    cursor = conn.cursor()


    cursor.execute(
        """
        DELETE FROM login_activity
        WHERE id = ?
        """,
        (activity_id,),
    )


    deleted = cursor.rowcount

    conn.commit()

    conn.close()


    if deleted == 0:

        raise HTTPException(
            status_code=404,
            detail="Login record not found.",
        )


    return {

        "success": True,

        "message": "Login record removed.",

    }


# =========================================================
# DELETE ALL LOGIN HISTORY
# =========================================================

@app.delete("/api/admin/logins")
def admin_clear_logins(email: str):

    verify_admin(email)

    conn = get_db()

    cursor = conn.cursor()


    cursor.execute(
        "DELETE FROM login_activity"
    )


    deleted = cursor.rowcount

    conn.commit()

    conn.close()


    return {

        "success": True,

        "message": "All login history deleted.",

        "deleted_count": deleted,

    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/api/health")
def health_check():

    return {

        "success": True,

        "status": "healthy",

        "database": DATABASE_PATH.exists(),

    }



# =========================================================
# DATABASE HELPER
# =========================================================

def get_db():

    conn = sqlite3.connect(str(DATABASE_PATH))

    conn.row_factory = sqlite3.Row

    return conn


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def initialize_database():

    conn = get_db()
    cursor = conn.cursor()

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


initialize_database()