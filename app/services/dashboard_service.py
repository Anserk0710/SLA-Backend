from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.constants import TicketStatus
from app.models.ticket import Ticket
from app.services.ticket_service import build_ticket_filtered_query


def get_dashboard_summary(
    db: Session,
    status: str | TicketStatus | None = None,
    category: str | None = None,
    date_from: date | datetime | None = None,
    date_to: date | datetime | None = None,
    technician_id: str | None = None,
) -> dict[str, int]:
    base_query = build_ticket_filtered_query(
        db=db,
        status=status,
        category=category,
        date_from=date_from,
        date_to=date_to,
        technician_id=technician_id,
    )

    return {
        "total_tickets": base_query.count(),
        "belum_direspon": base_query.filter(
            Ticket.internal_status == TicketStatus.NEW.value
        ).count(),
        "sudah_direspon": base_query.filter(
            Ticket.internal_status == TicketStatus.RESPONDED.value
        ).count(),
        "on_progress": base_query.filter(
            Ticket.internal_status.in_(
                [
                    TicketStatus.ASSIGNED.value,
                    TicketStatus.ON_SITE.value,
                    TicketStatus.IN_PROGRESS.value,
                ]
            )
        ).count(),
        "selesai": base_query.filter(
            Ticket.internal_status.in_(
                [
                    TicketStatus.RESOLVED.value,
                    TicketStatus.CLOSED.value,
                ]
            )
        ).count(),
        "sla_breached": base_query.filter(Ticket.is_sla_breached.is_(True)).count(),
    }
