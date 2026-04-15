from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from typing import TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import TicketStatus
from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.ticket_assignment import TicketAssignment
    from app.models.ticket_checkin import TicketCheckIn
    from app.models.ticket_resolution import TicketResolution
    from app.models.ticket_status_log import TicketStatusLog
    from app.models.user import User


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    ticket_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    full_name: Mapped[str] = mapped_column(String(150))
    full_address: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str] = mapped_column(Text)
    pic_name: Mapped[str] = mapped_column(String(150))
    phone_number: Mapped[str] = mapped_column(String(30), index=True)

    internal_status: Mapped[str] = mapped_column(String(50), default=TicketStatus.NEW.value, index=True)
    public_status: Mapped[str] = mapped_column(String(50), default="Dalam Antrian")
    intial_respons: Mapped[str | None] = mapped_column(Text, nullable=True)
    sla_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    is_sla_breached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    responded_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    assignments: Mapped[list[TicketAssignment]] = relationship(
        "TicketAssignment",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
    checkins: Mapped[list[TicketCheckIn]] = relationship(
        "TicketCheckIn",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
    resolution: Mapped[list[TicketResolution]] = relationship(
        "TicketResolution",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
    status_logs: Mapped[list[TicketStatusLog]] = relationship(
        "TicketStatusLog",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
    responded_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[responded_by_user_id],
    )
