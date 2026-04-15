from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import RoleName
from app.core.security import get_password_hash
from app.models.notification import Notification
from app.models.role import Role
from app.models.user import User


def test_create_ticket_endpoint_creates_notifications_for_admin_and_head(
    client: TestClient,
    db_session: Session,
) -> None:
    head_role = Role(name=RoleName.HEAD.value)
    db_session.add(head_role)
    db_session.flush()
    db_session.add(
        User(
            full_name="Head User",
            email="head@example.com",
            hashed_password=get_password_hash("head123"),
            is_active=True,
            role_id=head_role.id,
        )
    )
    db_session.commit()

    response = client.post(
        f"{settings.API_V1_STR}/public/tickets",
        json={
            "full_name": "Rahmat Hidayat",
            "full_address": "Jl. Anggrek No. 99 Bandung",
            "category": "Critical",
            "description": "Layanan tidak bisa diakses sejak pagi dan perlu ditindaklanjuti.",
            "pic_name": "Rahmat",
            "phone_number": "081234567899",
        },
    )

    assert response.status_code == 201
    ticket_code = response.json()["ticket_code"]

    notifications = db_session.scalars(select(Notification)).all()

    assert len(notifications) == 2
    assert all(notification.type == "TICKET" for notification in notifications)
    assert all(notification.ticket_id is not None for notification in notifications)
    assert all(notification.is_read is False for notification in notifications)
    assert all(ticket_code in notification.message for notification in notifications)
