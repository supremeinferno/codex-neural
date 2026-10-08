from fastapi import APIRouter, Depends, HTTPException

from backend.auth import ADMIN_EMAILS, record_event, verify_admin
from backend.repositories.sqlite_repository import get_db, initialize_admin_database

router = APIRouter()


def sync_excel_safely():
    try:
        from backend.auth import sync_excel

        sync_excel()
    except ImportError:
        pass
    except Exception as error:
        print("Excel synchronization warning:", error)


@router.get("/api/admin/dashboard")
def admin_dashboard(session: dict = Depends(verify_admin)):
    initialize_admin_database()
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM users")
    total_users = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM login_activity")
    total_logins = cursor.fetchone()["total"]

    cursor.execute(
        "SELECT id, email, role, created_at FROM users ORDER BY id DESC"
    )
    users = [
        {
            "id": row["id"],
            "email": row["email"],
            "role": row["role"] or "user",
            "created_at": row["created_at"],
        }
        for row in cursor.fetchall()
    ]

    cursor.execute(
        """
        SELECT id, user_id, email, login_time
        FROM login_activity
        ORDER BY id DESC
        LIMIT 100
        """
    )
    recent_logins = [dict(row) for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT id, event_type, user_id, email, ip_address, path, details, occurred_at
        FROM events
        ORDER BY id DESC
        LIMIT 100
        """
    )
    recent_events = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {
        "success": True,
        "total_users": total_users,
        "total_logins": total_logins,
        "users": users,
        "recent_logins": recent_logins,
        "recent_events": recent_events,
    }


@router.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, session: dict = Depends(verify_admin)):
    record_event(
        event_type="admin_user_deleted",
        path=f"/api/admin/users/{user_id}",
        details={"deleted_user_id": user_id},
        user_id=session["id"],
        email=session["email"],
    )

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, role FROM users WHERE id = ?", (user_id,))
    target = cursor.fetchone()

    if not target:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found.")

    role = (target["role"] or "user").strip().lower()
    email = target["email"].strip().lower()
    if email in ADMIN_EMAILS or role == "admin":
        conn.close()
        raise HTTPException(
            status_code=403,
            detail="Administrator account cannot be deleted.",
        )

    cursor.execute("DELETE FROM login_activity WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    sync_excel_safely()
    return {"success": True, "message": "User removed successfully."}


@router.delete("/api/admin/logins/{activity_id}")
def admin_delete_login(activity_id: int, session: dict = Depends(verify_admin)):
    record_event(
        event_type="admin_login_record_deleted",
        path=f"/api/admin/logins/{activity_id}",
        details={"deleted_activity_id": activity_id},
        user_id=session["id"],
        email=session["email"],
    )

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM login_activity WHERE id = ?", (activity_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    if deleted == 0:
        raise HTTPException(status_code=404, detail="Login record not found.")

    sync_excel_safely()
    return {"success": True, "message": "Login record removed."}


@router.delete("/api/admin/logins")
def admin_clear_logins(session: dict = Depends(verify_admin)):
    record_event(
        event_type="admin_login_history_cleared",
        path="/api/admin/logins",
        user_id=session["id"],
        email=session["email"],
    )

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM login_activity")
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    sync_excel_safely()
    return {
        "success": True,
        "message": "All login history deleted.",
        "deleted": deleted,
    }
