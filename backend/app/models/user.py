import uuid
from datetime import date, datetime

from sqlalchemy import (JSON, Boolean, Date, DateTime, Float, ForeignKey,
                        Integer, String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base, utcnow


class User(AuditMixin, Base):
    __tablename__ = "users"

    # Phone is nullable so email-first accounts can exist; at least one of
    # phone/email is enforced in the auth flow, not at the schema level.
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(16), default="phone", nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    intent_mode: Mapped[str] = mapped_column(String(16), default="serious", nullable=False)
    discreet_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    account_status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="user", nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    data_saver: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # AI companions are REAL user rows (§14): they own a Profile, Photos, a
    # Match with their human, and Messages — so every downstream surface
    # (inbox, chat, realtime, themes, read receipts) treats them identically.
    # `is_ai` is the single source of truth for the one place they must differ:
    # the AI disclosure badge. Never used to fork chat/transport logic.
    is_ai: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_character_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("saathi_characters.id"), unique=True, nullable=True)
    # Consent state for the AI-companion disclosure — persisted per ACCOUNT so
    # the intro is shown once, ever (re-shown only when the version changes).
    saathi_intro_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    saathi_terms_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Opt-in to seeing AI companion profiles in the Discover deck (default off;
    # they're always reachable from the Companions surface regardless).
    include_ai_in_discovery: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False)

    # Reputation rollup (doc 8 §C9): a single 0-100 scalar derived from the
    # signals Milan already collects (liveness, face embedding, photo count,
    # profile completeness, upheld reports). Read by discovery ranking so
    # verified, complete, unreported profiles surface first.
    trust_score: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    # Soft delete: "delete my account" must be reversible for a grace window
    # and must not orphan matches/messages. Every read path filters this.
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    # Activity recency for ranking + "last seen" (updated on any authenticated
    # request; presence sockets refine it in realtime).
    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False)
    photos: Mapped[list["Photo"]] = relationship(back_populates="user", order_by="Photo.order_index")
    video_intro: Mapped["VideoIntro | None"] = relationship(back_populates="user", uselist=False)


class Profile(AuditMixin, Base):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    interests: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    horoscope_details: Mapped[dict | None] = mapped_column(JSON, default=None, nullable=True)
    ethnicity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    religion: Mapped[str | None] = mapped_column(String(64), nullable=True)
    profession: Mapped[str | None] = mapped_column(String(120), nullable=True)
    conversation_style: Mapped[str | None] = mapped_column(String(32), nullable=True)
    lifestyle_tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    values_tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    dealbreakers: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    relationship_intent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    interview_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Language identity (§14): every profile — human or AI — declares how it
    # actually writes. NOTHING hardcoded per character; the companion's prompt
    # is built from these fields, so two companions can speak completely
    # differently (romanized Nepali vs Devanagari vs Pahadi-accented vs English).
    # primary_script: roman | devanagari | mixed
    primary_script: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # languages: [{"code": "ne", "label": "Nepali", "fluency": "native"}, ...]
    languages: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # dialect: e.g. kathmandu_urban, pahadi_west, madhesi_hindi_mix, sherpa_east
    dialect: Mapped[str | None] = mapped_column(String(48), nullable=True)
    # speech_markers: characteristic fillers/particles this person actually uses
    speech_markers: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    hometown: Mapped[str | None] = mapped_column(String(120), nullable=True)
    education: Mapped[str | None] = mapped_column(String(120), nullable=True)
    height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diet: Mapped[str | None] = mapped_column(String(24), nullable=True)
    smoking: Mapped[str | None] = mapped_column(String(24), nullable=True)
    drinking: Mapped[str | None] = mapped_column(String(24), nullable=True)
    mother_tongue: Mapped[str | None] = mapped_column(String(48), nullable=True)
    # Sensitive-field visibility (caste/religion/income are opt-in to show)
    hidden_fields: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    prompts: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # Onboarding "what are you looking for" answers, verbatim, so the ranking
    # engine and the AI both read the user's OWN words instead of only the
    # LLM-extracted tags: [{"question", "answer", "answered_at"}].
    interview_answers: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    user: Mapped[User] = relationship(back_populates="profile")


class Photo(AuditMixin, Base):
    __tablename__ = "photos"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    order_index: Mapped[int] = mapped_column(default=0, nullable=False)
    moderation_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)

    user: Mapped[User] = relationship(back_populates="photos")


class VideoIntro(AuditMixin, Base):
    __tablename__ = "video_intros"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(nullable=True)
    moderation_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)

    user: Mapped[User] = relationship(back_populates="video_intro")


class Interest(AuditMixin, Base):
    """Canonical interest taxonomy (doc 8 §A5). `Profile.interests` used to be
    free text, so 'momo' and 'Momos' never matched and typos silently killed
    compatibility scoring. Profiles now store catalog KEYS; this table owns the
    human label, icon and grouping for the picker."""
    __tablename__ = "interests"

    key: Mapped[str] = mapped_column(String(48), unique=True, index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    label_ne: Mapped[str | None] = mapped_column(String(64), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(32), nullable=True)
    category: Mapped[str] = mapped_column(String(32), default="other", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ProfileView(AuditMixin, Base):
    """"Who viewed my profile" (doc 8 §C9). One row per viewer/viewed pair,
    `viewed_at` bumped on repeat views so the count stays honest instead of
    inflating with every scroll-past."""
    __tablename__ = "profile_views"
    __table_args__ = (
        UniqueConstraint("viewer_id", "viewed_id", name="uq_profile_view_pair"),
    )

    viewer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False)
    viewed_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False)
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # surfaced-to-owner flag so the "someone viewed you" notification fires once
    notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
