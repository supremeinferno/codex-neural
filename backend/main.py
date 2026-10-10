from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import FileResponse

import sqlite3
import re
from pathlib import Path
from datetime import datetime
import json
import os
from fastapi import Depends


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
    get_user_for_session,
    revoke_session,
)

from backend.individual import (
    INDIVIDUAL_DB_PATH,
    build_individual_index,
    answer_individual_question,
)


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("CODEX_DATABASE_PATH", str(BASE_DIR / "users.db")))


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
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN ('research', 'pdf')),
            document_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            sources TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_documents (
            document_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            document_name TEXT NOT NULL,
            pages INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (document_id, user_id)
        )
        """
    )
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
def login(request: AuthRequest):

    user = authenticate_user(
        request.email,
        request.password
    )

    if not user:

        return {
            "success": False,
            "message": "Invalid email or password."
        }

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

    token = create_session(user["id"])
    return {
        "success": True,
        "message": "Login successful",
        "user": user,
        "token": token,
    }


# =========================================================
# FORGOT PASSWORD
# =========================================================

@app.post("/api/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest
):

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
def verify_otp_endpoint(
    request: VerifyOTPRequest
):

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



def require_user(authorization: str | None = Header(default=None)):
    scheme, _, token = (authorization or "").partition(" ")
    user = get_user_for_session(token) if scheme.lower() == "bearer" else None
    if not user:
        raise HTTPException(status_code=401, detail="Please sign in again.")
    return user


def _owned_conversation(cursor, conversation_id, user_id):
    cursor.execute(
        "SELECT * FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id),
    )
    return cursor.fetchone()


class ConversationRequest(BaseModel):
    title: str = "New chat"
    kind: str = "research"
    document_id: str | None = None


class ConversationRenameRequest(BaseModel):
    title: str


class MessageRequest(BaseModel):
    role: str
    content: str
    sources: list = []


@app.get("/api/session")
def session_info(user=Depends(require_user)):
    return {"user": user}


@app.post("/api/logout")
def logout(authorization: str | None = Header(default=None)):
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() == "bearer":
        revoke_session(token)
    return {"success": True}


@app.get("/api/conversations")
def list_conversations(kind: str | None = None, user=Depends(require_user)):
    if kind is not None and kind not in ("research", "pdf"):
        raise HTTPException(status_code=400, detail="Invalid chat type.")
    conn = get_db()
    query = "SELECT id, title, kind, document_id, created_at, updated_at FROM conversations WHERE user_id = ?"
    params = [user["id"]]
    if kind:
        query += " AND kind = ?"
        params.append(kind)
    query += " ORDER BY updated_at DESC, id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return {"conversations": [dict(row) for row in rows]}


@app.post("/api/conversations")
def create_conversation(request: ConversationRequest, user=Depends(require_user)):
    kind = request.kind.strip().lower()
    if kind not in ("research", "pdf"):
        raise HTTPException(status_code=400, detail="Invalid chat type.")
    title = request.title.strip()[:200] or "New chat"
    conn = get_db()
    if kind == "pdf":
        owned = conn.execute(
            "SELECT 1 FROM user_documents WHERE document_id = ? AND user_id = ?",
            (request.document_id, user["id"]),
        ).fetchone()
        if not owned:
            conn.close()
            raise HTTPException(status_code=404, detail="PDF document not found.")
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    cursor = conn.execute(
        "INSERT INTO conversations (user_id, title, kind, document_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user["id"], title, kind, request.document_id if kind == "pdf" else None, now, now),
    )
    conversation_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": conversation_id, "title": title, "kind": kind, "document_id": request.document_id}


@app.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: int, user=Depends(require_user)):
    conn = get_db()
    conversation = _owned_conversation(conn.cursor(), conversation_id, user["id"])
    if not conversation:
        conn.close()
        raise HTTPException(status_code=404, detail="Chat not found.")
    messages = conn.execute(
        "SELECT id, role, content, sources, created_at FROM conversation_messages WHERE conversation_id = ? ORDER BY id",
        (conversation_id,),
    ).fetchall()
    result = dict(conversation)
    if result.get("document_id"):
        document = conn.execute("SELECT document_name, pages FROM user_documents WHERE document_id = ? AND user_id = ?", (result["document_id"], user["id"])).fetchone()
        result["document"] = dict(document) if document else None
    result["messages"] = []
    for message in messages:
        item = dict(message)
        try:
            item["sources"] = json.loads(item["sources"] or "[]")
        except (ValueError, TypeError):
            item["sources"] = []
        result["messages"].append(item)
    conn.close()
    return result


@app.patch("/api/conversations/{conversation_id}")
def rename_conversation(conversation_id: int, request: ConversationRenameRequest, user=Depends(require_user)):
    title = request.title.strip()[:200]
    if not title:
        raise HTTPException(status_code=400, detail="Chat name cannot be empty.")
    conn = get_db()
    cursor = conn.cursor()
    if not _owned_conversation(cursor, conversation_id, user["id"]):
        conn.close()
        raise HTTPException(status_code=404, detail="Chat not found.")
    conn.execute("UPDATE conversations SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                 (title, datetime.now().isoformat(sep=" ", timespec="seconds"), conversation_id, user["id"]))
    conn.commit()
    conn.close()
    return {"success": True, "title": title}


@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, user=Depends(require_user)):
    conn = get_db()
    cursor = conn.cursor()
    if not _owned_conversation(cursor, conversation_id, user["id"]):
        conn.close()
        raise HTTPException(status_code=404, detail="Chat not found.")
    conn.execute("DELETE FROM conversation_messages WHERE conversation_id = ?", (conversation_id,))
    conn.execute("DELETE FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user["id"]))
    conn.commit()
    conn.close()
    return {"success": True}


@app.post("/api/conversations/{conversation_id}/messages")
def save_message(conversation_id: int, request: MessageRequest, user=Depends(require_user)):
    role = request.role.strip().lower()
    if role not in ("user", "assistant") or not request.content.strip():
        raise HTTPException(status_code=400, detail="A valid chat message is required.")
    conn = get_db()
    cursor = conn.cursor()
    conversation = _owned_conversation(cursor, conversation_id, user["id"])
    if not conversation:
        conn.close()
        raise HTTPException(status_code=404, detail="Chat not found.")
    if conversation["kind"] == "pdf":
        owned = conn.execute("SELECT 1 FROM user_documents WHERE document_id = ? AND user_id = ?",
                             (conversation["document_id"], user["id"])).fetchone()
        if not owned:
            conn.close()
            raise HTTPException(status_code=404, detail="PDF document not found.")
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    cursor.execute("INSERT INTO conversation_messages (conversation_id, role, content, sources, created_at) VALUES (?, ?, ?, ?, ?)",
                   (conversation_id, role, request.content, json.dumps(request.sources), now))
    if role == "user" and conversation["title"] == "New chat":
        title = request.content.strip().replace("\n", " ")[:70] or "New chat"
        conn.execute("UPDATE conversations SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                     (title, now, conversation_id, user["id"]))
    else:
        conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ? AND user_id = ?",
                     (now, conversation_id, user["id"]))
    conn.commit()
    conn.close()
    return {"success": True}


# =========================================================
# NEXUS RESEARCH
# =========================================================

@app.post("/api/research")
def research(
    request: ResearchRequest,
    user=Depends(require_user),
):

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
    user=Depends(require_user),
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

    if result.get("success"):
        conn = get_db()
        conn.execute(
            "INSERT OR IGNORE INTO user_documents (document_id, user_id, document_name, pages, created_at) VALUES (?, ?, ?, ?, ?)",
            (result["document_id"], user["id"], result["document_name"], result["pages"], datetime.now().isoformat(sep=" ", timespec="seconds")),
        )
        conn.commit()
        conn.close()
    return result


# =========================================================
# INDIVIDUAL PDF FILE
# =========================================================

@app.get("/api/individual/{document_id}/file")
def get_individual_pdf(
    document_id: str,
    download: bool = False,
    user=Depends(require_user),
):

    if re.fullmatch(r"[a-f0-9]{12}", document_id) is None:

        raise HTTPException(
            status_code=400,
            detail="Invalid document ID.",
        )

    conn = get_db()
    owned = conn.execute("SELECT 1 FROM user_documents WHERE document_id = ? AND user_id = ?", (document_id, user["id"])).fetchone()
    conn.close()
    if not owned:
        raise HTTPException(status_code=404, detail="PDF document not found.")

    pdf_path = Path(INDIVIDUAL_DB_PATH) / f"{document_id}.pdf"

    if not pdf_path.is_file():

        raise HTTPException(
            status_code=404,
            detail="PDF document not found.",
        )

    disposition = "attachment" if download else "inline"

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'{disposition}; filename="{pdf_path.name}"'
            ),
        },
    )


# =========================================================
# INDIVIDUAL PDF CHAT
# =========================================================

@app.post("/api/individual/chat")
def individual_chat(
    request: IndividualQuestionRequest,
    user=Depends(require_user),
):

    if not request.question.strip():

        return {
            "success": False,
            "message": "Please enter a question."
        }

    conn = get_db()
    owned = conn.execute("SELECT 1 FROM user_documents WHERE document_id = ? AND user_id = ?", (request.document_id, user["id"])).fetchone()
    conn.close()
    if not owned:
        raise HTTPException(status_code=404, detail="PDF document not found.")

    result = answer_individual_question(
        request.question,
        request.document_id
    )

    return result


# =========================================================
# ADMIN AUTHORIZATION
# =========================================================

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


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.get("/api/admin/dashboard")
def admin_dashboard(email: str):

    verify_admin(email)

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

    conn.close()

    return {
        "success": True,
        "total_users": total_users,
        "total_logins": total_logins,
        "users": users,
        "recent_logins": recent_logins,
    }


# =========================================================
# DELETE USER
# =========================================================

@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(
    user_id: int,
    email: str
):

    verify_admin(email)

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
    email: str
):

    verify_admin(email)

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
    email: str
):

    verify_admin(email)

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
