from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import RoleName
from app.models.user import User
from app.services.notification_service import (
    count_unread_notifications,
    create_notifications_for_roles,
    create_notifications_for_user_ids,
    get_unread_notifications,
    mark_notification_as_read,
)


def test_create_notifications_for_roles_creates_unread_items(db_session: Session) -> None:
    user = db_session.scalar(select(User))
    assert user is not None

    create_notifications_for_roles(
        db=db_session,
        role_names=[RoleName.ADMIN.value],
        title="Ticket Baru",
        message="Ada ticket baru yang perlu ditinjau.",
        notification_type="TICKET",
        ticket_id="ticket-123",
    )

    unread_items = get_unread_notifications(db_session, user.id)

    assert len(unread_items) == 1
    assert unread_items[0].user_id == user.id
    assert unread_items[0].ticket_id == "ticket-123"
    assert unread_items[0].is_read is False
    assert count_unread_notifications(db_session, user.id) == 1


def test_mark_notification_as_read_updates_notification(db_session: Session) -> None:
    user = db_session.scalar(select(User))
    assert user is not None

    create_notifications_for_user_ids(
        db=db_session,
        user_ids=[user.id],
        title="Pengingat SLA",
        message="Ticket mendekati batas SLA.",
        notification_type="SLA",
        ticket_id="ticket-456",
    )

    notification = get_unread_notifications(db_session, user.id)[0]

    updated = mark_notification_as_read(db_session, notification.id, user.id)

    assert updated is not None
    assert updated.is_read is True
    assert count_unread_notifications(db_session, user.id) == 0
