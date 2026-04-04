from enum import Enum

class RoleName(str, Enum):
    ADMIN = "admin"
    HEAD = "head"
    TECHNICIAN = "technician"

class TicketStatus(str, Enum):
    NEW = "new"
    RESPONDED = "responded"
    ASSIGNED = "assigned"
    ON_SITE = "on_site"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REJECTED = "rejected"


def coerce_ticket_status(value: str | TicketStatus) -> TicketStatus | None:
    if isinstance(value, TicketStatus):
        return value

    if not isinstance(value, str):
        return None

    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    if not normalized:
        return None

    try:
        return TicketStatus(normalized)
    except ValueError:
        return None

PUBLIC_STATUS_MAP = {
    TicketStatus.NEW: "Dalam Antrian",
    TicketStatus.RESPONDED: "Sudah Ditanggapi",
    TicketStatus.ASSIGNED: "Sedang Dikerjakan",
    TicketStatus.ON_SITE: "Sedang Dikerjakan",
    TicketStatus.IN_PROGRESS: "Sedang Dikerjakan",
    TicketStatus.RESOLVED: "Sudah Selesai",
    TicketStatus.CLOSED: "Sudah Selesai",
    TicketStatus.REJECTED: "Ditolak",
}
