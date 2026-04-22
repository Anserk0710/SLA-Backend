from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.constants import RoleName
from app.core.permissions import require_roles
from app.models.user import User
from app.schemas.admin_ticket import TechnicianOption
from app.services.admin_ticket_service import list_technicians

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/technicians", response_model=list[TechnicianOption])
def get_technicians(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value, RoleName.HEAD.value)),

):
    return list_technicians(db)
