import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.models.notification import Notification
from app.models.user import User
from app.services.notification_service import create_notifications_for_user_ids


@pytest.fixture()
def authenticated_client(client: TestClient, db_session: Session) -> TestClient:
    current_user = db_session.scalar(select(User))
    assert current_user is not None

    client.app.dependency_overrides[get_current_user] = lambda: current_user
    try:
        yield client
    finally:
        client.app.dependency_overrides.pop(get_current_user, None)


def test_unread_notifications_returns_current_user_items(
    authenticated_client: TestClient,
    db_session: Session,
) -> None:
    current_user = db_session.scalar(select(User))
    assert current_user is not None

    create_notifications_for_user_ids(
        db=db_session,
        user_ids=[current_user.id],
        title="Ticket Baru",
        message="Ada ticket baru untuk Anda.",
        notification_type="TICKET",
        ticket_id="ticket-123",
    )

    response = authenticated_client.get(f"{settings.API_V1_STR}/notifications/unread")

    assert response.status_code == 200
    payload = response.json()
    assert payload["unread_count"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["user_id"] == current_user.id
    assert payload["items"][0]["ticket_id"] == "ticket-123"
    assert payload["items"][0]["is_read"] is False


def test_read_notification_marks_item_as_read(
    authenticated_client: TestClient,
    db_session: Session,
) -> None:
    current_user = db_session.scalar(select(User))
    assert current_user is not None

    create_notifications_for_user_ids(
        db=db_session,
        user_ids=[current_user.id],
        title="Pengingat SLA",
        message="Ticket mendekati SLA.",
        notification_type="SLA",
        ticket_id="ticket-456",
    )

    notification = db_session.scalar(
        select(Notification).where(Notification.user_id == current_user.id)
    )
    assert notification is not None

    response = authenticated_client.post(
        f"{settings.API_V1_STR}/notifications/{notification.id}/read"
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Notification marked as read"}

    db_session.refresh(notification)
    assert notification.is_read is True
