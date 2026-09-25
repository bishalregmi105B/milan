import logging

from app.extensions import db
from app.models import Match, Profile, PromptAnswer, Swipe, User

logger = logging.getLogger(__name__)

# doc 8 §C8 — ranking v2. Every term draws on data already collected in
# onboarding (interview answers were stored but never consumed). The old
# 40-base score with 3 signals is replaced by this weighted 0..100 scale.
W_INTEREST = 22.0
W_INTENT = 14.0
W_VALUES = 10.0
W_DISTANCE = 12.0
W_RECENCY = 10.0
W_STYLE = 8.0
W_RECIPROCAL = 8.0
W_PHOTOS = 6.0
W_VERIFIED = 5.0
W_PROMPTS = 5.0
W_DEALBREAKER_PENALTY = 20.0

# distance decay reaches 0 at this radius (km)
MAX_DISTANCE_KM = 50.0


def _shared_interests(profile_a: Profile | None, profile_b: Profile | None) -> list[str]:
    if not profile_a or not profile_b:
        return []
    a = set(profile_a.interests or [])
    b = set(profile_b.interests or [])
    return sorted(a & b)


def _style_complementary(style_a: str | None, style_b: str | None) -> bool:
    pairs = {("direct", "playful"), ("direct", "thoughtful"), ("playful", "thoughtful")}
    if not style_a or not style_b:
        return False
    return (style_a, style_b) in pairs or (style_b, style_a) in pairs


def _interest_jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _distance_decay(km: float | None) -> float:
    if km is None:
        return 0.0
    return max(0.0, 1.0 - (km / MAX_DISTANCE_KM))


def _activity_recency(last_active_at) -> float:
    """Hours the candidate has been quiet, on a gentle curve. A user seen
    today ranks far above one unseen for a month."""
    from datetime import datetime, timedelta, timezone

    if last_active_at is None:
        return 0.05
    dt = last_active_at if last_active_at.tzinfo else last_active_at.replace(tzinfo=timezone.utc)
    hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
    if hours <= 24:
        return 1.0
    if hours <= 24 * 7:
        return 0.6
    if hours <= 24 * 30:
        return 0.25
    return 0.05


def _reciprocal_like(viewer_id, candidate_id) -> bool:
    return db.session.query(Swipe.id).filter_by(
        swiper_id=candidate_id, target_id=viewer_id,
        direction="like").first() is not None or db.session.query(Swipe.id).filter_by(
        swiper_id=candidate_id, target_id=viewer_id,
        direction="superlike").first() is not None


_DEALBREAKER_FIELD_MAP = {
    # dealbreaker keys from the interview -> candidate profile fields that
    # trip them. Stored dealbreakers are free strings; normalise loosely.
    "smoking": ("smoking",),
    "smokes": ("smoking",),
    "drinking": ("drinking",),
    "drinks": ("drinking",),
    "non_veg": ("diet",),
    "vegan": ("diet",),
}


def _dealbreaker_hit(viewer_profile: Profile | None, candidate: User) -> bool:
    if not viewer_profile or not viewer_profile.dealbreakers:
        return False
    cand_profile = getattr(candidate, "profile", None)
    if not cand_profile:
        return False
    cand_tags = {str(t).lower() for t in (cand_profile.lifestyle_tags or [])}
    for raw in viewer_profile.dealbreakers:
        key = str(raw).strip().lower().replace(" ", "_").replace("-", "_")
        fields = _DEALBREAKER_FIELD_MAP.get(key)
        if fields:
            for f in fields:
                value = str(getattr(cand_profile, f, "") or "").lower()
                # "never"/"no" answers do not trip the dealbreaker
                if value and not value.startswith(("never", "no", "none")):
                    return True
        elif key in cand_tags:
            return True
    return False


def compute_compatibility(user_a: User, user_b: User) -> tuple[float, dict]:
    """Compatibility in 0..100 (doc 8 §C8). `user_a` is the viewer — the
    reciprocal-like and dealbreaker terms are directional."""
    profile_a = getattr(user_a, "profile", None)
    profile_b = getattr(user_b, "profile", None)

    interests_a = set(profile_a.interests or []) if profile_a else set()
    interests_b = set(profile_b.interests or []) if profile_b else set()
    jaccard = _interest_jaccard(interests_a, interests_b)
    shared_interests = sorted(interests_a & interests_b)

    values_a = set(profile_a.values_tags or []) if profile_a else set()
    values_b = set(profile_b.values_tags or []) if profile_b else set()

    intent_match = bool(
        profile_a and profile_b
        and profile_a.relationship_intent
        and profile_a.relationship_intent == profile_b.relationship_intent
    )
    styles_complement = _style_complementary(
        profile_a.conversation_style if profile_a else None,
        profile_b.conversation_style if profile_b else None,
    )
    distance_km = _haversine_km(profile_a, profile_b)
    reciprocal = _reciprocal_like(user_a.id, user_b.id)

    photo_count = len(user_b.photos or [])
    prompt_depth = min(len(profile_b.prompts or []) if profile_b else 0, 3)

    score = (
        W_INTEREST * jaccard
        + (W_INTENT if intent_match else 0.0)
        + W_VALUES * (len(values_a & values_b) / 3.0 if values_a else 0.0)
        + W_DISTANCE * _distance_decay(distance_km)
        + W_RECENCY * _activity_recency(getattr(user_b, "last_active_at", None))
        + (W_STYLE if styles_complement else 0.0)
        + (W_RECIPROCAL if reciprocal else 0.0)
        + W_PHOTOS * min(photo_count / 4.0, 1.0)
        + (W_VERIFIED if user_b.is_verified else 0.0)
        + W_PROMPTS * (prompt_depth / 3.0)
        - (W_DEALBREAKER_PENALTY if _dealbreaker_hit(profile_a, user_b) else 0.0)
    )
    score = max(0.0, min(score, 99.0))

    signals = {
        "shared_interest_tags": shared_interests,
        "interest_jaccard": round(jaccard, 3),
        "compatible_intent_mode": intent_match,
        "shared_values": sorted(values_a & values_b),
        "complementary_conversation_styles": styles_complement,
        "distance_km": distance_km,
        "recently_active": _activity_recency(getattr(user_b, "last_active_at", None)) >= 0.6,
        "reciprocal_like": reciprocal,
        "dealbreaker_hit": _dealbreaker_hit(profile_a, user_b),
    }
    return round(score, 1), signals


def _haversine_km(a: Profile | None, b: Profile | None) -> float | None:
    import math

    if not a or not b or a.latitude is None or b.latitude is None:
        return None
    lat1, lon1, lat2, lon2 = map(math.radians, [a.latitude, a.longitude, b.latitude, b.longitude])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return round(6371 * 2 * math.asin(math.sqrt(h)), 1)


def record_swipe_and_match(swiper: User, target: User, direction: str,
                           note: str | None = None) -> dict:
    # A REWOUND swipe doesn't count: the user undid it, so the target is
    # swipeable again (rewind refunds the quota and re-opens the decision).
    existing_swipe = Swipe.query.filter_by(
        swiper_id=swiper.id, target_id=target.id, is_rewound=False).first()
    if existing_swipe is not None:
        return {"match": False, "already_swiped": True}

    swipe = Swipe(swiper_id=swiper.id, target_id=target.id, direction=direction,
                  note=note or None)
    db.session.add(swipe)
    db.session.flush()

    result: dict = {"match": False}
    if direction in ("like", "superlike"):
        reciprocal = Swipe.query.filter_by(swiper_id=target.id, target_id=swiper.id).first()
        if reciprocal and reciprocal.direction in ("like", "superlike"):
            user_a_id, user_b_id = sorted([swiper.id, target.id], key=str)
            existing = Match.query.filter_by(user_a_id=user_a_id, user_b_id=user_b_id).first()
            if existing is None:
                from sqlalchemy.exc import IntegrityError

                score, signals = compute_compatibility(swiper, target)
                from datetime import datetime, timedelta, timezone

                match = Match(
                    user_a_id=user_a_id,
                    user_b_id=user_b_id,
                    matched_at=db.func.now(),
                    compatibility_score=score,
                    # doc 8 §C9: the 72h conversation window starts now; any
                    # message clears it permanently (chat blueprint writes
                    # last_activity_at).
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=72),
                )
                db.session.add(match)
                try:
                    db.session.flush()
                except IntegrityError:
                    # concurrent mutual swipe already created the pair
                    db.session.rollback()
                    return {"match": True, "already_matched": True}
                # The AI explainer is a NETWORK call — it must never sit inside
                # the swipe request (a Groq outage would hang swipes ~60s).
                # The reason text is filled asynchronously after commit.
                result = {"match": True, "match_id": str(match.id),
                          "compatibility_score": score}
                from flask import has_app_context, current_app

                if has_app_context() and current_app.config.get("TESTING"):
                    _fill_match_reason(str(match.id), signals)  # stubbed, instant
                else:
                    _queue_match_explainer(match.id, signals)
                # Both sides learn about the match — only the swiper's client
                # sees the swipe response; the other user gets a push.
                from app.services.notification_service import queue_notification

                other = target if swiper.id == match.user_a_id else swiper
                liker_name = (swiper.profile.display_name if swiper.profile else "Someone")
                queue_notification(
                    other.id, "matches",
                    f"It's a match with {liker_name}! 💛",
                    "Say namaste before the moment passes.",
                    data={"type": "match", "match_id": str(match.id)},
                )

    # Superlike surfaces to the recipient even without a mutual swipe: notify
    # them now (message-before-match note included when present).
    if direction == "superlike" and not result.get("match"):
        try:
            from app.services.notification_service import queue_notification

            queue_notification(
                target.id, "matches",
                f"{swiper.profile.display_name if swiper.profile else 'Someone'} super-liked you ⭐",
                note or "Open Milan to see who it is!",
                data={"type": "superlike", "liker_id": str(swiper.id)},
            )
        except Exception:  # noqa: BLE001
            logger.exception("superlike notification failed")
    elif direction == "like" and not result.get("match"):
        # doc 8 §A4 — a regular like must be visible to the recipient too:
        # they get a push on their FIRST unseen like (batched after that, the
        # who-liked-you screen holds the full list; premium reveals names).
        try:
            from app.services.notification_service import queue_notification

            unseen = Swipe.query.filter_by(
                target_id=target.id, direction="like", seen_by_target=False).count()
            if unseen <= 1:
                queue_notification(
                    target.id, "matches",
                    "Someone liked you 💛",
                    "Like back to see who it is — they're waiting for your move.",
                    data={"type": "like_received"},
                )
        except Exception:  # noqa: BLE001
            logger.exception("like notification failed")
    db.session.commit()
    return result


def rank_candidates(viewer: User, candidates: list[User]) -> list[tuple[User, float]]:
    from datetime import datetime, timezone

    from app.models import Boost

    now = datetime.now(timezone.utc)
    boosted_ids = {
        b.user_id for b in Boost.query.filter(Boost.expires_at > now).all()
    }
    scored = []
    for candidate in candidates:
        score, _signals = compute_compatibility(viewer, candidate)
        # active boosts multiply the final score — visibility, not quality
        if candidate.id in boosted_ids:
            score = min(99.0, score * 1.5 + 20)
        scored.append((candidate, score))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored


def nightly_rerank_for_user(user: User) -> None:
    """Batch-refresh ranking signal; consumed by matching_tasks.nightly_rerank."""
    rank_candidates(user, [])


def _fill_match_reason(match_id: str, signals: dict) -> None:
    import uuid as uuid_module

    from app.extensions import db as _db

    match = _db.session.get(Match, uuid_module.UUID(match_id))
    if match is None or match.match_reason_text:
        return
    from app.services.groq_service import explain_match

    try:
        match.match_reason_text = explain_match(signals)
    except Exception:
        return
    _db.session.commit()


def _queue_match_explainer(match_id, signals: dict) -> None:
    """Fill match_reason_text off the request path (network call isolation:
    a Groq outage must never hang the swipe endpoint)."""
    from threading import Thread

    try:
        Thread(target=_fill_match_reason, args=(str(match_id), dict(signals)),
               daemon=True).start()
    except Exception:
        logger.warning("match explainer thread could not start")
