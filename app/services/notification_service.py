from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.role import Role
from app.models.user import User


def create_notifications_for_user_ids(
    db: Session,
    user_ids: Sequence[str],
    title: str,
    message: str,
    notification_type: str = "INFO",
    ticket_id: str | None = None,
) -> None:
    if not user_ids:
        return

    payload = [
        Notification(
            user_id=user_id,
            ticket_id=ticket_id,
            title=title,
            message=message,
            type=notification_type,
            is_read=False,
        )
        for user_id in user_ids
    ]

    db.add_all(payload)
    db.commit()


def get_user_ids_by_roles(db: Session, role_names: Sequence[str]) -> list[str]:
    """
    Sesuaikan query ini jika relasi User-Role Anda berbeda.
    Asumsi:
    - users.role_id -> roles.id
    - roles.name menyimpan nama role
    """
    stmt = (
        select(User.id)
        .join(Role, User.role_id == Role.id)
        .where(Role.name.in_(role_names))
    )

    return list(db.scalars(stmt).all())


def create_notifications_for_roles(
    db: Session,
    role_names: Sequence[str],
    title: str,
    message: str,
    notification_type: str = "INFO",
    ticket_id: str | None = None,
) -> None:
    user_ids = get_user_ids_by_roles(db, role_names)
    create_notifications_for_user_ids(
        db=db,
        user_ids=user_ids,
        title=title,
        message=message,
        notification_type=notification_type,
        ticket_id=ticket_id,
    )


def get_unread_notifications(
    db: Session,
    user_id: str,
    limit: int = 10,
) -> list[Notification]:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )


def count_unread_notifications(db: Session, user_id: str) -> int:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .count()
    )


def mark_notification_as_read(
    db: Session,
    notification_id: str,
    user_id: str,
) -> Notification | None:
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )

    if notification is None:
        return None

    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification
