from datetime import date, datetime
from io import BytesIO

from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.services.ticket_service import build_ticket_filtered_query


def generate_ticket_report_xlsx(
    db: Session,
    status: str | None = None,
    category: str | None = None,
    date_from: date | datetime | None = None,
    date_to: date | datetime | None = None,
    technician_id: str | None = None,
) -> BytesIO:
    query = build_ticket_filtered_query(
        db=db,
        status=status,
        category=category,
        date_from=date_from,
        date_to=date_to,
        technician_id=technician_id,
    )

    tickets = query.order_by().all()

    workbook = Workbook()
    default_sheet = workbook.active
    if default_sheet is not None:
        workbook.remove(default_sheet)

    sheet = workbook.create_sheet(title="Tickets Report")

    sheet.append(
        [
            "ID",
            "Ticket Code",
            "Category",
            "Status",
            "SLA Deadline",
            "SLA Breached",
            "Created At",
        ]
    )

    for ticket in tickets:
        sheet.append(
            [
                ticket.id,
                ticket.ticket_code,
                ticket.category,
                ticket.internal_status,
                ticket.sla_deadline.isoformat() if ticket.sla_deadline else "",
                "YES" if ticket.is_sla_breached else "NO",
                ticket.created_at.isoformat() if ticket.created_at else "",
            ]
        )

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    workbook.close()

    return output
