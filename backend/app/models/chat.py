import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base


class Message(AuditMixin, Base):
    __tablename__ = "messages"

    match_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matches.id"), index=True, nullable=False)
    sender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # image | gif | audio — chat never carries video (product rule). Drives the
    # renderer choice on the client: a voice note must not render as a picture.
    media_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Voice-note length so the player can draw its waveform before loading.
    media_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_ai_suggested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    match: Mapped["Match"] = relationship(back_populates="messages")


class Snap(AuditMixin, Base):
    __tablename__ = "snaps"

    match_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matches.id"), index=True, nullable=False)
    sender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    media_url: Mapped[str] = mapped_column(String(512), nullable=False)
    view_mode: Mapped[str] = mapped_column(String(16), default="single_view", nullable=False)
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    screenshot_detected: Mapped[bool] = mapped_column(default=False, nullable=False)
