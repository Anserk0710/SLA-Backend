from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.core.permissions import ensure_dashboard_permission
from app.models.user import User
from app.schemas.admin_ticket import DashboardSummaryResponse
from app.services.dashboard_service import get_dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    technician_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    ensure_dashboard_permission(current_user)

    return get_dashboard_summary(
        db=db,
        status=status,
        category=category,
        date_from=date_from,
        date_to=date_to,
        technician_id=technician_id,
    )
