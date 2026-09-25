"""Trust score — one persisted scalar per user (doc 8 §C2, §A5 "worth
importing" from dobato, done with Milan's richer signals).

Milan collects far more raw trust signal than dobato ever did — liveness
checks, face embeddings with duplicate detection, scam flags, moderation
events, report outcomes — but never rolled any of it into a number. This
service is the single writer of `users.trust_score` (default 50):

    25 base
  + 20 passed liveness
  + 10 verified (phone/email OTP at signup)
  + 15 profile completeness (photo + bio + interests + intent)
  + 10 tenure (account older than 30 days)
  − 15 per open (unresolved) report, capped at −45
  − 10 per unreviewed high-risk scam flag, capped at −30
  − 40 duplicate face (same person, second account)
  + 5 bonus for a video intro — bounded to the 0..100 clamp.

Every writer recomputes from source rows, so the score never drifts from the
signals. Call it after: liveness submission, profile/photo changes, report
filing/resolution, scam-flag creation. Reads: profile badge, discovery
ranking (§C8 `verified` term), match cards.
"""
import logging
from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import FaceEmbedding, LivenessCheck, Report, ScamFlag

logger = logging.getLogger(__name__)

BASE = 25
LIVENESS_PASS = 20
VERIFIED = 10
COMPLETENESS = 15
TENURE = 10
VIDEO_INTRO = 5
REPORT_PENALTY = 15
SCAMFLAG_PENALTY = 10
DUPLICATE_FACE_PENALTY = 40


def compute(user) -> int:
    """Recompute the trust score for a user from source rows. Never raises —
    a scoring failure must not fail the request that triggered it."""
    try:
        return _compute(user)
    except Exception:
        logger.exception("trust score computation failed user=%s", getattr(user, "id", None))
        return getattr(user, "trust_score", 50) or 50


def _compute(user) -> int:
    score = BASE

    liveness = (LivenessCheck.query.filter_by(user_id=user.id, passed=True)
                .order_by(LivenessCheck.created_at.desc()).first())
    if liveness:
        score += LIVENESS_PASS
    if user.is_verified:
        score += VERIFIED

    score += _completeness_bonus(user)

    created_at = getattr(user, "created_at", None)
    if created_at and datetime.now(timezone.utc) - _as_aware(created_at) > timedelta(days=30):
        score += TENURE

    if getattr(user, "video_intro", None) is not None:
        score += VIDEO_INTRO

    open_reports = Report.query.filter(
        Report.target_id == user.id,
        Report.status.in_(("open", "reviewing", "escalated")),
    ).count()
    score -= min(open_reports * REPORT_PENALTY, 45)

    high_risk_flags = ScamFlag.query.filter(
        ScamFlag.flagged_user_id == user.id,
        ScamFlag.risk_level == "high",
        ScamFlag.reviewed.is_(False),
    ).count()
    score -= min(high_risk_flags * SCAMFLAG_PENALTY, 30)

    embedding = FaceEmbedding.query.filter_by(user_id=user.id).first()
    if embedding and embedding.duplicate_of_user_id:
        score -= DUPLICATE_FACE_PENALTY

    return max(0, min(100, score))


def _completeness_bonus(user) -> int:
    profile = getattr(user, "profile", None)
    if profile is None:
        return 0
    filled = 0
    required = 0
    for value in (user.photos, profile.bio, profile.interests, user.intent_mode):
        required += 1
        if value:
            filled += 1
    return round(COMPLETENESS * filled / required) if required else 0


def refresh(user) -> int:
    """Recompute and persist. Returns the new score."""
    score = compute(user)
    if user.trust_score != score:
        user.trust_score = score
        db.session.add(user)
        db.session.commit()
    return score


def _as_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
