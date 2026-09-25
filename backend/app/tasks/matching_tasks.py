import logging
from datetime import datetime, timedelta, timezone

from app.extensions import celery_app, db
from app.models import Match, Message, User
from app.services.matching_service import rank_candidates

logger = logging.getLogger(__name__)

MATCH_EXPIRY_WARN_HOURS = 48
MATCH_EXPIRY_HOURS = 72


@celery_app.task(name="app.tasks.matching_tasks.nightly_rerank")
def nightly_rerank() -> dict:
    """Batch-refresh candidate ranking per active user using accumulated signal."""
    active_users = User.query.filter_by(account_status="active").limit(1000).all()
    ranked = 0
    for user in active_users:
        try:
            rank_candidates(user, [])
            ranked += 1
        except Exception:
            logger.exception("nightly rerank failed for user %s", user.id)
    db.session.commit()
    return {"users_ranked": ranked}


def _last_message_at(match: Match) -> datetime | None:
    last = (Message.query.filter_by(match_id=match.id)
            .order_by(Message.created_at.desc()).first())
    return last.created_at if last else None


@celery_app.task(name="app.tasks.matching_tasks.expire_stale_matches")
def expire_stale_matches() -> dict:
    """Match expiry (doc 8 §C9): a human match with NO conversation goes
    stale — warned at 48h, expired at 72h of silence. Companion matches and
    matches where anyone already messaged never expire."""
    from app.services.notification_service import queue_notification

    now = datetime.now(timezone.utc)
    warned = expired = 0

    # ── 48h warning ──────────────────────────────────────────────────────
    warn_deadline = now - timedelta(hours=MATCH_EXPIRY_WARN_HOURS)
    expiring = Match.query.filter(
        Match.is_active.is_(True),
        Match.kind == "human",
        Match.expiry_warned_at.is_(None),
        Match.matched_at <= warn_deadline,
        Match.matched_at > now - timedelta(hours=MATCH_EXPIRY_HOURS),
    ).all()
    for match in expiring:
        match.expiry_warned_at = now
        if _last_message_at(match) is not None:
            continue  # conversation started between ticks — no warning
        for uid in (match.user_a_id, match.user_b_id):
            queue_notification(
                uid, "matches",
                "Your match expires in 24 hours ⏳",
                "Say something before the connection fades.",
                data={"type": "match_expiry_warning", "match_id": str(match.id)},
            )
        warned += 1

    # ── 72h expiry ───────────────────────────────────────────────────────
    expiry_deadline = now - timedelta(hours=MATCH_EXPIRY_HOURS)
    stale = Match.query.filter(
        Match.is_active.is_(True),
        Match.kind == "human",
        Match.matched_at <= expiry_deadline,
    ).all()
    for match in stale:
        if match.last_activity_at is None:
            match.last_activity_at = _last_message_at(match)
        if match.last_activity_at is not None:
            continue  # a conversation happened — never expires
        match.is_active = False
        for uid in (match.user_a_id, match.user_b_id):
            queue_notification(
                uid, "matches",
                "A match has expired",
                "The conversation window closed after 72 hours of silence.",
                data={"type": "match_expired", "match_id": str(match.id)},
            )
        expired += 1

    db.session.commit()
    return {"warned": warned, "expired": expired}
