import uuid as uuid_module
from datetime import date, timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db, limiter
from app.models import Block, Match, Swipe, User
from app.models import Match as _Match
from app.services import groq_service
from app.services.matching_service import record_swipe_and_match, rank_candidates
from app.services.preference_service import preference_bias_for, record_calibration
from app.utils.serializers import error_response, user_brief
from app.utils.validators import ALLOWED_SWIPE_DIRECTIONS

discovery_bp = Blueprint("discovery", __name__)

DAILY_CANDIDATE_LIMIT = 30


@discovery_bp.get("/candidates")
@jwt_required()
def candidates():
    viewer = db.session.get(User, uuid_module.UUID(get_jwt_identity()))
    swiped_ids = {s.target_id for s in Swipe.query.filter_by(swiper_id=viewer.id).all()}
    blocked_ids = {b.blocked_id for b in Block.query.filter_by(blocker_id=viewer.id).all()} | {
        b.blocker_id for b in Block.query.filter_by(blocked_id=viewer.id).all()
    }
    excluded = swiped_ids | blocked_ids | {viewer.id}

    # Search filters (Indian-app standard: TrulyMadly/Aisle/QuackQuack parity).
    # Server-side filtering — the client sends its filter state, never fakes it.
    args = request.args
    age_min = args.get("age_min", type=int)
    age_max = args.get("age_max", type=int)
    city = (args.get("city") or "").strip()
    verified_only = args.get("verified_only") == "true"
    intent = (args.get("intent") or "").strip()

    today = date.today()
    age_cut = []
    if age_min:
        age_cut.append(User.date_of_birth <= today - timedelta(days=365 * age_min))
    if age_max:
        age_cut.append(User.date_of_birth >= today - timedelta(days=365 * (age_max + 1)))

    filters = [
        User.id.not_in(excluded) if excluded else User.id != viewer.id,
        User.account_status == "active",
        # AI companions only appear in the deck when explicitly opted in (§14)
        User.is_ai.is_(False),
        User.date_of_birth.is_not(None),
        *age_cut,
    ]
    if verified_only:
        filters.append(User.is_verified.is_(True))
    if intent:
        filters.append(User.intent_mode == intent)

    pool = (User.query.filter(*filters)
            .order_by(User.id.desc()).limit(400).all())
    if city:
        pool = [u for u in pool
                if u.profile and u.profile.city
                and city.lower() in u.profile.city.lower()]

    # doc 8 §A4.1: "Milan user" on cards is killed at the source — every
    # candidate must have a display name and at least one photo.
    pool = [u for u in pool
            if u.profile and (u.profile.display_name or "").strip() and u.photos]

    ranked = rank_candidates(viewer, pool)[:DAILY_CANDIDATE_LIMIT]
    biases = preference_bias_for(
        viewer.id,
        [(user, user.photos[0].url if user.photos else None) for user, _ in ranked],
    )
    matched_ids = {
        m.user_b_id if m.user_a_id == viewer.id else m.user_a_id
        for m in _Match.query.filter(
            (_Match.user_a_id == viewer.id) | (_Match.user_b_id == viewer.id)).all()
    }
    viewer_profile = viewer.profile
    return jsonify({
        "candidates": [
            {
                **user_brief(user),
                "compatibility_score": min(99.0, score + biases.get(str(user.id), 0.0)),
                # doc 8 §A4.3: the deck always carries distance — the client
                # renders it; the ranking already consumed the raw value.
                "distance_km": _distance_for(viewer_profile, user),
                # Blur-until-mutual-interest (doc 1 §4.4): discreet users' photos
                # stay blurred to non-matches; client renders the blur state.
                "is_blurred": bool(user.discreet_mode) and user.id not in matched_ids,
                "photo_blur_preview_url": (user.photos[0].url if user.photos else None)
                    if (user.discreet_mode and user.id not in matched_ids) else None,
            }
            for user, score in ranked
        ]
    })


def _distance_for(viewer_profile, candidate) -> float | None:
    from app.services.matching_service import _haversine_km

    return _haversine_km(viewer_profile, getattr(candidate, "profile", None))


@discovery_bp.post("/calibration")
@jwt_required()
def calibration():
    """LIKE/PASS/MAYBE face-preference calibration ingest (doc 1 §4.1)."""
    viewer_id = uuid_module.UUID(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    label = data.get("label")
    target_id = data.get("target_id")
    if label not in ("like", "pass", "maybe"):
        return error_response("invalid_label", 422)
    ok = record_calibration(viewer_id, uuid_module.UUID(str(target_id)) if target_id else None,
                            data.get("photo_url") or "", label)
    if not ok:
        return error_response("calibration_failed", 422)
    return jsonify({"recorded": True})


@discovery_bp.post("/swipe")
@jwt_required()
def swipe():
    swiper = db.session.get(User, uuid_module.UUID(get_jwt_identity()))
    data = request.get_json(silent=True) or {}
    direction = data.get("direction")
    target_id = data.get("target_id")
    if direction not in ALLOWED_SWIPE_DIRECTIONS:
        return error_response("invalid_direction", 422)
    target = db.session.get(User, uuid_module.UUID(str(target_id))) if target_id else None
    if target is None:
        return error_response("target_not_found", 404)

    # Swipe economy (Tinder parity): caps enforced SERVER-SIDE against the
    # quota ledger — the client never decides.
    from app.services import swipe_economy_service

    if bool(getattr(target, "is_ai", False)) and not swiper.include_ai_in_discovery:
        # AI companions stay out of the deck unless the user opted in (§14)
        return error_response("target_not_found", 404)
    if direction in ("like", "superlike"):
        ok, reason = swipe_economy_service.check_can_like(swiper.id)
        if not ok:
            return {"error": reason, "message":
                    "You've used today's likes. Upgrade for more or come back tomorrow.",
                    "quota": swipe_economy_service.quota_snapshot(swiper.id)}, 429
    if direction == "superlike":
        ok, reason = swipe_economy_service.check_can_superlike(swiper.id)
        if not ok:
            return {"error": reason, "message": "No super likes left today.",
                    "quota": swipe_economy_service.quota_snapshot(swiper.id)}, 429

    result = record_swipe_and_match(swiper, target, direction,
                                    note=(data.get("note") or "")[:140])
    if result.get("already_swiped") is not True:
        swipe_economy_service.record_like_usage(swiper.id, direction)
    result["quota"] = swipe_economy_service.quota_snapshot(swiper.id)
    return jsonify(result)


@discovery_bp.post("/rewind")
@jwt_required()
def rewind():
    """Undo the last swipe (tier-gated count)."""
    swiper = db.session.get(User, uuid_module.UUID(get_jwt_identity()))
    from app.services import swipe_economy_service

    result = swipe_economy_service.rewind_last_swipe(swiper)
    return jsonify(result), (200 if result.get("rewound") else 403)


@discovery_bp.get("/likes-received")
@jwt_required()
def likes_received():
    """Who Liked You — identities for premium, count-only for free (Gold)."""
    from app.services import swipe_economy_service, subscription_service

    user_id = uuid_module.UUID(get_jwt_identity())
    tier = subscription_service.get_user_tier(user_id)
    premium = subscription_service.TIER_LIMITS.get(
        tier, subscription_service.TIER_LIMITS["free"]).get("top_picks", False)
    return jsonify(swipe_economy_service.who_liked_me(user_id, premium))


@discovery_bp.get("/top-picks")
@jwt_required()
def top_picks():
    from app.services import swipe_economy_service

    return jsonify(swipe_economy_service.get_top_picks(
        uuid_module.UUID(get_jwt_identity())))


@discovery_bp.post("/boost")
@jwt_required()
def boost():
    """Start a visibility boost (tier-gated; one active at a time)."""
    from app.services import swipe_economy_service

    data = request.get_json(silent=True) or {}
    result = swipe_economy_service.grant_boost(
        uuid_module.UUID(get_jwt_identity()), kind=data.get("kind") or "boost")
    return jsonify(result), (200 if result.get("granted") else 403)


@discovery_bp.get("/quota")
@jwt_required()
def quota():
    from app.services import swipe_economy_service

    return jsonify(swipe_economy_service.quota_snapshot(
        uuid_module.UUID(get_jwt_identity())))


@discovery_bp.get("/search")
@jwt_required()
def search():
    """doc 8 §C9 — search people by name, interest or city."""
    from datetime import datetime, timezone

    from app.models import Boost, Profile

    viewer = db.session.get(User, uuid_module.UUID(get_jwt_identity()))
    args = request.args
    q = (args.get("q") or "").strip()
    if not q:
        return jsonify({"results": []})
    lowered = q.lower()

    swiped_ids = {s.target_id for s in Swipe.query.filter_by(swiper_id=viewer.id).all()}
    blocked_ids = {b.blocked_id for b in Block.query.filter_by(blocker_id=viewer.id).all()} | {
        b.blocker_id for b in Block.query.filter_by(blocked_id=viewer.id).all()
    }
    excluded = swiped_ids | blocked_ids | {viewer.id}

    filters = [
        User.id.not_in(excluded) if excluded else User.id != viewer.id,
        User.account_status == "active",
        User.is_ai.is_(False),
    ]
    pool = User.query.filter(*filters).order_by(User.id.desc()).limit(400).all()
    pool = [u for u in pool if u.profile and (u.profile.display_name or "").strip() and u.photos]

    def _matches(u) -> bool:
        p = u.profile
        if lowered in (p.display_name or "").lower():
            return True
        if p.city and lowered in p.city.lower():
            return True
        return any(lowered in str(i).lower() for i in (p.interests or []))

    hits = [u for u in pool if _matches(u)][:30]
    ranked = rank_candidates(viewer, hits)
    viewer_profile = viewer.profile
    now = datetime.now(timezone.utc)
    boosted_ids = {b.user_id for b in Boost.query.filter(Boost.expires_at > now).all()}
    return jsonify({
        "results": [
            {
                **user_brief(u),
                "compatibility_score": score,
                "distance_km": _distance_for(viewer_profile, u),
                "city": getattr(u.profile, "city", None),
                "is_boosted": u.id in boosted_ids,
            }
            for u, score in ranked
        ]
    })


@discovery_bp.get("/viewed-me")
@jwt_required()
def viewed_me():
    """doc 8 §C9 — Who Viewed Me. Premium sees identities; free sees the
    count and blurred cards (same gating as Who Liked You)."""
    from datetime import datetime, timezone

    from app.models import ProfileView
    from app.services import subscription_service

    viewer_id = uuid_module.UUID(get_jwt_identity())
    tier = subscription_service.get_user_tier(viewer_id)
    premium = subscription_service.TIER_LIMITS.get(
        tier, subscription_service.TIER_LIMITS["free"]).get("top_picks", False)

    rows = (ProfileView.query.filter_by(viewed_id=viewer_id)
            .order_by(ProfileView.viewed_at.desc()).limit(200).all())
    latest_by_viewer: dict = {}
    for row in rows:
        latest_by_viewer.setdefault(row.viewer_id, row)

    results = []
    for viewer_row, latest in latest_by_viewer.items():
        user = db.session.get(User, viewer_row)
        if user is None or not user.profile or not user.photos:
            continue
        brief = user_brief(user)
        if not premium:
            brief["display_name"] = None
            brief["photo_url"] = None
        results.append({
            **brief,
            "viewed_at": latest.viewed_at.isoformat() if latest.viewed_at else None,
            "view_count": latest.view_count or 1,
        })
    results.sort(key=lambda r: r.get("viewed_at") or "", reverse=True)
    return jsonify({
        "premium": premium,
        "total_views": sum(r.view_count or 1 for r in latest_by_viewer.values()),
        "viewers": results if premium else [],
        "viewer_count": len(results),
    })


@discovery_bp.get("/kundali/<match_id>")
@jwt_required()
def kundali(match_id):
    viewer_id = uuid_module.UUID(get_jwt_identity())
    match = db.session.get(Match, uuid_module.UUID(match_id))
    if match is None or viewer_id not in (match.user_a_id, match.user_b_id):
        return error_response("match_not_found", 404)

    other_id = match.user_b_id if match.user_a_id == viewer_id else match.user_a_id
    viewer = db.session.get(User, viewer_id)
    other = db.session.get(User, other_id)
    details_a = (viewer.profile.horoscope_details if viewer.profile else None) or {}
    details_b = (other.profile.horoscope_details if other.profile else None) or {}
    if not details_a or not details_b:
        return error_response("horoscope_details_missing", 422,
                              detail="Both users must opt in with birth details.")
    try:
        narrative = groq_service.kundali_mode_narrative(details_a, details_b)
    except groq_service.GroqUnavailableError:
        return error_response("ai_unavailable_try_later", 503)
    return jsonify({
        "match_id": str(match.id),
        "narrative": narrative,
        "label": "fun_cultural_signal_not_science",
    })
