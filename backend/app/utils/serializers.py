import uuid

from flask import jsonify


# Single source of truth for user-facing error copy. Every error_response()
# call sends a stable machine `error` code plus this controlled `message` so
# clients can show human text without hard-coding strings per endpoint.
ERROR_MESSAGES = {
    "invalid_phone": "That phone number doesn't look right. Use a Nepali mobile number like 98XXXXXXXX.",
    "invalid_email": "That email address doesn't look right. Check it and try again.",
    "identifier_required": "Enter your phone number or email to continue.",
    "sms_send_failed": "We couldn't send the SMS code right now. Please try again in a moment.",
    "email_send_failed": "We couldn't send the email code right now. Please try again in a moment.",
    "invalid_or_expired_otp": "That code is invalid or has expired. Request a new one and try again.",
    "onboarding_required": "Finish age verification and profile setup before continuing.",
    "google_not_configured": "Google sign-in is not available right now. Use OTP or try again later.",
    "otp_temporarily_unavailable": "We couldn't send a code right now. Please try again shortly.",
    "rate_limited": "Too many code requests. Wait a little before trying again.",
    "age_gate_18_plus": "You must be 18 or older to join Milan.",
    "invalid_date_format": "That birth date isn't valid. Use the date picker (YYYY-MM-DD).",
    "account_suspended": "This account has been suspended. Contact support if you think this is a mistake.",
    "display_name_required": "Add a display name before saving your profile.",
    "display_name_profanity": "That name has language we don't allow. Pick another.",
    "bio_profanity": "Your text has language we don't allow. Rewrite and save again.",
    "selfie_required": "Take a live selfie so we can verify it's really you.",
    "notes_required": "Tell us a little about yourself first, then we'll draft your bio.",
    "answer_required": "Write your prompt answer first, then get feedback.",
    "qa_pairs_required": "Answer at least one interview question.",
    "url_required": "Upload the media first, then save.",
    "max_photos_reached": "You've reached the maximum of 6 photos.",
    "not_found": "We couldn't find what you were looking for.",
    "internal_error": "Something went wrong on our side. Please try again.",
    "forbidden": "You don't have access to do that.",
    "invalid_target_id": "That report target is invalid. Refresh and try again.",
    "invalid_target_ref": "That report reference is invalid. Refresh and try again.",
    "invalid_target_type": "That report target type is not supported.",
    "invalid_or_missing_token": "Your session expired. Sign in again to continue.",
    "signed_out": "You're signed out. Sign in to continue.",
    "network_error": "Can't reach Milan's servers. Check your connection and try again.",
    "unknown_error": "Something went wrong. Please try again.",
    "key_exists": "That key is already in use — pick a different one.",
    "horoscope_details_missing": "Add your birth date, time, and place to open Kundali Mode.",
}


def _humanize(code: str) -> str:
    """Fallback for unmapped codes: 'some_code_here' -> 'Some code here.'"""
    text = (code or "").replace("_", " ").replace("-", " ").strip()
    if not text:
        return ERROR_MESSAGES["unknown_error"]
    return text[0].upper() + text[1:] + "."


def error_response(code: str, status: int = 400, message: str | None = None, **extra):
    payload = {
        "error": code,
        "message": message or ERROR_MESSAGES.get(code) or _humanize(code),
    }
    payload.update(extra)
    return jsonify(payload), status


def ok_response(**data):
    return jsonify(data), 200


def parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def user_brief(user) -> dict:
    profile = getattr(user, "profile", None)
    photo = user.photos[0].url if user.photos else None
    is_ai = bool(getattr(user, "is_ai", False))
    return {
        "id": str(user.id),
        # AI disclosure lives in the name plus this flag — the ONE place a
        # companion differs from a human profile (§14). Everything else about
        # the payload, the inbox row and the chat screen is identical.
        "display_name": _display_name(profile, is_ai),
        "raw_name": profile.display_name if profile else None,
        "is_ai": is_ai,
        "photo_url": photo,
        "is_verified": user.is_verified,
        "trust_score": getattr(user, "trust_score", None),
        "intent_mode": user.intent_mode,
        "city": getattr(profile, "city", None),
        "age": _age_from_dob(getattr(user, "date_of_birth", None)),
        "languages": getattr(profile, "languages", None) or [],
    }


def _display_name(profile, is_ai: bool = False) -> str | None:
    """doc 8 §E: no `· AI` suffix on any surface. Companions carry the
    machine-readable `is_ai` flag; disclosure lives on the profile screen."""
    return profile.display_name if profile else None


def _age_from_dob(dob) -> int | None:
    if dob is None:
        return None
    import datetime as _dt

    today = _dt.date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def match_dto(match, viewer_id: uuid.UUID) -> dict:
    from app.models import Message

    other_id = match.user_b_id if match.user_a_id == viewer_id else match.user_a_id
    last = (Message.query.filter_by(match_id=match.id)
            .order_by(Message.created_at.desc()).first())
    unread = Message.query.filter(
        Message.match_id == match.id,
        Message.sender_id != viewer_id,
        Message.read_at.is_(None),
    ).count()
    return {
        "id": str(match.id),
        "other_user_id": str(other_id),
        "matched_at": match.matched_at.isoformat() if match.matched_at else None,
        "compatibility_score": match.compatibility_score,
        "match_reason_text": match.match_reason_text,
        # human | companion — clients use this only for the AI badge, never to
        # pick a different chat screen.
        "kind": getattr(match, "kind", "human"),
        "last_message": last.body if last else None,
        "last_message_at": last.created_at.isoformat() if last else None,
        "unread_count": unread,
    }
