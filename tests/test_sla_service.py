from datetime import datetime, timezone

import app.services.ticket_service as ticket_service
from sqlalchemy.orm import Session

from app.core.constants import TicketStatus
from app.models.sla_policy import SLAPolicy
from app.models.ticket import Ticket
from app.schemas.ticket import PublicTicketCreate
from app.services.sla_service import calculate_sla_deadline, sync_sla_breaches


def test_calculate_sla_deadline_matches_active_policy(db_session: Session) -> None:
    db_session.add(
        SLAPolicy(
            category="High",
            hours_target=4,
            is_active=True,
        )
    )
    db_session.commit()

    created_at = datetime(2026, 4, 13, 8, 0, 0)

    deadline = calculate_sla_deadline(db_session, " high ", created_at)

    assert deadline == datetime(2026, 4, 13, 12, 0, 0, tzinfo=timezone.utc)


def test_sync_sla_breaches_marks_only_overdue_non_final_tickets(db_session: Session) -> None:
    overdue_ticket = Ticket(
        ticket_code="TCK-SLA-OVERDUE",
        full_name="Budi Santoso",
        full_address="Jl. Melati No. 15 Jakarta Selatan",
        category="High",
        description="Gangguan koneksi membutuhkan pengecekan teknis segera.",
        pic_name="Budi",
        phone_number="081234567890",
        internal_status=TicketStatus.ASSIGNED.value,
        public_status="Sedang Dikerjakan",
        sla_deadline=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        is_sla_breached=False,
    )
    final_ticket = Ticket(
        ticket_code="TCK-SLA-FINAL",
        full_name="Siti Aminah",
        full_address="Jl. Mawar No. 8 Jakarta Timur",
        category="High",
        description="Perlu verifikasi bahwa ticket final tidak ikut ditandai breach.",
        pic_name="Siti",
        phone_number="081298765432",
        internal_status="CLOSED",
        public_status="Sudah Selesai",
        sla_deadline=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        is_sla_breached=False,
    )
    db_session.add_all([overdue_ticket, final_ticket])
    db_session.commit()

    updated_count = sync_sla_breaches(db_session)

    db_session.refresh(overdue_ticket)
    db_session.refresh(final_ticket)

    assert updated_count == 1
    assert overdue_ticket.is_sla_breached is True
    assert final_ticket.is_sla_breached is False


def test_create_public_ticket_assigns_sla_deadline(db_session: Session, monkeypatch) -> None:
    expected_deadline = datetime(2026, 4, 13, 14, 0, 0, tzinfo=timezone.utc)
    captured_call: dict[str, datetime | str | None] = {}

    def fake_calculate_sla_deadline(
        db: Session,
        category: str,
        created_at: datetime | None = None,
    ) -> datetime:
        captured_call["category"] = category
        captured_call["created_at"] = created_at
        return expected_deadline

    monkeypatch.setattr(ticket_service, "calculate_sla_deadline", fake_calculate_sla_deadline)

    payload = PublicTicketCreate(
        full_name="Rahmat Hidayat",
        full_address="Jl. Anggrek No. 99 Bandung",
        category="Critical",
        description="Layanan tidak bisa diakses sejak pagi dan perlu ditindaklanjuti.",
        pic_name="Rahmat",
        phone_number="081234567899",
    )

    ticket = ticket_service.create_public_ticket(db_session, payload)

    assert ticket.sla_deadline is not None
    assert ticket.sla_deadline.replace(tzinfo=timezone.utc) == expected_deadline
    assert captured_call["category"] == "Critical"
    assert captured_call["created_at"] == ticket.created_at
    assert ticket.is_sla_breached is False
