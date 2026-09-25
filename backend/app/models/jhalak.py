import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base


class JhalakSnap(AuditMixin, Base):
    """Jhalak pivot (§Jhalak v2): view-once image snaps, Snapchat/Instagram-
    ephemeral style. Every viewer sees a snap exactly once — the server only
    releases the media URL to a viewer whose row in `jhalak_snap_views` does
    not exist yet, and stamps that row the moment it does. The author's own
    snap stays replayable for them for 24h. Screenshots are self-reported and
    surface to the author (mirrors `Snap.screenshot_detected` in chat)."""
    __tablename__ = "jhalak_snaps"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    image_url: Mapped[str] = mapped_column(String(512), nullable=False)
    caption: Mapped[str | None] = mapped_column(String(280), nullable=True)
    filter_key: Mapped[str | None] = mapped_column(String(24), nullable=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class JhalakSnapView(AuditMixin, Base):
    __tablename__ = "jhalak_snap_views"
    __table_args__ = (UniqueConstraint("snap_id", "viewer_id",
                                       name="uq_jhalak_view_once"),)

    snap_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jhalak_snaps.id", ondelete="CASCADE"),
                                               index=True, nullable=False)
    viewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    screenshot_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Reel(AuditMixin, Base):
    __tablename__ = "reels"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    video_url: Mapped[str] = mapped_column(String(512), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    prompt_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("prompts.id"), nullable=True)
    caption: Mapped[str | None] = mapped_column(String(280), nullable=True)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_duet: Mapped[bool] = mapped_column(default=False, nullable=False)
    original_reel_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reels.id"), nullable=True)
    moderation_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)


class ReelLike(AuditMixin, Base):
    __tablename__ = "reel_likes"
    __table_args__ = (UniqueConstraint("reel_id", "user_id", name="uq_reel_like_once"),)

    reel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reels.id"), index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)


class Story(AuditMixin, Base):
    __tablename__ = "stories"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    media_url: Mapped[str] = mapped_column(String(512), nullable=False)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Circle(AuditMixin, Base):
    __tablename__ = "circles"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    memberships = relationship("CircleMembership", back_populates="circle")
    rooms = relationship("LiveAudioRoom", back_populates="circle")


class CircleMembership(AuditMixin, Base):
    __tablename__ = "circle_memberships"
    __table_args__ = (UniqueConstraint("circle_id", "user_id", name="uq_circle_member_once"),)

    circle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("circles.id"), index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="member", nullable=False)

    circle: Mapped[Circle] = relationship(back_populates="memberships")


class LiveAudioRoom(AuditMixin, Base):
    __tablename__ = "live_audio_rooms"

    circle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("circles.id"), index=True, nullable=False)
    host_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="scheduled", nullable=False)

    circle: Mapped[Circle] = relationship(back_populates="rooms")
