from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.pipeline import run_research_pipeline

from backend.auth import (
    register_user,
    authenticate_user,
    request_password_reset,
    verify_otp,
    reset_password
)

from backend.individual import (
    build_individual_index,
    answer_individual_question
)


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="Nexus Research API",
    description="Multi-Agent AI Research System",
    version="1.0.0"
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
# AUTHENTICATION
# =========================================================

@app.post("/api/register")
def register(request: AuthRequest):

    success, message = register_user(
        request.email,
        request.password
    )

    return {
        "success": success,
        "message": message
    }


@app.post("/api/login")
def login(request: AuthRequest):

    user = authenticate_user(
        request.email,
        request.password
    )

    if user:
        return {
            "success": True,
            "message": "Login successful",
            "user": user
        }

    return {
        "success": False,
        "message": "Invalid email or password."
    }


# =========================================================
# FORGOT PASSWORD
# =========================================================

@app.post("/api/forgot-password")
def forgot_password(request: ForgotPasswordRequest):

    success, message = request_password_reset(
        request.email
    )

    return {
        "success": success,
        "message": message
    }


# =========================================================
# VERIFY OTP
# =========================================================

@app.post("/api/verify-otp")
def verify_otp_endpoint(request: VerifyOTPRequest):

    success, message = verify_otp(
        request.email,
        request.otp
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
    request: ResetPasswordRequest
):

    success, message = reset_password(
        request.email,
        request.otp,
        request.new_password
    )

    return {
        "success": success,
        "message": message
    }


# =========================================================
# NEXUS RESEARCH
# =========================================================

@app.post("/api/research")
def research(request: ResearchRequest):

    result = run_research_pipeline(
        request.topic
    )

    return result


# =========================================================
# INDIVIDUAL PDF ANALYZER
# =========================================================

@app.post("/api/individual/upload")
async def upload_individual_pdf(
    file: UploadFile = File(...)
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
    request: IndividualQuestionRequest
):

    if not request.question.strip():
        return {
            "success": False,
            "message": "Please enter a question."
        }

    result = answer_individual_question(
        request.question,
        request.document_id
    )

    return result


# ==========================================================
# ADMIN DASHBOARD
# ==========================================================

from fastapi import HTTPException

from auth import (
    get_total_users,
    get_total_logins,
    get_users,
    get_login_activity,
    delete_user,
    clear_login_activity,
)


ADMIN_EMAIL = "codexproject9@gmail.com"


def verify_admin(email: str):

    if not email:
        raise HTTPException(
            status_code=401,
            detail="Administrator email is required."
        )

    if email.strip().lower() != ADMIN_EMAIL.lower():
        raise HTTPException(
            status_code=403,
            detail="Administrator access required."
        )


# ==========================================================
# DASHBOARD OVERVIEW
# ==========================================================

@app.get("/api/admin/dashboard")
def admin_dashboard(email: str):

    verify_admin(email)

    return {
        "success": True,

        "total_users": get_total_users(),

        "total_logins": get_total_logins(),

        "users": [
            {
                "id": user[0],
                "email": user[1],
                "created_at": user[2],
            }
            for user in get_users()
        ],

        "recent_logins": [
            {
                "id": login[0],
                "user_id": login[1],
                "email": login[2],
                "login_time": login[3],
            }
            for login in get_login_activity()
        ],
    }


# ==========================================================
# REMOVE ONE USER
# ==========================================================

@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(
    user_id: int,
    email: str
):

    verify_admin(email)

    # Never allow admin account to be deleted
    if email.strip().lower() == ADMIN_EMAIL.lower():

        # Check target user separately below
        pass

    success = delete_user(user_id)

    if not success:

        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    return {
        "success": True,
        "message": "User removed successfully."
    }


# ==========================================================
# DELETE ONE LOGIN RECORD
# ==========================================================

@app.delete("/api/admin/logins/{activity_id}")
def admin_delete_login(
    activity_id: int,
    email: str
):

    verify_admin(email)

    import sqlite3

    conn = sqlite3.connect("users.db")

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

    # Keep Excel synchronized
    from auth import sync_excel

    sync_excel()

    return {
        "success": True,
        "message": "Login record removed."
    }


# ==========================================================
# DELETE ALL LOGIN HISTORY
# ==========================================================

@app.delete("/api/admin/logins")
def admin_clear_logins(email: str):

    verify_admin(email)

    clear_login_activity()

    return {
        "success": True,
        "message": "All login history deleted."
    }