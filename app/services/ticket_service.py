from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import PUBLIC_STATUS_MAP, TicketStatus, coerce_ticket_status
from app.models.ticket import Ticket
from app.models.ticket_status_log import TicketStatusLog
from app.schemas.ticket import PublicTicketCreate
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

def create_public_ticket(db: Session, payload: PublicTicketCreate) -> Ticket:
    ticket_code = generate_unique_ticket_code(db)
    initial_status = TicketStatus.NEW
    public_status = get_public_status_from_internal(initial_status)

    ticket = Ticket(
        ticket_code=ticket_code,
        full_name=payload.full_name.strip(),
        full_address=payload.full_address.strip(),
        category=payload.category.strip(),
        description=payload.description.strip(),
        pic_name=payload.pic_name.strip(),
        phone_number=normalize_phone_number(payload.phone_number),
        internal_status=initial_status.value,
        public_status=public_status
    )

    db.add(ticket)
    db.flush()

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
    return ticket
