from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.core.constants import RoleName, TicketStatus
from app.models.role import Role
from app.models.ticket import Ticket
from app.models.ticket_assignment import TicketAssignment
from app.models.user import User
from app.services.ticket_service import build_ticket_filtered_query, get_ticket_list


def test_build_ticket_filtered_query_filters_by_basic_fields(db_session: Session) -> None:
    technician_role = Role(name=RoleName.TECHNICIAN.value)
    db_session.add(technician_role)
    db_session.flush()

    technician = User(
        full_name="Teknisi Lapangan",
        email="teknisi@example.com",
        hashed_password="hashed-password",
        is_active=True,
        role_id=technician_role.id,
    )
    db_session.add(technician)
    db_session.flush()

    matching_ticket = Ticket(
        ticket_code="TCK-FILTER-001",
        full_name="Andi Pratama",
        full_address="Jl. Melati No. 10",
        category="Internet",
        description="Perlu penanganan jaringan.",
        pic_name="Andi",
        phone_number="081200000001",
        internal_status=TicketStatus.ASSIGNED.value,
        public_status="Sedang Dikerjakan",
        sla_deadline=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        is_sla_breached=False,
        created_at=datetime(2026, 4, 13, 9, 0, 0, tzinfo=timezone.utc),
    )
    other_ticket = Ticket(
        ticket_code="TCK-FILTER-002",
        full_name="Beni Saputra",
        full_address="Jl. Kenanga No. 11",
        category="CCTV",
        description="Kategori berbeda.",
        pic_name="Beni",
        phone_number="081200000002",
        internal_status=TicketStatus.ASSIGNED.value,
        public_status="Sedang Dikerjakan",
        created_at=datetime(2026, 4, 13, 10, 0, 0, tzinfo=timezone.utc),
    )
    outside_range_ticket = Ticket(
        ticket_code="TCK-FILTER-003",
        full_name="Citra Lestari",
        full_address="Jl. Mawar No. 12",
        category="Internet",
        description="Tanggal di luar range.",
        pic_name="Citra",
        phone_number="081200000003",
        internal_status=TicketStatus.ASSIGNED.value,
        public_status="Sedang Dikerjakan",
        created_at=datetime(2026, 4, 14, 8, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([matching_ticket, other_ticket, outside_range_ticket])
    db_session.flush()

    db_session.add(
        TicketAssignment(
            ticket_id=matching_ticket.id,
            technician_user_id=technician.id,
        )
    )
    db_session.commit()

    tickets = build_ticket_filtered_query(
        db=db_session,
        status="ASSIGNED",
        category="Internet",
        date_from=date(2026, 4, 13),
        date_to=date(2026, 4, 13),
        technician_id=technician.id,
    ).all()

    db_session.refresh(matching_ticket)

    assert [ticket.id for ticket in tickets] == [matching_ticket.id]
    assert matching_ticket.is_sla_breached is True


def test_get_ticket_list_orders_desc_and_paginates(db_session: Session) -> None:
    oldest_ticket = Ticket(
        ticket_code="TCK-LIST-001",
        full_name="Dian",
        full_address="Jl. A",
        category="Internet",
        description="Oldest ticket.",
        pic_name="Dian",
        phone_number="081200000011",
        internal_status=TicketStatus.NEW.value,
        public_status="Dalam Antrian",
        created_at=datetime(2026, 4, 11, 9, 0, 0, tzinfo=timezone.utc),
    )
    middle_ticket = Ticket(
        ticket_code="TCK-LIST-002",
        full_name="Eka",
        full_address="Jl. B",
        category="Internet",
        description="Middle ticket.",
        pic_name="Eka",
        phone_number="081200000012",
        internal_status=TicketStatus.NEW.value,
        public_status="Dalam Antrian",
        created_at=datetime(2026, 4, 12, 9, 0, 0, tzinfo=timezone.utc),
    )
    newest_ticket = Ticket(
        ticket_code="TCK-LIST-003",
        full_name="Fajar",
        full_address="Jl. C",
        category="Internet",
        description="Newest ticket.",
        pic_name="Fajar",
        phone_number="081200000013",
        internal_status=TicketStatus.NEW.value,
        public_status="Dalam Antrian",
        created_at=datetime(2026, 4, 13, 9, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([oldest_ticket, middle_ticket, newest_ticket])
    db_session.commit()

    tickets = get_ticket_list(
        db=db_session,
        status=TicketStatus.NEW,
        skip=1,
        limit=1,
    )

    assert len(tickets) == 1
    assert tickets[0].id == middle_ticket.id
