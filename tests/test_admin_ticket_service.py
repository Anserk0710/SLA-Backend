from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import RoleName, TicketStatus
from app.models.notification import Notification
from app.models.role import Role
from app.models.ticket import Ticket
from app.models.user import User
from app.services.admin_ticket_service import assign_ticket_technicians


def test_assign_ticket_technicians_creates_notifications_for_assigned_technicians(
    db_session: Session,
) -> None:
    technician_role = Role(name=RoleName.TECHNICIAN.value)
    db_session.add(technician_role)
    db_session.flush()

    technician_one = User(
        full_name="Teknisi Satu",
        email="teknisi1@example.com",
        hashed_password="hashed-password",
        is_active=True,
        role_id=technician_role.id,
    )
    technician_two = User(
        full_name="Teknisi Dua",
        email="teknisi2@example.com",
        hashed_password="hashed-password",
        is_active=True,
        role_id=technician_role.id,
    )
    ticket = Ticket(
        ticket_code="TCK-ASSIGN-001",
        full_name="Andi Pratama",
        full_address="Jl. Melati No. 10 Jakarta Barat",
        category="Internet",
        description="Perlu penanganan jaringan.",
        pic_name="Andi",
        phone_number="081200000001",
        internal_status=TicketStatus.RESPONDED.value,
        public_status="Sudah Ditanggapi",
    )
    admin_user = db_session.scalar(select(User))

    assert admin_user is not None

    db_session.add_all([technician_one, technician_two, ticket])
    db_session.commit()

    assign_ticket_technicians(
        db=db_session,
        ticket_id=ticket.id,
        technician_user_ids=[technician_one.id, technician_two.id],
        current_user=admin_user,
    )

    notifications = db_session.scalars(
        select(Notification).where(Notification.ticket_id == ticket.id)
    ).all()

    assert len(notifications) == 2
    assert {notification.user_id for notification in notifications} == {
        technician_one.id,
        technician_two.id,
    }
    assert all(notification.type == "TICKET" for notification in notifications)
    assert all(notification.is_read is False for notification in notifications)
    assert all(ticket.ticket_code in notification.message for notification in notifications)
