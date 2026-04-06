from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.constants import RoleName
from app.models.user import User
from app.schemas.admin_ticket import DashboardSummaryResponse
from app.services.admin_ticket_service import get_dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value, RoleName.HEAD.value)),

):
    return get_dashboard_summary(db)