from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.constants import RoleName
from app.models.user import User
from app.services.report_service import generate_ticket_report_xlsx

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/tickets/export")
def export_ticket_report(
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    technician_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_roles(RoleName.ADMIN.value, RoleName.HEAD.value)
    ),
):
    file_stream = generate_ticket_report_xlsx(
        db=db,
        status=status,
        category=category,
        date_from=date_from,
        date_to=date_to,
        technician_id=technician_id,
    )

    filename = f"ticket-report-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.xlsx"

    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
