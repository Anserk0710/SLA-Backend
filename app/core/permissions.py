from enum import Enum
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.constants import RoleName
from app.models.ticket import Ticket
from app.models.ticket_assignment import TicketAssignment
from app.models.user import User


class UserRole(str, Enum):
    ADMIN = RoleName.ADMIN.value
    HEAD = RoleName.HEAD.value
    TECHNICIAN = RoleName.TECHNICIAN.value


def _normalize_role_name(value: str | Enum | None) -> str | None:
    if value is None:
        return None

    if isinstance(value, Enum):
        value = value.value

    if not isinstance(value, str):
        return None

    normalized = value.strip().lower()
    return normalized or None


def get_role_name(user: Any) -> str | None:
    role_name = _normalize_role_name(getattr(user, "role_name", None))
    if role_name:
        return role_name

    role_obj = getattr(user, "role", None)
    if role_obj is not None:
        role_name = _normalize_role_name(getattr(role_obj, "name", role_obj))
        if role_name:
            return role_name

    return None


def require_roles(*allowed_roles: str | RoleName | UserRole):
    normalized_allowed_roles = {
        normalized
        for role in allowed_roles
        if (normalized := _normalize_role_name(role)) is not None
    }

    def checker(current_user: User = Depends(get_current_active_user)) -> User:
        role_name = get_role_name(current_user)

        if role_name not in normalized_allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anda tidak memiliki izin untuk mengakses resource ini.",
            )

        return current_user

    return checker


def ensure_ticket_visible_to_user(
    db: Session,
    ticket_id: str,
    current_user: User,
) -> None:
    ticket_exists = db.scalar(select(Ticket.id).where(Ticket.id == ticket_id))
    if ticket_exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket tidak ditemukan",
        )

    role_name = get_role_name(current_user)

    if role_name in {UserRole.ADMIN.value, UserRole.HEAD.value}:
        return

    if role_name == UserRole.TECHNICIAN.value:
        assignment = db.scalar(
            select(TicketAssignment.id).where(
                TicketAssignment.ticket_id == ticket_id,
                TicketAssignment.technician_user_id == current_user.id,
            )
        )
        if assignment is not None:
            return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Anda tidak berhak mengakses ticket ini.",
    )


def ensure_assign_permission(current_user: User) -> None:
    role_name = get_role_name(current_user)
    if role_name not in {UserRole.ADMIN.value, UserRole.HEAD.value}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya admin/head yang boleh assign teknisi.",
        )


def ensure_dashboard_permission(current_user: User) -> None:
    role_name = get_role_name(current_user)
    if role_name not in {UserRole.ADMIN.value, UserRole.HEAD.value}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya admin/head yang boleh membuka dashboard operasional.",
        )


def ensure_technician_only(current_user: User) -> None:
    role_name = get_role_name(current_user)
    if role_name != UserRole.TECHNICIAN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya teknisi yang boleh melakukan aksi ini.",
        )
