import sqlite3
import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "users.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def register_user(email, password):
    email = email.strip().lower()

    if not email or not password:
        return False, "Email and password are required."

    conn = get_connection()

    try:
        conn.execute(
            "INSERT INTO users (email, password) VALUES (?, ?)",
            (email, hash_password(password)),
        )
        conn.commit()
        return True, "Account created successfully."

    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."

    finally:
        conn.close()


def authenticate_user(email, password):
    email = email.strip().lower()

    conn = get_connection()

    user = conn.execute(
        "SELECT id, email FROM users WHERE email = ? AND password = ?",
        (email, hash_password(password)),
    ).fetchone()

    conn.close()

    if user:
        return {
            "id": user[0],
            "email": user[1],
        }

    return None


# Create the database/table when this module is loaded.
init_db()