from uuid import uuid4

from datetime import datetime
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import TicketStatus
from app.db.base_class import Base


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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    assignments = relationship("TicketAssignment", back_populates="ticket", cascade="all, delete-orphan")
    status_logs = relationship("TicketStatusLog", back_populates="ticket", cascade="all, delete-orphan")
