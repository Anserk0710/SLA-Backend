from datetime import date, datetime, time

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.constants import PUBLIC_STATUS_MAP, TicketStatus, coerce_ticket_status
from app.models.ticket import Ticket
from app.models.ticket_assignment import TicketAssignment
from app.models.ticket_status_log import TicketStatusLog
from app.schemas.ticket import PublicTicketCreate
from app.services.sla_service import (
    calculate_sla_deadline,
    refresh_ticket_sla_state,
    sync_sla_breaches,
)
from app.utils.phone import normalize_phone_number
from app.utils.ticket_code import generate_ticket_code


def get_public_status_from_internal(internal_status: str | TicketStatus) -> str:
    status_key = coerce_ticket_status(internal_status)
    if status_key is None:
        return "Dalam Antrian"

    return PUBLIC_STATUS_MAP.get(status_key, "Dalam Antrian")


def generate_unique_ticket_code(db: Session) -> str:
    while True:
        code = generate_ticket_code()
        existing = db.scalar(select(Ticket).where(Ticket.ticket_code == code))
        if not existing:
            return code


def _coerce_datetime_boundary(value: date | datetime, boundary: time) -> datetime:
    if isinstance(value, datetime):
        return value

    return datetime.combine(value, boundary)


def build_ticket_filtered_query(
    db: Session,
    status: str | TicketStatus | None = None,
    category: str | None = None,
    date_from: date | datetime | None = None,
    date_to: date | datetime | None = None,
    technician_id: str | None = None,
    q: str | None = None,
):
    sync_sla_breaches(db)

    query = db.query(Ticket).options(
        selectinload(Ticket.assignments).selectinload(TicketAssignment.technician)
    )

    normalized_technician_id = technician_id.strip() if technician_id else None
    if normalized_technician_id:
        query = query.join(
            TicketAssignment,
            TicketAssignment.ticket_id == Ticket.id,
        ).filter(TicketAssignment.technician_user_id == normalized_technician_id)

    normalized_status = coerce_ticket_status(status) if status else None
    status_value = normalized_status.value if normalized_status is not None else None
    if status_value is None and isinstance(status, str):
        status_value = status.strip() or None
    if status_value:
        query = query.filter(Ticket.internal_status == status_value)

    normalized_category = category.strip() if category else None
    if normalized_category:
        query = query.filter(Ticket.category == normalized_category)

    normalized_query = q.strip() if q else None
    if normalized_query:
        keyword = f"%{normalized_query}%"
        query = query.filter(
            or_(
                Ticket.ticket_code.ilike(keyword),
                Ticket.full_name.ilike(keyword),
                Ticket.category.ilike(keyword),
                Ticket.item_name.ilike(keyword),
                Ticket.pic_name.ilike(keyword),
            )
        )

    if date_from is not None:
        query = query.filter(
            Ticket.created_at >= _coerce_datetime_boundary(date_from, time.min)
        )

    if date_to is not None:
        query = query.filter(
            Ticket.created_at <= _coerce_datetime_boundary(date_to, time.max)
        )

    return query.distinct()


def get_ticket_list(
    db: Session,
    status: str | TicketStatus | None = None,
    category: str | None = None,
    date_from: date | datetime | None = None,
    date_to: date | datetime | None = None,
    technician_id: str | None = None,
    q: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Ticket]:
    query = build_ticket_filtered_query(
        db=db,
        status=status,
        category=category,
        date_from=date_from,
        date_to=date_to,
        technician_id=technician_id,
        q=q,
    )

    return query.order_by(Ticket.created_at.desc()).offset(skip).limit(limit).all()


def create_public_ticket(db: Session, payload: PublicTicketCreate) -> Ticket:
    ticket_code = generate_unique_ticket_code(db)
    initial_status = TicketStatus.NEW
    public_status = get_public_status_from_internal(initial_status)
    category = payload.category.strip()

    ticket = Ticket(
        ticket_code=ticket_code,
        full_name=payload.full_name.strip(),
        full_address=payload.full_address.strip(),
        category=category,
        item_name=payload.item_name.strip(),
        description=payload.description.strip(),
        pic_name=payload.pic_name.strip(),
        phone_number=normalize_phone_number(payload.phone_number),
        internal_status=initial_status.value,
        public_status=public_status,
        is_sla_breached=False,
    )

    db.add(ticket)
    db.flush()
    db.refresh(ticket)

    ticket.sla_deadline = calculate_sla_deadline(
        db=db,
        category=category,
        created_at=ticket.created_at,
    )

    status_log = TicketStatusLog(
        ticket_id=ticket.id,
        old_status=None,
        new_status=initial_status.value,
        notes="Ticket dibuat melalui layanan publik",
        changed_by=None,
    )
    db.add(status_log)
    db.commit()
    db.refresh(ticket)

    return ticket


def track_public_ticket(db: Session, ticket_code: str, phone_number: str) -> Ticket | None:
    normalized_ticket_code = ticket_code.strip().upper()
    normalized_phone_number = normalize_phone_number(phone_number.strip())

    ticket = db.scalar(
        select(Ticket).where(
            Ticket.ticket_code == normalized_ticket_code,
            Ticket.phone_number == normalized_phone_number,
        )
    )

    if ticket is None:
        return None

    normalized_status = coerce_ticket_status(ticket.internal_status)
    if normalized_status is not None:
        ticket.internal_status = normalized_status.value

    ticket.public_status = get_public_status_from_internal(ticket.internal_status)
    refresh_ticket_sla_state(ticket)
    return ticket
