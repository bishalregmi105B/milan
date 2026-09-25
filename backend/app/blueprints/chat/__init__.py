import uuid as uuid_module
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db, limiter
from app.models import Match, Message, Snap, User
from app.services import groq_service
from app.services.moderation_service import scan_message_deep, screen_inbound_message
from app.utils.pagination import paginate
from app.utils.serializers import error_response

chat_bp = Blueprint("chat", __name__)


def _participant_or_404(match_id: str, viewer_id):
    try:
        mid = uuid_module.UUID(match_id)
    except (ValueError, AttributeError):
        return None, None
    match = db.session.get(Match, mid)
    if match is None or viewer_id not in (match.user_a_id, match.user_b_id):
        return None, None
    other_id = match.user_b_id if match.user_a_id == viewer_id else match.user_a_id
    return match, other_id


@chat_bp.get("/<match_id>/messages")
@jwt_required()
def history(match_id):
    viewer_id = uuid_module.UUID(get_jwt_identity())
    match, _other = _participant_or_404(match_id, viewer_id)
    if match is None:
        return error_response("match_not_found", 404)
    query = Message.query.filter_by(match_id=match.id).order_by(Message.created_at.desc())
    result = paginate(query, request.args.get("page", 1, type=int), request.args.get("per_page", 50, type=int))
    messages = [{
        "id": str(m.id),
        "sender_id": str(m.sender_id),
        "body": m.body,
        "media_url": m.media_url,
        "media_type": m.media_type,
        "is_ai_suggested": m.is_ai_suggested,
        "read_at": m.read_at.isoformat() if m.read_at else None,
        "created_at": m.created_at.isoformat(),
    } for m in reversed(result.pop("items"))]
    return jsonify({"messages": messages, **result})


@chat_bp.post("/<match_id>/messages")
@jwt_required()
@limiter.limit("60 per minute")
def send_message(match_id):
    sender_id = uuid_module.UUID(get_jwt_identity())
    match, _other = _participant_or_404(match_id, sender_id)
    if match is None:
        return error_response("match_not_found", 404)

    data = request.get_json(silent=True) or {}
    body = (data.get("body") or "").strip()
    media_url = data.get("media_url")
    # doc 8 §A2.12: image | gif | audio — the client picks the renderer by it.
    media_type = ((data.get("media_type") or "").strip() or None)
    is_ai_suggested = bool(data.get("is_ai_suggested", False))
    if not body and not media_url:
        return error_response("empty_message", 422)
    if media_type and media_type not in ("image", "gif", "audio"):
        return error_response("invalid_media_type", 422)

    screen = screen_inbound_message(body) if body else {"flagged": False, "deferred": False}
    if screen["flagged"]:
        return error_response("message_blocked_by_moderation", 422, categories=screen["categories"])

    message = Message(
        match_id=match.id,
        sender_id=sender_id,
        body=body or None,
        media_url=media_url,
        media_type=media_type,
        is_ai_suggested=is_ai_suggested,
    )
    db.session.add(message)
    # doc 8 §C9: any message permanently clears the 72h match-expiry window.
    match.last_activity_at = db.func.now()
    db.session.commit()

    if screen.get("deferred") or not screen["flagged"]:
        from app.extensions import dispatch
        from app.tasks.moderation_tasks import scan_message_async

        dispatch(scan_message_async, str(message.id))

    from app.sockets.chat_events import broadcast_message

    broadcast_message(match_id, {
        "id": str(message.id),
        "sender_id": str(sender_id),
        "body": message.body,
        "media_url": message.media_url,
        "media_type": message.media_type,
        "created_at": message.created_at.isoformat(),
        "is_ai_suggested": message.is_ai_suggested,
    })

    # Offline recipients learn about messages via push (queue_notification
    # applies per-category daily caps + quiet predictions internally).
    if body:
        from app.services.notification_service import queue_notification

        sender = db.session.get(User, sender_id)
        sender_name = (sender.profile.display_name if sender and sender.profile
                       else "Your match")
        other_id = (match.user_b_id if match.user_a_id == sender_id
                    else match.user_a_id)
        preview = body[:80]
        queue_notification(
            other_id, "messages",
            f"{sender_name}",
            preview,
            data={"type": "message", "match_id": str(match.id)},
        )

    # §14: a companion match is an ordinary match — the reply is generated
    # off the request path and delivered through the socket room.
    companion_reply = None
    if getattr(match, "kind", "human") == "companion" and body:
        companion_reply = _companion_reply(match, sender_id, body, data)

    payload = {"id": str(message.id), "status": "sent"}
    if companion_reply:
        payload["companion_reply"] = companion_reply
        payload["companion_pending"] = bool(companion_reply.get("pending"))
    return jsonify(payload), 201


def _companion_reply(match, human_id, body: str, data: dict) -> dict:
    """Generate the companion's reply inline and return it in the HTTP response.

    The reply used to be produced by a fire-and-forget Celery task and delivered
    ONLY over the socket, so a single dropped `chat:message` left the user
    staring at a "typing…" bubble that never resolved — the reply landed in the
    database but appeared in the app only after a manual refresh.

    Now it is generated synchronously: the model call is a few seconds and the
    eventlet worker yields during it, so the request is not really blocked. The
    reply is returned here for the sender AND broadcast over the socket room for
    any other device and the inbox row. The HTTP response is the source of
    truth; the socket is a bonus, not a requirement."""
    from app.models import SaathiMessage
    from app.services import companion_account_service

    session = companion_account_service.session_for_match(match)
    if session is None:
        return {}

    regenerate_variant = int(data.get("regenerate_variant") or 0)
    tone_chip = (data.get("tone_chip") or "").strip().lower() or None

    # Mirror the user's turn into her memory before generating (skipped on a
    # regenerate — re-rolling her reply is not a new user turn).
    if regenerate_variant == 0:
        db.session.add(SaathiMessage(session_id=session.id, role="user",
                                     content=body))
        db.session.commit()

    try:
        result = groq_service.saathi_respond_full(
            str(session.id), str(session.character_id), body,
            regenerate_variant=regenerate_variant, tone_chip=tone_chip,
            defer_user_mirror=True, reactive=True)
    except groq_service.GroqUnavailableError:
        result = {"reply": groq_service.DEGRADED_SAATHI_MESSAGE,
                  "segments": [groq_service.DEGRADED_SAATHI_MESSAGE],
                  "degraded": True}

    from app.blueprints.saathi import (_extract_open_loops,
                                       _summarize_into_memory,
                                       apply_bond_progress)

    apply_bond_progress(session)
    envelopes = companion_account_service.persist_companion_reply(
        match, session, result, pace=False)

    # Turn-milestone housekeeping (memory + open loops), same cadence the
    # standalone Saathi surface uses, so both chat paths stay in step.
    from flask import current_app as _app

    if (regenerate_variant == 0 and session.turn_count > 0
            and session.turn_count % _app.config["SAATHI_MEMORY_SUMMARY_EVERY_TURNS"] == 0):
        _summarize_into_memory(session)
        _extract_open_loops(session)

    return {"messages": envelopes,
            "segments": result.get("segments") or [],
            "typing_delay_seconds": result.get("typing_delay_seconds", 0.0)}


@chat_bp.post("/<match_id>/icebreakers")
@jwt_required()
@limiter.limit("15 per hour")
def icebreakers(match_id):
    viewer_id = uuid_module.UUID(get_jwt_identity())
    match, other_id = _participant_or_404(match_id, viewer_id)
    if match is None:
        return error_response("match_not_found", 404)
    other = db.session.get(User, other_id)
    from app.services.matching_service import _shared_interests

    context = {
        "match_reason_text": match.match_reason_text or "",
        "shared_interest_tags": _shared_interests(
            db.session.get(User, viewer_id).profile, other.profile),
        "conversation_style": getattr(other.profile, "conversation_style", None) if other.profile else None,
    }
    try:
        suggestions = groq_service.suggest_icebreakers(context)
    except groq_service.GroqUnavailableError:
        return jsonify({"suggestions": []})
    return jsonify({"suggestions": suggestions})


@chat_bp.post("/<match_id>/snaps")
@jwt_required()
def send_snap(match_id):
    sender_id = uuid_module.UUID(get_jwt_identity())
    match, _other = _participant_or_404(match_id, sender_id)
    if match is None:
        return error_response("match_not_found", 404)
    data = request.get_json(silent=True) or {}
    media_url = data.get("media_url")
    view_mode = data.get("view_mode", "single_view")
    if not media_url:
        return error_response("media_url_required", 422)
    if view_mode not in ("single_view", "24h"):
        return error_response("invalid_view_mode", 422)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(hours=24) if view_mode == "24h"
        else datetime.now(timezone.utc) + timedelta(days=7)
    )
    snap = Snap(match_id=match.id, sender_id=sender_id, media_url=media_url,
                view_mode=view_mode, expires_at=expires_at)
    db.session.add(snap)
    db.session.commit()
    return jsonify({"id": str(snap.id), "expires_at": expires_at.isoformat()}), 201


def _snap_for_viewer(snap_id: str, viewer_id):
    """IDOR guard: resolve a snap only if the caller is a participant of its
    match. Returns (snap, None) or (None, error_response)."""
    try:
        snap = db.session.get(Snap, uuid_module.UUID(snap_id))
    except (ValueError, AttributeError):
        return None, error_response("snap_not_found", 404)
    if snap is None:
        return None, error_response("snap_not_found", 404)
    match = db.session.get(Match, snap.match_id)
    if match is None or viewer_id not in (match.user_a_id, match.user_b_id):
        return None, error_response("snap_not_found", 404)
    return snap, None


@chat_bp.post("/snaps/<snap_id>/viewed")
@jwt_required()
def mark_snap_viewed(snap_id):
    viewer_id = uuid_module.UUID(get_jwt_identity())
    snap, err = _snap_for_viewer(snap_id, viewer_id)
    if err is not None:
        return err
    snap.viewed_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"ok": True})


@chat_bp.post("/snaps/<snap_id>/screenshot")
@jwt_required()
def report_snap_screenshot(snap_id):
    viewer_id = uuid_module.UUID(get_jwt_identity())
    snap, err = _snap_for_viewer(snap_id, viewer_id)
    if err is not None:
        return err
    snap.screenshot_detected = True
    db.session.commit()

    from app.services.notification_service import queue_notification

    queue_notification(
        snap.sender_id, "messages",
        "Screenshot detected",
        "Someone took a screenshot of your disappearing snap.",
    )
    return jsonify({"ok": True})


@chat_bp.post("/<match_id>/share-date")
@jwt_required()
def share_date(match_id):
    viewer_id = uuid_module.UUID(get_jwt_identity())
    match, _other = _participant_or_404(match_id, viewer_id)
    if match is None:
        return error_response("match_not_found", 404)
    data = request.get_json(silent=True) or {}
    required = ["contact_name", "contact_phone", "date_time", "location"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return error_response("missing_fields", 422, fields=missing)

    from app.services.notification_service import queue_notification
    from app.utils.sms import send_sms

    queue_notification(
        viewer_id, "social",
        "Date shared",
        f"Your date plan at {data['location']} was shared with {data['contact_name']}.",
        data={"share_my_date": data},
    )
    # Trusted-contact SMS (doc 1 §4.4): who/when/where + live-location opt-in flag.
    live_note = " (live location ON)" if data.get("live_location") else ""
    send_sms(
        str(data["contact_phone"]),
        f"[Milan] {data['contact_name']}: your friend has a date at "
        f"{data['location']} on {data['date_time']}{live_note}. "
        f"Track: milan.app/date/{match_id[:8]}",
    )
    return jsonify({"ok": True}), 201


@chat_bp.post("/<match_id>/read")
@jwt_required()
def mark_read(match_id):
    viewer_id = uuid_module.UUID(get_jwt_identity())
    match, _other = _participant_or_404(match_id, viewer_id)
    if match is None:
        return error_response("match_not_found", 404)
    now = datetime.now(timezone.utc)
    updated = Message.query.filter(
        Message.match_id == match.id,
        Message.sender_id != viewer_id,
        Message.read_at.is_(None),
    ).update({"read_at": now}, synchronize_session=False)
    db.session.commit()
    return jsonify({"marked": updated})
