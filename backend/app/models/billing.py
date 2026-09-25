import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base


class Subscription(AuditMixin, Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    tier: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    renews_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_method_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("payment_methods.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)


class PaymentMethod(AuditMixin, Base):
    __tablename__ = "payment_methods"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    tokenized_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)


class Payment(AuditMixin, Base):
    __tablename__ = "payments"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_npr: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    provider_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    purpose: Mapped[str | None] = mapped_column(String(64), nullable=True)


class PaymentSubmission(AuditMixin, Base):
    """Phase-1 manual QR verification (real eSewa/Khalti merchant APIs need
    business KYC first). The user pays externally, submits the transaction ref
    + screenshot, and an admin approves — the entitlement activates ONLY on
    approval, never on submission. Every decision is audit-logged."""
    __tablename__ = "payment_submissions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    tier: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_npr: Mapped[int] = mapped_column(Integer, nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)  # esewa|khalti|fonepay|connectips
    reference_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    screenshot_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    screenshot_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    fraud_flags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)


class PaymentQrCode(AuditMixin, Base):
    """Admin-uploaded static QR per provider, shown on the checkout screen."""
    __tablename__ = "payment_qr_codes"

    method: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    image_url: Mapped[str] = mapped_column(String(512), nullable=False)
    account_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    instructions: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PaymentAuditLog(AuditMixin, Base):
    """Immutable trail for a manual financial process (disputes + fraud review)."""
    __tablename__ = "payment_audit_logs"

    submission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payment_submissions.id"), index=True, nullable=False)
    admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(24), nullable=False)  # submitted|approved|rejected
    detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
