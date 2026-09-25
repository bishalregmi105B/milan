import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import Match, Message, Notification, NotificationPreference

logger = logging.getLogger(__name__)

CATEGORY_DEFAULT_CAPS = {
    "matches": 5,
    "messages": 10,
    "saathi": 1,
    "social": 5,
    "promo": 1,
}

DEFAULT_SEND_WINDOW = (19, 21)


def predicted_send_time(user_id) -> datetime:
    """Best send window from the user's own historical open times; 7-9pm fallback."""
    opens = (
        Notification.query.filter_by(user_id=user_id)
        .filter(Notification.opened_at.isnot(None))
        .order_by(Notification.opened_at.desc())
        .limit(50)
        .all()
    )
    if not opens:
        now = datetime.now(timezone.utc)
        candidate = now.replace(hour=DEFAULT_SEND_WINDOW[0], minute=0, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate
    hour_counts = Counter(n.opened_at.astimezone().hour for n in opens)
    best_hour = hour_counts.most_common(1)[0][0]
    now = datetime.now(timezone.utc).astimezone()
    candidate = now.replace(hour=best_hour, minute=0, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def should_send(user_id, category: str) -> bool:
    """Gate called before ANY notification is queued — including Saathi proactive messages."""
    pref = NotificationPreference.query.filter_by(user_id=user_id, category=category).first()
    if pref is not None and not pref.enabled:
        return False
    cap = pref.max_per_day if pref is not None else CATEGORY_DEFAULT_CAPS.get(category, 3)
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    sent_recently = Notification.query.filter(
        Notification.user_id == user_id,
        Notification.category == category,
        Notification.created_at >= since,
    ).count()
    return sent_recently < cap


def segment_for(user_id) -> str:
    """Behavioral segment selecting copy/cadence (doc 4 §6)."""
    from app.models import Swipe

    recent_matches = Match.query.filter(
        (Match.user_a_id == user_id) | (Match.user_b_id == user_id),
        Match.matched_at >= datetime.now(timezone.utc) - timedelta(days=7),
    ).count()

    match_ids = [
        m.id for m in Match.query.filter((Match.user_a_id == user_id) | (Match.user_b_id == user_id)).all()
    ]
    sent_messages = 0
    received_replies = 0
    if match_ids:
        sent_messages = Message.query.filter(
            Message.match_id.in_(match_ids), Message.sender_id == user_id
        ).count()
        received = Message.query.filter(
            Message.match_id.in_(match_ids), Message.sender_id != user_id
        ).count()
        received_replies = received

    likes_sent = Swipe.query.filter_by(swiper_id=user_id, direction="like").count()
    matches_total = Match.query.filter(
        (Match.user_a_id == user_id) | (Match.user_b_id == user_id)
    ).count()

    if recent_matches == 0 and sent_messages > 0 and received_replies == 0:
        return "liked_no_reply_24h"
    if recent_matches > 0:
        return "new_match_no_message" if sent_messages == 0 else "active_chatter"
    if likes_sent >= 20 and matches_total == 0:
        return "high_views_no_matches"
    return "dormant"


# Time-critical categories go out NOW. Everything else may be held for the
# user's predicted open window by the beat sweep.
#
# This was the "no push on the other device" bug: EVERY notification, including
# a live chat message, only got a DB row and waited for
# send_scheduled_notifications -> predicted_send_time, which for a user with no
# open history returns 7pm *tomorrow*. A message push could sit unsent for 24h.
IMMEDIATE_CATEGORIES = {"messages", "matches", "saathi", "safety"}


def queue_notification(user_id, category: str, title: str, body: str, data: dict | None = None) -> bool:
    """Queue through caps; returns False when suppressed by preference or cap.
    Time-critical categories are pushed immediately instead of waiting for the
    predicted-send-window sweep."""
    if not should_send(user_id, category):
        logger.info("notification suppressed by cap/pref user=%s category=%s", user_id, category)
        return False
    notification = Notification(user_id=user_id, category=category, title=title,
                                body=body, data=data)
    db.session.add(notification)
    db.session.commit()

    if category in IMMEDIATE_CATEGORIES:
        try:
            from datetime import datetime, timezone

            from app.models import User
            from app.tasks.notification_tasks import _deliver_push

            user = db.session.get(User, user_id)
            if user is not None:
                _deliver_push(user, notification)
                notification.sent_at = datetime.now(timezone.utc)
                db.session.commit()
        except Exception:  # noqa: BLE001 — a push failure must not fail the
            logger.exception("immediate push failed user=%s", user_id)  # caller
    return True
