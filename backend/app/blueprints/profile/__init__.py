import uuid as uuid_module

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db, limiter
from app.models import (Photo, Profile, SaathiSession, User, VideoIntro)
from app.services import groq_service, media_service, text_filter
from app.services.verification_service import submit_liveness_check
from app.utils.serializers import error_response
from app.utils.validators import validate_age_18

profile_bp = Blueprint("profile", __name__)


def current_user() -> User | None:
    return db.session.get(User, uuid_module.UUID(get_jwt_identity()))


@profile_bp.get("/me")
@jwt_required()
def get_me():
    user = current_user()
    # Session-restore path hits this before onboarding finishes — never 500
    # on a missing profile row; return an empty scaffold instead.
    profile = user.profile
    if profile is None:
        profile = Profile(user_id=user.id, display_name="")
    from app.services.subscription_service import get_user_tier

    return jsonify({
        "tier": get_user_tier(user.id),
        "user": {
            "id": str(user.id),
            "phone": user.phone,
            "email": user.email,
            "is_verified": user.is_verified,
            "intent_mode": user.intent_mode,
            "discreet_mode": user.discreet_mode,
            "language": user.language,
            "data_saver": user.data_saver,
            "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
            "gender": user.gender,
            # AI-companion disclosure consent (persisted per account, so the
            # intro is shown once ever — not once per session)
            "saathi_intro_accepted_at": (user.saathi_intro_accepted_at.isoformat()
                                         if user.saathi_intro_accepted_at else None),
            "saathi_terms_version": user.saathi_terms_version,
            "include_ai_in_discovery": user.include_ai_in_discovery,
        },
        "profile": {
            "display_name": profile.display_name if profile else None,
            "bio": profile.bio if profile else None,
            "interests": profile.interests if profile else [],
            "city": profile.city if profile else None,
            "conversation_style": profile.conversation_style if profile else None,
            "relationship_intent": profile.relationship_intent if profile else None,
            "horoscope_details": profile.horoscope_details if profile else None,
            "ethnicity": profile.ethnicity if profile else None,
            "religion": profile.religion if profile else None,
            "profession": profile.profession if profile else None,
            "lifestyle_tags": profile.lifestyle_tags if profile else [],
            "values_tags": profile.values_tags if profile else [],
            "dealbreakers": profile.dealbreakers if profile else [],
            "primary_script": profile.primary_script if profile else None,
            "languages": profile.languages if profile else [],
            "dialect": profile.dialect if profile else None,
            "mother_tongue": profile.mother_tongue if profile else None,
            "hometown": profile.hometown if profile else None,
            "education": profile.education if profile else None,
            "height_cm": profile.height_cm if profile else None,
            "diet": profile.diet if profile else None,
            "smoking": profile.smoking if profile else None,
            "drinking": profile.drinking if profile else None,
            "hidden_fields": profile.hidden_fields if profile else [],
            "prompts": profile.prompts if profile else [],
            "photos": [{"id": str(p.id), "url": p.url, "order_index": p.order_index,
                        "moderation_status": p.moderation_status} for p in user.photos],
            "video_intro": ({"url": user.video_intro.url} if user.video_intro else None),
        },
    })


@profile_bp.put("/me")
@jwt_required()
def update_me():
    user = current_user()
    data = request.get_json(silent=True) or {}

    profile = user.profile or Profile(user_id=user.id, display_name="")
    allowed = {"display_name", "bio", "interests", "city", "latitude", "longitude",
               "conversation_style", "relationship_intent", "ethnicity", "religion",
               "profession", "lifestyle_tags", "values_tags", "dealbreakers",
               "horoscope_details",
               # language identity + search-filter fields (§14, §11)
               "primary_script", "languages", "dialect", "mother_tongue",
               "speech_markers", "hometown", "education", "height_cm",
               "diet", "smoking", "drinking", "hidden_fields", "prompts"}
    for field in allowed:
        if field in data:
            setattr(profile, field, data[field])
    # doc 8 §C9: interests arrive as catalog keys (or legacy free text, which
    # normalize_interests maps onto keys where it can) — deduped and capped.
    if "interests" in data:
        from app.services.interests_catalog import normalize_interests

        profile.interests = normalize_interests(data["interests"])
    if "discreet_mode" in data:
        user.discreet_mode = bool(data["discreet_mode"])
    if "intent_mode" in data:
        user.intent_mode = data["intent_mode"]
    if "gender" in data and data["gender"] in ("female", "male", "nonbinary", "other"):
        user.gender = data["gender"]
    if "language" in data:
        user.language = data["language"]
    if "data_saver" in data:
        user.data_saver = bool(data["data_saver"])
    if "include_ai_in_discovery" in data:
        user.include_ai_in_discovery = bool(data["include_ai_in_discovery"])
    # doc 8 §C9: profanity filter on identity surfaces. Display names reject
    # rough language too; bios/prompts only reject the hard belt.
    if "display_name" in data:
        verdict = text_filter.screen(str(data["display_name"] or ""), allow_rough=False)
        if not verdict["ok"]:
            return error_response("display_name_profanity", 422)
    for free_text_field in ("bio", "prompts"):
        if free_text_field in data and data[free_text_field]:
            blob = data[free_text_field]
            if isinstance(blob, list):
                blob = " ".join(str(item) for item in blob)
            verdict = text_filter.screen(str(blob))
            if not verdict["ok"]:
                return error_response("bio_profanity", 422)
    if not profile.display_name:
        return error_response("display_name_required", 422)
    db.session.add(profile)
    db.session.commit()
    from app.services import trust_service

    trust_service.refresh(user)
    return jsonify({"updated": True})


@profile_bp.post("/photos")
@jwt_required()
def add_photo():
    user = current_user()
    if len(user.photos) >= 6:
        return error_response("max_photos_reached", 422)
    data = request.get_json(silent=True) or {}
    url = data.get("url")
    if not url:
        return error_response("url_required", 422)
    photo = Photo(user_id=user.id, url=url, order_index=len(user.photos))
    db.session.add(photo)
    db.session.commit()
    from app.services.moderation_service import moderate_media_asset

    moderate_media_asset(subject_type="photo", subject_id=photo.id, media_url=url)
    return jsonify({"id": str(photo.id), "moderation_status": "pending"}), 201


@profile_bp.post("/video-intro")
@jwt_required()
def add_video_intro():
    user = current_user()
    data = request.get_json(silent=True) or {}
    url = data.get("url")
    if not url:
        return error_response("url_required", 422)
    intro = user.video_intro or VideoIntro(user_id=user.id, url=url)
    intro.url = url
    db.session.add(intro)
    db.session.commit()
    media_service.trigger_video_transcode(url)
    return jsonify({"ok": True}), 201


@profile_bp.post("/bio/generate")
@jwt_required()
@limiter.limit("10 per hour")
def generate_bio():
    user = current_user()
    data = request.get_json(silent=True) or {}
    notes = (data.get("notes") or "").strip()
    language = data.get("language", user.language)
    if not notes:
        return error_response("notes_required", 422)
    tags = {}
    if user.profile:
        tags = {
            "lifestyle_tags": user.profile.lifestyle_tags,
            "values_tags": user.profile.values_tags,
            "relationship_intent": user.profile.relationship_intent,
        }
    try:
        drafts = groq_service.generate_bio(notes, tags, language)
    except ValueError as exc:
        return error_response(str(exc), 422)
    except groq_service.GroqUnavailableError:
        return error_response("ai_unavailable_try_later", 503)
    return jsonify({"drafts": drafts})


@profile_bp.post("/prompts/feedback")
@jwt_required()
@limiter.limit("30 per hour")
def prompt_feedback():
    data = request.get_json(silent=True) or {}
    answer = (data.get("answer") or "").strip()
    if not answer:
        return error_response("answer_required", 422)
    try:
        result = groq_service.grade_prompt(answer)
    except groq_service.GroqUnavailableError:
        return error_response("ai_unavailable_try_later", 503)
    return jsonify(result)


verification_bp = Blueprint("verification", __name__, url_prefix="/verification")


@verification_bp.post("/liveness")
@jwt_required()
def liveness():
    user = current_user()
    file = request.files.get("selfie")
    if file is None:
        return error_response("selfie_required", 422)
    selfie_bytes = file.read()
    result = submit_liveness_check(user, selfie_bytes)
    del selfie_bytes
    status = 200 if result.get("passed") else 422
    return jsonify(result), status


@profile_bp.post("/interview/signal")
@jwt_required()
@limiter.limit("30 per hour")
def interview_signal():
    """Structured extraction from conversational-interview answers (doc 5 §3.1).
    Accepts partial batches so a dropped connection never loses progress."""
    import uuid as uuid_module

    user = db.session.get(User, uuid_module.UUID(get_jwt_identity()))
    data = request.get_json(silent=True) or {}
    qa_pairs = data.get("qa_pairs") or []
    if not qa_pairs:
        return error_response("qa_pairs_required", 422)
    try:
        signal = groq_service.extract_interview_signal(qa_pairs)
    except ValueError as exc:
        return error_response(str(exc), 422)
    except groq_service.GroqUnavailableError:
        return error_response("ai_unavailable_try_later", 503)

    if not signal and not data.get("partial"):
        return jsonify({"signal": {}})

    profile = user.profile or Profile(user_id=user.id, display_name="")
    mapping = {
        "relationship_intent": "relationship_intent",
        "conversation_style": "conversation_style",
    }
    for json_field, column in mapping.items():
        value = signal.get(json_field)
        if value:
            setattr(profile, column, str(value)[:32])
    for list_field in ("lifestyle_tags", "values_tags", "dealbreakers"):
        values = signal.get(list_field)
        if isinstance(values, list):
            merged = list({*getattr(profile, list_field), *values})
            setattr(profile, list_field, [str(v) for v in merged][:20])
    if not data.get("partial"):
        from app.models.base import utcnow

        profile.interview_completed_at = utcnow()
    db.session.add(profile)
    db.session.commit()
    return jsonify({"signal": signal})


# ---------------------------------------------------------------------------
# AI-companion disclosure consent (§3.2 of the build brief): persisted per
# ACCOUNT so the "Meet Saathi" intro appears once, ever — re-shown only when
# the terms version changes. No auto-accept anywhere.
# ---------------------------------------------------------------------------

SAATHI_TERMS_VERSION = "2026-09-01"


@profile_bp.get("/saathi-consent")
@jwt_required()
def get_saathi_consent():
    user = current_user()
    accepted = (user.saathi_intro_accepted_at is not None
                and user.saathi_terms_version == SAATHI_TERMS_VERSION)
    return jsonify({
        "accepted": accepted,
        "accepted_at": (user.saathi_intro_accepted_at.isoformat()
                        if user.saathi_intro_accepted_at else None),
        "accepted_version": user.saathi_terms_version,
        "current_version": SAATHI_TERMS_VERSION,
    })


@profile_bp.post("/saathi-consent")
@jwt_required()
def accept_saathi_consent():
    """Records the explicit 18+ / not-a-real-person acknowledgment. The server
    verifies age from the account DOB; a checkbox alone is insufficient."""
    user = current_user()
    if user.date_of_birth is None or not validate_age_18(user.date_of_birth):
        return error_response("age_gate_18_plus", 403)
    data = request.get_json(silent=True) or {}
    if data.get("confirm_18") is not True:
        return error_response("age_confirmation_required", 422)
    from app.models.base import utcnow

    user.saathi_intro_accepted_at = utcnow()
    user.saathi_terms_version = SAATHI_TERMS_VERSION
    db.session.commit()
    return jsonify({
        "accepted": True,
        "accepted_at": user.saathi_intro_accepted_at.isoformat(),
        "current_version": SAATHI_TERMS_VERSION,
    })


@profile_bp.delete("/saathi-consent")
@jwt_required()
def revoke_saathi_consent():
    """Withdraw Saathi access immediately and stop future proactive messages."""
    user = current_user()
    user.saathi_intro_accepted_at = None
    user.saathi_terms_version = None
    SaathiSession.query.filter_by(user_id=user.id).update(
        {"is_paused": True, "proactive_opt_in": False},
        synchronize_session=False,
    )
    db.session.commit()
    return jsonify({"accepted": False, "revoked": True})


@profile_bp.post("/phone")
@jwt_required()
def add_phone():
    """Attach (or replace) a phone number on an email-first account. The new
    number must verify by OTP before it is stored — same proof as signup."""
    user = current_user()
    if user.phone:
        return error_response("phone_already_set", 409,
                              message="A phone number is already linked to this account.")
    data = request.get_json(silent=True) or {}
    phone = (data.get("phone") or "").strip()
    code = (data.get("code") or "").strip()
    from app.utils.validators import normalize_phone

    try:
        phone = normalize_phone(phone)
    except ValueError:
        return error_response("invalid_phone", 422)
    from app.utils.otp import verify_stored_otp

    if not code or not verify_stored_otp(phone, code):
        return error_response("invalid_or_expired_otp", 401)
    if User.query.filter_by(phone=phone).first():
        return error_response("phone_in_use", 409)
    user.phone = phone
    db.session.commit()
    return jsonify({"linked": True, "phone": phone})


@profile_bp.post("/phone/request-otp")
@jwt_required()
@limiter.limit("5 per hour")
def add_phone_request_otp():
    """Kick off the OTP for linking a phone to an existing account."""
    from app.utils.otp import send_sms_otp, store_otp
    from app.utils.validators import normalize_phone

    data = request.get_json(silent=True) or {}
    try:
        phone = normalize_phone((data.get("phone") or "").strip())
    except ValueError:
        return error_response("invalid_phone", 422)
    import secrets

    code = str(secrets.randbelow(10 ** 6)).zfill(6)
    store_otp(phone, code)
    sent = send_sms_otp(phone, code)
    if not sent:
        return error_response("sms_send_failed", 502)
    return jsonify({"sent": True})


@profile_bp.get("/<uuid:user_id>/public")
@jwt_required()
def public_profile(user_id):
    """doc 8 Part D.7 — the public view of a profile (deck tap-through).
    Honours `hidden_fields`, blurs discreet users, and records a ProfileView
    so "Who viewed me" (doc 8 §C9) has real data behind it."""
    from datetime import datetime, timezone

    from app.models import ProfileView
    from app.utils.serializers import user_brief

    viewer_id = uuid_module.UUID(get_jwt_identity())
    subject = db.session.get(User, user_id)
    if subject is None or subject.id == viewer_id:
        return error_response("not_found", 404)
    profile = subject.profile
    if profile is None:
        return error_response("not_found", 404)

    hidden = set(profile.hidden_fields or [])
    photos = [p.url for p in subject.photos if p.url]
    is_blurred = bool(subject.discreet_mode)

    payload = {
        **user_brief(subject),
        "bio": None if "bio" in hidden else profile.bio,
        "city": None if "city" in hidden else profile.city,
        "profession": None if "profession" in hidden else profile.profession,
        "education": None if "education" in hidden else profile.education,
        "height_cm": None if "height_cm" in hidden else profile.height_cm,
        "relationship_intent": profile.relationship_intent,
        "conversation_style": profile.conversation_style,
        "interests": profile.interests or [],
        "lifestyle_tags": [] if "lifestyle_tags" in hidden else (profile.lifestyle_tags or []),
        "values_tags": [] if "values_tags" in hidden else (profile.values_tags or []),
        "prompts": profile.prompts or [],
        "photos": photos,
        "photo_count": len(photos),
        "is_blurred": is_blurred,
        "last_active_at": subject.last_active_at.isoformat()
            if getattr(subject, "last_active_at", None) else None,
    }

    # ProfileView upsert — one row per (viewer, viewed), newest view wins.
    if not bool(getattr(subject, "is_ai", False)):
        row = ProfileView.query.filter_by(viewer_id=viewer_id, viewed_id=subject.id).first()
        now = datetime.now(timezone.utc)
        if row is None:
            db.session.add(ProfileView(
                viewer_id=viewer_id, viewed_id=subject.id, viewed_at=now, view_count=1))
        else:
            row.viewed_at = now
            row.view_count = (row.view_count or 1) + 1
        db.session.commit()

    return jsonify(payload)


@profile_bp.get("/interests/catalog")
@jwt_required()
def interests_catalog():
    """doc 8 §C9 — the canonical interest taxonomy for the picker, grouped by
    category. Lazily seeds the Interest table (same pattern as the companion
    roster seeding)."""
    from app.models import Interest
    from app.services.interests_catalog import CATEGORY_ORDER, ensure_seeded

    ensure_seeded()
    rows = Interest.query.filter_by(is_active=True).order_by(Interest.category, Interest.label).all()
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row.category or "other", []).append({
            "key": row.key,
            "label": row.label,
            "label_ne": row.label_ne,
            "icon": row.icon,
        })
    ordered = {cat: grouped[cat] for cat in CATEGORY_ORDER if cat in grouped}
    for extra, items in grouped.items():
        ordered.setdefault(extra, items)
    return jsonify({"categories": ordered})
