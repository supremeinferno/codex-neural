from fastapi import APIRouter, Depends, HTTPException

from backend.auth import record_event, verify_admin
from backend.services import admin_service

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
    return admin_service.get_dashboard_data()


@router.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, session: dict = Depends(verify_admin)):
    record_event(
        event_type="admin_user_deleted",
        path=f"/api/admin/users/{user_id}",
        details={"deleted_user_id": user_id},
        user_id=session["id"],
        email=session["email"],
    )

    try:
        admin_service.delete_user(user_id)
    except admin_service.UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found.")
    except admin_service.ProtectedAdministratorError:
        raise HTTPException(
            status_code=403,
            detail="Administrator account cannot be deleted.",
        )

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

    if not admin_service.delete_login_record(activity_id):
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

    deleted = admin_service.clear_login_history()

    sync_excel_safely()
    return {
        "success": True,
        "message": "All login history deleted.",
        "deleted": deleted,
    }
