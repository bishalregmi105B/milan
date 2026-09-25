"""Subscription tier service — the premium gate for companion features.

Tier hierarchy: free < basic < plus < premium. All companion-tier limits
(master plan §6) resolve here; blueprints call require_tier()/tier_limit()
and never read Subscription rows directly. Lookups are memoized briefly
per worker process to keep per-request overhead near zero; webhook tier
changes take effect on the next process-local refresh.
"""
import logging
import time
from datetime import datetime, timezone

from flask_jwt_extended import get_jwt_identity, jwt_required

from app.models import Subscription

logger = logging.getLogger(__name__)

TIER_RANK = {"free": 0, "basic": 1, "plus": 2, "premium": 3}
_TIER_TTL_SECONDS = 120
_tier_cache: dict[str, tuple[float, str]] = {}

# Master plan §6 / doc 8 §C7 — per-tier capability limits. Keys are consumed by
# saathi routes and the initiative/status/bond tasks.
#
# doc 8 changed the shape of the free tier deliberately. It used to grant zero
# companions and zero auto-texts, which meant a free user could only reach a
# "practice coach" — the exact experience in the bug report. Free now gets ONE
# real relationship with light auto-texting; paid tiers buy depth (how close it
# can get, how present she is) and breadth (how many companions), not access.
TIER_LIMITS = {
    "free": {
        "romantic_companions": 1,       # one real relationship, not a demo
        "proactive_daily": 2,           # she texts first, sparingly
        "status_posts_daily": 1,
        "intimacy_cap": 40,             # real warmth, short of the deep stages
        "voice_notes": False,
        "regenerate_per_reply": 2,
        "daily_likes": 25,
        "daily_superlikes": 0,
        "rewinds_per_day": 0,
        "monthly_boost": False,
        "top_picks": False,
    },
    "basic": {
        "romantic_companions": 2,
        "proactive_daily": 4,
        "status_posts_daily": 2,
        "intimacy_cap": 65,
        "voice_notes": False,
        "regenerate_per_reply": 5,
        "daily_likes": 50,
        "daily_superlikes": 5,
        "rewinds_per_day": 0,
        "monthly_boost": False,
        "top_picks": True,
    },
    "plus": {
        "romantic_companions": 4,
        "proactive_daily": 6,
        "status_posts_daily": 3,
        "intimacy_cap": 85,
        "voice_notes": True,
        "regenerate_per_reply": 10,
        "daily_likes": -1,
        "daily_superlikes": 10,
        "rewinds_per_day": 10,
        "monthly_boost": True,
        "top_picks": True,
    },
    "premium": {
        "romantic_companions": 8,
        "proactive_daily": 10,
        "status_posts_daily": 3,
        "intimacy_cap": 100,
        "voice_notes": True,
        "regenerate_per_reply": 20,
        "daily_likes": -1,
        "daily_superlikes": 15,
        "rewinds_per_day": 25,
        "monthly_boost": True,
        "top_picks": True,
    },
}


def normalize_tier(tier: str | None) -> str:
    return tier if tier in TIER_RANK else "free"


def _load_tier(user_id) -> str:
    # JWT identity is a string UUID; Subscription.user_id is a UUID column —
    # coerce so both sqlite (tests) and Postgres accept the comparison.
    if isinstance(user_id, str):
        try:
            import uuid as uuid_module

            user_id = uuid_module.UUID(user_id)
        except ValueError:
            return "free"
    sub = (
        Subscription.query.filter(
            Subscription.user_id == user_id,
            Subscription.status == "active",
        )
        .order_by(Subscription.renews_at.desc().nullslast())
        .first()
    )
    if sub is None:
        return "free"
    if sub.renews_at is not None and sub.renews_at < datetime.now(timezone.utc):
        return "free"
    return normalize_tier(sub.tier)


def get_user_tier(user_id) -> str:
    key = str(user_id)
    now = time.monotonic()
    cached = _tier_cache.get(key)
    if cached and now - cached[0] < _TIER_TTL_SECONDS:
        return cached[1]
    tier = _load_tier(user_id)
    _tier_cache[key] = (now, tier)
    return tier


def invalidate_tier_cache(user_id) -> None:
    _tier_cache.pop(str(user_id), None)


def tier_at_least(user_tier: str, minimum: str) -> bool:
    return TIER_RANK.get(user_tier, 0) >= TIER_RANK.get(minimum, 0)


def tier_limit(user_id, key: str):
    tier = get_user_tier(user_id)
    return TIER_LIMITS.get(tier, TIER_LIMITS["free"]).get(key)


def require_tier(minimum: str):
    """Decorator: 403 unless the caller's active tier >= minimum.
    Usage on companion routes: @require_tier("basic")."""

    def wrapper(fn):
        from functools import wraps

        @jwt_required()
        @wraps(fn)
        def inner(*args, **kwargs):
            user_id = get_jwt_identity()
            if not tier_at_least(get_user_tier(user_id), minimum):
                return {
                    "error": "upgrade_required",
                    "message": "This companion feature needs a higher Milan pass.",
                    "required_tier": minimum,
                }, 403
            return fn(*args, **kwargs)

        return inner

    return wrapper
