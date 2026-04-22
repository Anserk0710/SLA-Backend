from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.notification import NotificationUnreadResponseSchema
from app.services.notification_service import (
    count_unread_notifications,
    get_unread_notifications,
    mark_notification_as_read,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/unread", response_model=NotificationUnreadResponseSchema)
def unread_notifications(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items = get_unread_notifications(db=db, user_id=current_user.id, limit=limit)
    unread_count = count_unread_notifications(db=db, user_id=current_user.id)

    return {
        "unread_count": unread_count,
        "items": items,
    }


@router.post("/{notification_id}/read")
def read_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, str]:
    notification = mark_notification_as_read(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id,
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"message": "Notification marked as read"}
