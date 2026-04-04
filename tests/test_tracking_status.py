from sqlalchemy.orm import Session

from app.core.constants import TicketStatus
from app.services.ticket_service import get_public_status_from_internal, track_public_ticket
from app.models.ticket import Ticket


def test_get_public_status_from_internal_accepts_uppercase_values() -> None:
    assert get_public_status_from_internal("RESPONDED") == "Sudah Ditanggapi"
    assert get_public_status_from_internal("IN_PROGRESS") == "Sedang Dikerjakan"
    assert get_public_status_from_internal(" resolved ") == "Sudah Selesai"


def test_track_public_ticket_maps_uppercase_internal_status(db_session: Session) -> None:
    ticket = Ticket(
        ticket_code="TCK-TRACKING-UPPERCASE",
        full_name="Budi Santoso",
        full_address="Jl. Kebon Jeruk No. 12 Jakarta Barat",
        category="Internet",
        description="Koneksi sering terputus sejak pagi hari dan perlu pengecekan.",
        pic_name="Budi",
        phone_number="081234567890",
        internal_status="RESPONDED",
        public_status="Dalam Antrian",
    )
    db_session.add(ticket)
    db_session.commit()

    result = track_public_ticket(
        db=db_session,
        ticket_code=ticket.ticket_code,
        phone_number=ticket.phone_number,
    )

    assert result is not None
    assert result.internal_status == TicketStatus.RESPONDED.value
    assert result.public_status == "Sudah Ditanggapi"
