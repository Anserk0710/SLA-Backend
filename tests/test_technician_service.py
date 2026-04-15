from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import RoleName, TicketStatus
from app.models.notification import Notification
from app.models.role import Role
from app.models.ticket import Ticket
from app.models.ticket_assignment import TicketAssignment
from app.models.ticket_checkin import TicketCheckIn
from app.models.user import User
from app.services.technician_service import submit_resolution


def test_submit_resolution_creates_notifications_for_admin_and_head(
    db_session: Session,
) -> None:
    admin_user = db_session.scalar(select(User))

    assert admin_user is not None

    technician_role = Role(name=RoleName.TECHNICIAN.value)
    head_role = Role(name=RoleName.HEAD.value)
    db_session.add_all([technician_role, head_role])
    db_session.flush()

    technician = User(
        full_name="Teknisi Lapangan",
        email="teknisi@example.com",
        hashed_password="hashed-password",
        is_active=True,
        role_id=technician_role.id,
    )
    head_user = User(
        full_name="Head User",
        email="head@example.com",
        hashed_password="hashed-password",
        is_active=True,
        role_id=head_role.id,
    )
    ticket = Ticket(
        ticket_code="TCK-RESOLVE-001",
        full_name="Budi Santoso",
        full_address="Jl. Kenanga No. 7 Jakarta Selatan",
        category="Internet",
        description="Perlu penyelesaian di lokasi.",
        pic_name="Budi",
        phone_number="081200000111",
        internal_status=TicketStatus.ON_SITE.value,
        public_status="Sedang Dikerjakan",
    )
    db_session.add_all([technician, head_user, ticket])
    db_session.flush()

    db_session.add(
        TicketAssignment(
            ticket_id=ticket.id,
            technician_user_id=technician.id,
        )
    )
    db_session.add(
        TicketCheckIn(
            ticket_id=ticket.id,
            technician_user_id=technician.id,
            photo_public_id="photo-public-id",
            photo_secure_url="https://example.com/photo.jpg",
            photo_resource_type="image",
            photo_format="jpg",
            photo_bytes=12345,
            photo_width=1080,
            photo_height=720,
            original_filename="checkin.jpg",
            latitude=-6.2,
            longitude=106.8,
            address="Jl. Kenanga No. 7 Jakarta Selatan",
            notes="Sudah tiba di lokasi",
            server_timestamp=datetime(2026, 4, 13, 8, 0, 0, tzinfo=timezone.utc),
        )
    )
    db_session.commit()

    submit_resolution(
        db=db_session,
        ticket_id=ticket.id,
        current_user=technician,
        latitude=-6.2,
        longitude=106.8,
        address="Jl. Kenanga No. 7 Jakarta Selatan",
        resolution_note="Masalah selesai ditangani.",
        upload_result={
            "public_id": "video-public-id",
            "secure_url": "https://example.com/video.mp4",
            "resource_type": "video",
            "format": "mp4",
            "bytes": 45678,
            "width": 1920,
            "height": 1080,
            "duration": 12.5,
        },
        original_filename="resolution.mp4",
    )

    notifications = db_session.scalars(
        select(Notification).where(Notification.ticket_id == ticket.id)
    ).all()
    assert len(notifications) == 2
    assert {notification.user_id for notification in notifications} == {
        admin_user.id,
        head_user.id,
    }
    assert all(notification.type == "TICKET" for notification in notifications)
    assert all(notification.is_read is False for notification in notifications)
    assert all(ticket.ticket_code in notification.message for notification in notifications)
