"""Swipe economy (Tinder-parity, server-enforced): daily like/superlike caps
per tier, superlike notes (message-before-match), rewind, boosts, Who-Liked-You
and Top Picks. The CLIENT NEVER enforces limits — every quota check happens
here, against the `swipe_quotas` ledger, in Kathmandu-local days."""
import logging
import uuid as uuid_module
from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import Boost, Match, Swipe, SwipeQuota, TopPick, User
from app.services import subscription_service

logger = logging.getLogger(__name__)

KATHMANDU_TZ = timezone(timedelta(hours=5, minutes=45))
SUPERLIKE_NOTE_MAX = 140


def _today_key() -> str:
    return datetime.now(KATHMANDU_TZ).strftime("%Y-%m-%d")


def _quota_row(user_id) -> SwipeQuota:
    """Get-or-create with a race-safe fallback: two concurrent first-swipes of
    the day both INSERT; the loser catches the unique violation and re-reads."""
    from sqlalchemy.exc import IntegrityError

    day = _today_key()
    row = SwipeQuota.query.filter_by(user_id=user_id, day_key=day).first()
    if row is not None:
        return row
    row = SwipeQuota(user_id=user_id, day_key=day)
    db.session.add(row)
    try:
        db.session.flush()
        return row
    except IntegrityError:
        db.session.rollback()
        return SwipeQuota.query.filter_by(user_id=user_id, day_key=day).one()


def quota_snapshot(user_id) -> dict:
    tier = subscription_service.get_user_tier(user_id)
    limits = subscription_service.TIER_LIMITS.get(tier, subscription_service.TIER_LIMITS["free"])
    row = _quota_row(user_id)
    db.session.commit()
    return {
        "tier": tier,
        "likes_limit": limits.get("daily_likes", 25),
        "likes_used": row.likes_used,
        "likes_remaining": None if limits.get("daily_likes", 25) == -1
        else max(0, limits["daily_likes"] - row.likes_used),
        "superlikes_limit": limits.get("daily_superlikes", 0),
        "superlikes_used": row.superlikes_used,
        "superlikes_remaining": max(0, limits.get("daily_superlikes", 0) - row.superlikes_used),
        "rewinds_limit": limits.get("rewinds_per_day", 0),
        "rewinds_used": row.rewinds_used,
        "rewinds_remaining": max(0, limits.get("rewinds_per_day", 0) - row.rewinds_used),
        "monthly_boost": limits.get("monthly_boost", False),
        "top_picks": limits.get("top_picks", False),
        "resets_at": (datetime.now(KATHMANDU_TZ).replace(hour=0, minute=0, second=0,
                                                         microsecond=0)
                      + timedelta(days=1)).isoformat(),
    }


def check_can_like(user_id) -> tuple[bool, str | None]:
    snap = quota_snapshot(user_id)
    if snap["likes_remaining"] == 0:
        return False, "daily_like_cap"
    return True, None


def check_can_superlike(user_id) -> tuple[bool, str | None]:
    snap = quota_snapshot(user_id)
    if snap["superlikes_remaining"] == 0:
        return False, "superlike_cap"
    return True, None


def record_like_usage(user_id, direction: str) -> None:
    # Conditional atomic increment — concurrent swipes can never overshoot the
    # cap via a lost update (check_can_like still gates, this makes it airtight).
    row = _quota_row(user_id)
    if direction == "like":
        SwipeQuota.query.filter_by(id=row.id).update(
            {SwipeQuota.likes_used: SwipeQuota.likes_used + 1})
    elif direction == "superlike":
        SwipeQuota.query.filter_by(id=row.id).update(
            {SwipeQuota.superlikes_used: SwipeQuota.superlikes_used + 1})
    db.session.commit()


def rewind_last_swipe(user) -> dict:
    """Undo the most recent swipe of TODAY (premium-only count). The swipe row
    is marked rewound (kept for audit), any match it created is deactivated,
    and the quota usage is refunded."""
    tier = subscription_service.get_user_tier(user.id)
    limits = subscription_service.TIER_LIMITS.get(tier, subscription_service.TIER_LIMITS["free"])
    allowed = int(limits.get("rewinds_per_day", 0) or 0)
    row = _quota_row(user.id)
    if allowed <= 0 or row.rewinds_used >= allowed:
        return {"rewound": False, "reason": "rewind_cap"}

    last = (Swipe.query.filter_by(swiper_id=user.id, is_rewound=False)
            .order_by(Swipe.created_at.desc()).first())
    if last is None:
        return {"rewound": False, "reason": "nothing_to_rewind"}

    last.is_rewound = True
    match = Match.query.filter(
        ((Match.user_a_id == user.id) & (Match.user_b_id == last.target_id))
        | ((Match.user_a_id == last.target_id) & (Match.user_b_id == user.id))).first()
    if match is not None:
        match.is_active = False
    row.rewinds_used += 1
    if last.direction == "like":
        row.likes_used = max(0, row.likes_used - 1)
    elif last.direction == "superlike":
        row.superlikes_used = max(0, row.superlikes_used - 1)
    db.session.commit()
    return {"rewound": True, "target_id": str(last.target_id)}


def grant_boost(user_id, kind: str = "boost") -> dict:
    """Tier-granted monthly boost (or a-la-carte later). Applies at ranking."""
    tier = subscription_service.get_user_tier(user_id)
    if not subscription_service.TIER_LIMITS.get(
            tier, subscription_service.TIER_LIMITS["free"]).get("monthly_boost"):
        return {"granted": False, "reason": "upgrade_required"}
    active = Boost.query.filter_by(user_id=user_id).filter(
        Boost.expires_at > datetime.now(timezone.utc)).first()
    if active is not None:
        return {"granted": False, "reason": "boost_active"}
    minutes = 180 if kind == "super_boost" else 30
    now = datetime.now(timezone.utc)
    db.session.add(Boost(
        user_id=user_id, kind=kind, multiplier=100.0 if kind == "super_boost" else 10.0,
        started_at=now, expires_at=now + timedelta(minutes=minutes),
        source="tier_grant"))
    db.session.commit()
    return {"granted": True, "kind": kind, "minutes": minutes}


def active_boost_multiplier(user_id) -> float:
    row = (Boost.query.filter_by(user_id=user_id)
           .filter(Boost.expires_at > datetime.now(timezone.utc)).first())
    return row.multiplier if row else 1.0


FREE_LIKES_VISIBLE = 5


def who_liked_me(user_id, premium: bool) -> dict:
    """Who Liked You (§A4.9 revised): everyone sees the first FIVE likers as
    real identities — beyond that the list stays but each entry is locked
    behind the pass (premium reveals the rest). Free users were previously
    shown only a count, which read as a paywall with no product."""
    likes = (Swipe.query.filter_by(target_id=user_id, direction="like", seen_by_target=False)
             .order_by(Swipe.created_at.desc()).all())
    liker_ids = []
    for like in likes:
        # only counts if this user hasn't already swiped them
        already = Swipe.query.filter_by(swiper_id=user_id, target_id=like.swiper_id).first()
        if already is None and like.swiper_id not in liker_ids:
            liker_ids.append(like.swiper_id)

    from app.utils.serializers import user_brief

    users = [db.session.get(User, uid) for uid in liker_ids[:50]]
    payload = {"count": len(liker_ids), "premium": premium,
               "free_visible": FREE_LIKES_VISIBLE}
    payload["likes"] = [{
        **user_brief(u),
        "superlike": any(s.direction == "superlike" for s in likes if s.swiper_id == u.id),
        "note": next((s.note for s in likes
                      if s.swiper_id == u.id and s.direction == "superlike" and s.note), None),
        # past the free five, identity fields blank out client-side and the
        # card renders as a locked teaser
        "locked": (not premium) and index >= FREE_LIKES_VISIBLE,
    } for index, u in enumerate(users) if u is not None]
    return payload


def mark_likes_seen(user_id) -> None:
    Swipe.query.filter_by(target_id=user_id).update({"seen_by_target": True})
    db.session.commit()


def refresh_top_picks(user_id, candidate_pool: list[tuple[User, float]]) -> int:
    """Store today's Top Picks (called from the discovery refresh path)."""
    day = _today_key()
    TopPick.query.filter_by(user_id=user_id, day_key=day).delete()
    picks = sorted(candidate_pool, key=lambda pair: pair[1], reverse=True)[:6]
    for candidate, score in picks:
        db.session.add(TopPick(
            user_id=user_id, candidate_id=candidate.id, day_key=day,
            score=float(score), reason=None))
    db.session.commit()
    return len(picks)


def get_top_picks(user_id) -> dict:
    tier = subscription_service.get_user_tier(user_id)
    premium = subscription_service.TIER_LIMITS.get(
        tier, subscription_service.TIER_LIMITS["free"]).get("top_picks", False)
    day = _today_key()
    rows = (TopPick.query.filter_by(user_id=user_id, day_key=day)
            .order_by(TopPick.score.desc()).all())
    count = len(rows)
    if not premium:
        return {"premium": False, "count": count, "picks": []}
    from app.utils.serializers import user_brief

    picks = []
    for row in rows[:6]:
        user = db.session.get(User, row.candidate_id)
        if user is not None:
            picks.append({**user_brief(user), "pick_score": row.score})
    return {"premium": True, "count": count, "picks": picks}
