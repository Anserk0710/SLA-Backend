from datetime import datetime, timezone

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.constants import RoleName, TicketStatus
from app.models.role import Role
from app.models.ticket import Ticket
from app.models.ticket_assignment import TicketAssignment
from app.models.ticket_status_log import TicketStatusLog
from app.models.user import User
from app.services.ticket_service import get_public_status_from_internal


def create_status_log(
    db: Session,
    *,
    ticket_id: str,
    old_status: str | None,
    new_status: str,
    notes: str | None,
    changed_by_user_id: str | None,
) -> None:
    db.add(
        TicketStatusLog(
            ticket_id=ticket_id,
            old_status=old_status,
            new_status=new_status,
            notes=notes,
            changed_by_user_id=changed_by_user_id,
        )
    )


def serialize_assigned_technicians(ticket: Ticket) -> list[dict]:
    result: list[dict] = []

    for assignment in ticket.assignments:
        if assignment.technician:
            result.append(
                {
                    "id": assignment.technician.id,
                    "full_name": assignment.technician.full_name,
                    "email": assignment.technician.email,
                }
            )

    return result


def serialize_status_logs(ticket: Ticket) -> list[dict]:
    logs = sorted(ticket.status_logs, key=lambda item: item.changed_at, reverse=True)

    result: list[dict] = []
    for log in logs:
        result.append(
            {
                "id": log.id,
                "old_status": log.old_status,
                "new_status": log.new_status,
                "notes": log.notes,
                "changed_by_name": log.changed_by.full_name if log.changed_by else None,
                "created_at": log.changed_at,
            }
        )

    return result


def serialize_ticket_list_item(ticket: Ticket) -> dict:
    return {
        "id": ticket.id,
        "ticket_code": ticket.ticket_code,
        "full_name": ticket.full_name,
        "category": ticket.category,
        "pic_name": ticket.pic_name,
        "phone_number": ticket.phone_number,
        "internal_status": ticket.internal_status,
        "public_status": ticket.public_status,
        "created_at": ticket.created_at,
        "assigned_technicians": serialize_assigned_technicians(ticket),
    }


def serialize_ticket_detail(ticket: Ticket) -> dict:
    data = serialize_ticket_list_item(ticket)
    data.update(
        {
            "full_address": ticket.full_address,
            "description": ticket.description,
            "inital_respons": ticket.intial_respons,
            "responded_at": ticket.responded_at,
            "responded_by_name": ticket.responded_by.full_name if ticket.responded_by else None,
            "status_logs": serialize_status_logs(ticket),
        }
    )
    return data


def get_dashboard_summary(db: Session) -> dict:
    rows = db.execute(
        select(Ticket.internal_status, func.count(Ticket.id)).group_by(Ticket.internal_status)
    ).all()

    counts = {status: count for status, count in rows}

    total_tickets = sum(counts.values())
    belum_direspon = counts.get(TicketStatus.NEW.value, 0)
    sudah_direspon = counts.get(TicketStatus.RESPONDED.value, 0)
    on_progress = (
        counts.get(TicketStatus.ASSIGNED.value, 0)
        + counts.get(TicketStatus.ON_SITE.value, 0)
        + counts.get(TicketStatus.IN_PROGRESS.value, 0)
    )
    selesai = counts.get(TicketStatus.RESOLVED.value, 0) + counts.get(
        TicketStatus.CLOSED.value, 0
    )

    return {
        "total_tickets": total_tickets,
        "belum_direspon": belum_direspon,
        "sudah_direspon": sudah_direspon,
        "on_progress": on_progress,
        "selesai": selesai,
    }


def list_tickets(db: Session, status: str | None = None, q: str | None = None) -> list[dict]:
    stmt = (
        select(Ticket)
        .options(
            selectinload(Ticket.assignments).selectinload(TicketAssignment.technician)
        )
        .order_by(Ticket.created_at.desc())
    )

    if status:
        stmt = stmt.where(Ticket.internal_status == status)

    if q and q.strip():
        keyword = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Ticket.ticket_code.ilike(keyword),
                Ticket.full_name.ilike(keyword),
                Ticket.category.ilike(keyword),
                Ticket.pic_name.ilike(keyword),
            )
        )

    tickets = db.scalars(stmt).unique().all()
    return [serialize_ticket_list_item(ticket) for ticket in tickets]


def get_ticket_detail(db: Session, ticket_id: str) -> dict | None:
    stmt = (
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .options(
            selectinload(Ticket.assignments).selectinload(TicketAssignment.technician),
            selectinload(Ticket.status_logs).selectinload(TicketStatusLog.changed_by),
            selectinload(Ticket.responded_by),
        )
    )

    ticket = db.scalar(stmt)
    if ticket is None:
        return None

    return serialize_ticket_detail(ticket)


def respond_ticket(
    db: Session,
    *,
    ticket_id: str,
    response_note: str,
    current_user: User,
) -> None:
    ticket = db.scalar(select(Ticket).where(Ticket.id == ticket_id))

    if ticket is None:
        raise ValueError("Ticket tidak ditemukan")

    if ticket.internal_status not in {TicketStatus.NEW.value, TicketStatus.RESPONDED.value}:
        raise ValueError("Ticket hanya bisa direspon saat status NEW atau RESPONDED")

    old_status = ticket.internal_status
    new_status = TicketStatus.RESPONDED.value

    ticket.intial_respons = response_note.strip()
    ticket.responded_by_user_id = current_user.id
    ticket.responded_at = datetime.now(timezone.utc)
    ticket.internal_status = new_status
    ticket.public_status = get_public_status_from_internal(new_status)

    create_status_log(
        db,
        ticket_id=ticket.id,
        old_status=old_status,
        new_status=new_status,
        notes=f"Respon awal: {response_note.strip()}",
        changed_by_user_id=current_user.id,
    )

    db.commit()


def list_technicians(db: Session) -> list[dict]:
    stmt = (
        select(User)
        .join(Role, User.role_id == Role.id)
        .where(
            Role.name == RoleName.TECHNICIAN.value,
            User.is_active.is_(True),
        )
        .order_by(User.full_name.asc())
    )

    users = db.scalars(stmt).all()

    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
        }
        for user in users
    ]


def assign_ticket_technicians(
    db: Session,
    *,
    ticket_id: str,
    technician_user_ids: list[str],
    current_user: User,
) -> None:
    stmt = (
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .options(selectinload(Ticket.assignments))
    )
    ticket = db.scalar(stmt)

    if ticket is None:
        raise ValueError("Ticket tidak ditemukan")

    if ticket.internal_status in {
        TicketStatus.RESOLVED.value,
        TicketStatus.CLOSED.value,
        TicketStatus.REJECTED.value,
    }:
        raise ValueError("Ticket sudah final dan tidak bisa di-assign lagi")

    if ticket.internal_status in {
        TicketStatus.ON_SITE.value,
        TicketStatus.IN_PROGRESS.value,
    }:
        raise ValueError("Ticket sudah masuk tahap eksekusi dan tidak bisa di-assign ulang dari flow ini")

    technician_stmt = (
        select(User)
        .join(Role, User.role_id == Role.id)
        .where(
            User.id.in_(technician_user_ids),
            Role.name == RoleName.TECHNICIAN.value,
            User.is_active.is_(True),
        )
        .order_by(User.full_name.asc())
    )
    technicians = db.scalars(technician_stmt).all()

    if len(technicians) != len(technician_user_ids):
        raise ValueError("Ada technician yang tidak valid atau tidak aktif")

    old_status = ticket.internal_status
    new_status = TicketStatus.ASSIGNED.value

    db.execute(delete(TicketAssignment).where(TicketAssignment.ticket_id == ticket.id))

    for technician in technicians:
        db.add(
            TicketAssignment(
                ticket_id=ticket.id,
                technician_user_id=technician.id,
                assigned_by_user_id=current_user.id,
            )
        )

    ticket.internal_status = new_status
    ticket.public_status = get_public_status_from_internal(new_status)

    technician_names = ", ".join([technician.full_name for technician in technicians])

    create_status_log(
        db,
        ticket_id=ticket.id,
        old_status=old_status,
        new_status=new_status,
        notes=f"Assigned technician: {technician_names}",
        changed_by_user_id=current_user.id,
    )

    db.commit()
