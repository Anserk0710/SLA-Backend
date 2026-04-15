from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.constants import RoleName, TicketStatus
from app.models.role import Role
from app.models.ticket import Ticket
from app.models.ticket_assignment import TicketAssignment
from app.models.user import User


@pytest.fixture()
def authenticated_admin_client(client: TestClient, db_session: Session) -> TestClient:
    current_user = db_session.scalar(select(User))
    assert current_user is not None

    client.app.dependency_overrides[get_current_user] = lambda: current_user
    try:
        yield client
    finally:
        client.app.dependency_overrides.pop(get_current_user, None)


def test_list_tickets_endpoint_supports_phase_five_filters(
    authenticated_admin_client: TestClient,
    db_session: Session,
) -> None:
    technician_role = Role(name=RoleName.TECHNICIAN.value)
    db_session.add(technician_role)
    db_session.flush()

    technician = User(
        full_name="Teknisi Lapangan",
        email="teknisi.filter@example.com",
        hashed_password="hashed-password",
        is_active=True,
        role_id=technician_role.id,
    )
    db_session.add(technician)
    db_session.flush()

    matching_ticket = Ticket(
        ticket_code="TCK-ENDPOINT-001",
        full_name="Andi Pratama",
        full_address="Jl. Melati No. 10",
        category="Internet",
        description="Perlu penanganan jaringan.",
        pic_name="Andi",
        phone_number="081200000001",
        internal_status=TicketStatus.ASSIGNED.value,
        public_status="Sedang Dikerjakan",
        created_at=datetime(2026, 4, 13, 9, 0, 0, tzinfo=timezone.utc),
    )
    other_ticket = Ticket(
        ticket_code="TCK-ENDPOINT-002",
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
        ticket_code="TCK-ENDPOINT-003",
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

    response = authenticated_admin_client.get(
        f"{settings.API_V1_STR}/tickets",
        params={
            "status": TicketStatus.ASSIGNED.value,
            "category": "Internet",
            "date_from": "2026-04-13",
            "date_to": "2026-04-13",
            "technician_id": technician.id,
            "skip": 0,
            "limit": 20,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == matching_ticket.id
    assert payload[0]["assigned_technicians"] == [
        {
            "id": technician.id,
            "full_name": technician.full_name,
            "email": technician.email,
        }
    ]


def test_list_tickets_endpoint_keeps_keyword_search_support(
    authenticated_admin_client: TestClient,
    db_session: Session,
) -> None:
    matching_ticket = Ticket(
        ticket_code="TCK-SEARCH-001",
        full_name="Rina Kartika",
        full_address="Jl. Anggrek No. 1",
        category="Internet",
        description="Perlu penanganan modem.",
        pic_name="Rina",
        phone_number="081200000111",
        internal_status=TicketStatus.NEW.value,
        public_status="Dalam Antrian",
    )
    other_ticket = Ticket(
        ticket_code="TCK-SEARCH-002",
        full_name="Santi Dewi",
        full_address="Jl. Anggrek No. 2",
        category="CCTV",
        description="Perlu pengecekan kamera.",
        pic_name="Santi",
        phone_number="081200000112",
        internal_status=TicketStatus.NEW.value,
        public_status="Dalam Antrian",
    )
    db_session.add_all([matching_ticket, other_ticket])
    db_session.commit()

    response = authenticated_admin_client.get(
        f"{settings.API_V1_STR}/tickets",
        params={"q": "Rina"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == matching_ticket.id
    assert payload[0]["ticket_code"] == matching_ticket.ticket_code
