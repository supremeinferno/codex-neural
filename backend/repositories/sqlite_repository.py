from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("NEXUS_DB_PATH", str(BASE_DIR / "users.db")))


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def record_login_activity(user_id: int, email: str, login_time: str | None = None):
    login_time = login_time or datetime.now().isoformat(sep=" ", timespec="seconds")
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO login_activity (user_id, email, login_time)
            VALUES (?, ?, ?)
            """,
            (user_id, email, login_time),
        )
        conn.commit()
    finally:
        conn.close()


def create_user(email: str, password_hash: str, role: str, created_at: str):
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO users (email, password, role, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (email, password_hash, role, created_at),
        )
        conn.commit()
    finally:
        conn.close()


def get_user_by_email(email: str):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, email, password, role FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_user_password(user_id: int, password_hash: str):
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET password = ? WHERE id = ?",
            (password_hash, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def create_session_record(session_id, user_id, email, created_at, expires_at):
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO sessions (session_id, user_id, email, created_at, expires_at, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, user_id, email, created_at, expires_at, created_at),
        )
        conn.commit()
    finally:
        conn.close()


def delete_session_record(session_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()


def get_session_record(session_id):
    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT user_id, email, expires_at
            FROM sessions
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_role_record(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT role FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return row["role"] if row else None
    finally:
        conn.close()


def insert_event(event_type, path, details, user_id, email, ip_address, occurred_at):
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO events (event_type, user_id, email, ip_address, path, details, occurred_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                user_id,
                email,
                ip_address,
                path,
                json.dumps(details, default=str) if details is not None else None,
                occurred_at,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_events(limit=100):
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT id, event_type, user_id, email, ip_address, path, details, occurred_at
            FROM events
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def user_exists(email):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT 1 FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def store_password_reset_otp(email, otp, expires):
    conn = get_db()
    try:
        conn.execute("DELETE FROM password_reset_otps WHERE email = ?", (email,))
        conn.execute(
            "INSERT INTO password_reset_otps (email, otp, expires) VALUES (?, ?, ?)",
            (email, otp, expires),
        )
        conn.commit()
    finally:
        conn.close()


def get_password_reset_otp(email):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT otp, expires FROM password_reset_otps WHERE email = ?",
            (email,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_password_reset_otp(email):
    conn = get_db()
    try:
        conn.execute("DELETE FROM password_reset_otps WHERE email = ?", (email,))
        conn.commit()
    finally:
        conn.close()


def update_user_password_by_email(email, password_hash):
    conn = get_db()
    try:
        cursor = conn.execute(
            "UPDATE users SET password = ? WHERE email = ?",
            (password_hash, email),
        )
        if cursor.rowcount:
            conn.execute("DELETE FROM password_reset_otps WHERE email = ?", (email,))
            conn.commit()
        else:
            conn.rollback()
        return cursor.rowcount
    finally:
        conn.close()


def get_admin_dashboard_data():
    conn = get_db()
    try:
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_logins = conn.execute("SELECT COUNT(*) FROM login_activity").fetchone()[0]
        users = conn.execute(
            "SELECT id, email, role, created_at FROM users ORDER BY id DESC"
        ).fetchall()
        recent_logins = conn.execute(
            """
            SELECT id, user_id, email, login_time
            FROM login_activity
            ORDER BY id DESC
            LIMIT 100
            """
        ).fetchall()
        recent_events = conn.execute(
            """
            SELECT id, event_type, user_id, email, ip_address, path, details, occurred_at
            FROM events
            ORDER BY id DESC
            LIMIT 100
            """
        ).fetchall()
        return {
            "success": True,
            "total_users": total_users,
            "total_logins": total_logins,
            "users": [
                {
                    "id": row["id"],
                    "email": row["email"],
                    "role": row["role"] or "user",
                    "created_at": row["created_at"],
                }
                for row in users
            ],
            "recent_logins": [dict(row) for row in recent_logins],
            "recent_events": [dict(row) for row in recent_events],
        }
    finally:
        conn.close()


def get_user_record(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, email, role FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_user_and_login_activity(user_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM login_activity WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()


def delete_login_activity(activity_id):
    conn = get_db()
    try:
        cursor = conn.execute("DELETE FROM login_activity WHERE id = ?", (activity_id,))
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def clear_login_activity():
    conn = get_db()
    try:
        cursor = conn.execute("DELETE FROM login_activity")
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def init_auth_tables():
    """Create the base application schema used across auth and admin flows."""
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS password_reset_otps (
            email TEXT PRIMARY KEY,
            otp TEXT NOT NULL,
            expires REAL NOT NULL
        )
        """
    )
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
    conn.execute(
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


def initialize_admin_database():
    """Create or repair database tables without deleting user data."""
    init_auth_tables()
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name='users'
        """
    )
    users_exists = cursor.fetchone()

    if users_exists:
        cursor.execute("PRAGMA table_info(users)")
        columns = [row["name"] for row in cursor.fetchall()]

        if "created_at" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
            cursor.execute(
                "UPDATE users SET created_at = ? WHERE created_at IS NULL OR created_at = ''",
                (datetime.now().isoformat(sep=" ", timespec="seconds"),),
            )

        if "role" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
            cursor.execute(
                "UPDATE users SET role = 'admin' WHERE email IN (?, ?)",
                ("codexproject9@gmail.com", "admin@localhost"),
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
