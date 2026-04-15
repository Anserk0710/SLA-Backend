from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import TicketStatus, coerce_ticket_status
from app.models.sla_policy import SLAPolicy
from app.models.ticket import Ticket

FINAL_SLA_STATUSES = frozenset(
    {
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED,
        TicketStatus.REJECTED,
    }
)


def get_now_utc() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def get_sla_policy_by_category(db: Session, category: str | None) -> SLAPolicy | None:
    normalized_category = (category or "").strip()
    if not normalized_category:
        return None

    stmt = select(SLAPolicy).where(
        func.lower(SLAPolicy.category) == normalized_category.lower(),
        SLAPolicy.is_active.is_(True),
    )
    return db.scalar(stmt)


def calculate_sla_deadline(
    db: Session,
    category: str,
    created_at: datetime | None = None,
) -> datetime | None:
    policy = get_sla_policy_by_category(db, category)
    if policy is None:
        return None

    base_time = ensure_utc_datetime(created_at or get_now_utc())
    return base_time + timedelta(hours=policy.hours_target)


def ticket_stops_sla_tracking(status: str | TicketStatus | None) -> bool:
    normalized_status = coerce_ticket_status(status) if status is not None else None
    return normalized_status in FINAL_SLA_STATUSES


def has_ticket_breached_sla(
    ticket: Ticket,
    reference_time: datetime | None = None,
) -> bool:
    if ticket.sla_deadline is None:
        return False

    if ticket.is_sla_breached:
        return True

    if ticket_stops_sla_tracking(ticket.internal_status):
        return False

    now = ensure_utc_datetime(reference_time or get_now_utc())
    deadline = ensure_utc_datetime(ticket.sla_deadline)
    return deadline <= now


def refresh_ticket_sla_state(
    ticket: Ticket,
    reference_time: datetime | None = None,
) -> bool:
    is_sla_breached = has_ticket_breached_sla(ticket, reference_time)
    ticket.is_sla_breached = is_sla_breached
    return is_sla_breached


def sync_sla_breaches(db: Session) -> int:
    now = get_now_utc()

    stmt = select(Ticket).where(
        Ticket.sla_deadline.is_not(None),
        Ticket.is_sla_breached.is_(False),
    )
    tickets = db.scalars(stmt).all()

    updated_count = 0
    for ticket in tickets:
        if refresh_ticket_sla_state(ticket, now):
            updated_count += 1

    if updated_count:
        db.commit()

    return updated_count
