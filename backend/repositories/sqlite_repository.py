from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "users.db"


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


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
