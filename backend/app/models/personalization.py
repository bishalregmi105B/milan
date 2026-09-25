import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base


class ChatTheme(AuditMixin, Base):
    __tablename__ = "chat_themes"
    __table_args__ = (
        UniqueConstraint("user_id", "scope", "scope_id", name="uq_chat_theme_user_scope"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    scope: Mapped[str] = mapped_column(String(16), default="global", nullable=False)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    wallpaper_type: Mapped[str] = mapped_column(String(16), nullable=False)
    wallpaper_value: Mapped[str] = mapped_column(String(512), nullable=False)
    bubble_color_sent: Mapped[str | None] = mapped_column(String(9), nullable=True)
    bubble_color_received: Mapped[str | None] = mapped_column(String(9), nullable=True)
    bubble_shape: Mapped[str | None] = mapped_column(String(16), nullable=True)
    doodle_overlay_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("doodle_overlays.id"), nullable=True)
    text_scale: Mapped[float | None] = mapped_column(Float, nullable=True)
    dark_mode_brightness: Mapped[float | None] = mapped_column(Float, nullable=True)


class ChatThemePreset(AuditMixin, Base):
    __tablename__ = "chat_theme_presets"

    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    pack: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    wallpaper_type: Mapped[str] = mapped_column(String(16), nullable=False)
    wallpaper_value: Mapped[str] = mapped_column(String(512), nullable=False)
    wallpaper_value_dark: Mapped[str | None] = mapped_column(String(512), nullable=True)
    bubble_color_sent: Mapped[str] = mapped_column(String(9), nullable=False)
    bubble_color_received: Mapped[str] = mapped_column(String(9), nullable=False)
    bubble_shape: Mapped[str] = mapped_column(String(16), default="rounded", nullable=False)
    doodle_overlay_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("doodle_overlays.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class DoodleOverlay(AuditMixin, Base):
    __tablename__ = "doodle_overlays"

    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    asset_url: Mapped[str] = mapped_column(String(512), nullable=False)
    opacity: Mapped[float] = mapped_column(Float, default=0.08, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class WallpaperUpload(AuditMixin, Base):
    __tablename__ = "wallpaper_uploads"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    media_url: Mapped[str] = mapped_column(String(512), nullable=False)
    moderation_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
