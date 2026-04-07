from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

class TicketCheckIn(Base):
    __tablename__ = "ticket_checkin"
    __table_args__= (
        UniqueConstraint("ticket_id", "technician_user_id", name="uq_ticket_checkin_ticket_technician"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    ticket_id: Mapped[str] = mapped_column(String(36), ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    technician_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)

    photo_public_id: Mapped[str] = mapped_column(String(255))
    photo_secure_url: Mapped[str] = mapped_column(Text)
    photo_resource_type: Mapped[str] = mapped_column(String(50), default="image")
    photo_format: Mapped[str | None] = mapped_column(String(50), nullable=True)
    photo_bytes: Mapped[int] = mapped_column(Integer)
    photo_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    photo_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)

    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    address: Mapped[str] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    server_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    ticket = relationship("Ticket", back_populates="checkins")
    technician = relationship("User", foreign_keys=[technician_user_id])