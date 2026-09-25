import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base


class LivenessCheck(AuditMixin, Base):
    __tablename__ = "liveness_checks"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    embedding_computed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class FaceEmbedding(AuditMixin, Base):
    __tablename__ = "face_embeddings"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    embedding_vector: Mapped[list] = mapped_column(JSON, nullable=False)
    source_check_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("liveness_checks.id"), nullable=True)
    duplicate_of_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    def similarity(self, other_vector: list[float]) -> float:
        if not self.embedding_vector or not other_vector:
            return 0.0
        a, b = self.embedding_vector, other_vector
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)


class VerificationAuditNote(AuditMixin, Base):
    __tablename__ = "verification_audit_notes"

    liveness_check_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("liveness_checks.id"), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)


class PreferenceCalibration(AuditMixin, Base):
    """LIKE/PASS/MAYBE calibration signal per user (doc 5 §1 final row).

    Stores only the derived photo embedding + label — never the image itself,
    mirroring the liveness-selfie retention rule for biometric-derived data.
    """

    __tablename__ = "preference_calibrations"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    photo_embedding: Mapped[list] = mapped_column(JSON, nullable=False)
    label: Mapped[str] = mapped_column(String(8), nullable=False)
