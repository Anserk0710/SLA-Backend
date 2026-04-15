from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    ticket_id: str | None
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime


class NotificationUnreadResponseSchema(BaseModel):
    unread_count: int
    items: list[NotificationItemSchema]
