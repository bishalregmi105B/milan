import uuid
from datetime import datetime

from sqlalchemy import (Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base


class Swipe(AuditMixin, Base):
    __tablename__ = "swipes"
    __table_args__ = (UniqueConstraint("swiper_id", "target_id", name="uq_swipe_once"),)

    swiper_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    # like | pass | superlike (superlike surfaces to the recipient before match)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    # Message-before-matching (Platinum pattern): 140-char note on a superlike
    note: Mapped[str | None] = mapped_column(String(140), nullable=True)
    # Rewind (undo) marks the swipe consumed rather than deleting it, so the
    # daily-cap ledger and abuse auditing stay intact.
    is_rewound: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    seen_by_target: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class SwipeQuota(AuditMixin, Base):
    """Daily like/superlike ledger enforced SERVER-SIDE (never client trust).
    One row per user per Kathmandu-local day."""
    __tablename__ = "swipe_quotas"
    __table_args__ = (UniqueConstraint("user_id", "day_key", name="uq_quota_day"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    day_key: Mapped[str] = mapped_column(String(10), nullable=False)
    likes_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    superlikes_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rewinds_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Boost(AuditMixin, Base):
    """Time-boxed visibility multiplier applied at ranking time."""
    __tablename__ = "boosts"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), default="boost", nullable=False)  # boost|super_boost
    multiplier: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(24), default="tier_grant", nullable=False)


class TopPick(AuditMixin, Base):
    """Daily curated set (refreshed by a beat job). Free tier sees a teaser
    count; premium sees the full set."""
    __tablename__ = "top_picks"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    day_key: Mapped[str] = mapped_column(String(10), nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)


class Match(AuditMixin, Base):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("user_a_id", "user_b_id", name="uq_match_pair"),)

    user_a_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    user_b_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    compatibility_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    match_reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    # companion|human — a companion match is a normal Match row so the inbox,
    # chat, realtime and theme systems need no special-casing (§14).
    kind: Mapped[str] = mapped_column(String(16), default="human", nullable=False)

    # Match expiry (doc 8 §C9): a match with no conversation goes stale. The
    # sweep warns at 48h and expires at 72h — silence is the signal, so ANY
    # message clears the deadline permanently (companion matches never expire).
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    expiry_warned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    messages = relationship("Message", back_populates="match", lazy="dynamic")


class Prompt(AuditMixin, Base):
    __tablename__ = "prompts"

    text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class PromptAnswer(AuditMixin, Base):
    __tablename__ = "prompt_answers"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    prompt_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prompts.id"), nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(default=0, nullable=False)
    feedback_tag: Mapped[str | None] = mapped_column(String(32), nullable=True)
    feedback_suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
