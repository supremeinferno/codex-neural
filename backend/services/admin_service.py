from backend.repositories import sqlite_repository
from backend.services.auth_service import ADMIN_EMAILS


class UserNotFoundError(Exception):
    pass


class ProtectedAdministratorError(Exception):
    pass


def get_dashboard_data():
    return sqlite_repository.get_admin_dashboard_data()


def delete_user(user_id: int):
    target = sqlite_repository.get_user_record(user_id)
    if not target:
        raise UserNotFoundError

    email = target["email"].strip().lower()
    role = (target["role"] or "user").strip().lower()
    if email in ADMIN_EMAILS or role == "admin":
        raise ProtectedAdministratorError

    sqlite_repository.delete_user_and_login_activity(user_id)


def delete_login_record(activity_id: int) -> bool:
    return sqlite_repository.delete_login_activity(activity_id) > 0


def clear_login_history() -> int:
    return sqlite_repository.clear_login_activity()