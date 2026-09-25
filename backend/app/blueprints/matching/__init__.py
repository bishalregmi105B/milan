import uuid as uuid_module

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import Match, Message, User
from app.utils.pagination import paginate
from app.utils.serializers import error_response, match_dto, user_brief

matching_bp = Blueprint("matching", __name__)


@matching_bp.get("/matches")
@jwt_required()
def list_matches():
    viewer_id = uuid_module.UUID(get_jwt_identity())
    query = Match.query.filter(
        (Match.user_a_id == viewer_id) | (Match.user_b_id == viewer_id),
        Match.is_active.is_(True),
    ).order_by(Match.matched_at.desc())
    result = paginate(query, request.args.get("page", 1, type=int), request.args.get("per_page", 20, type=int))
    matches = []
    for match in result.pop("items"):
        dto = match_dto(match, viewer_id)
        other = db.session.get(User, uuid_module.UUID(dto["other_user_id"]))
        dto["user"] = user_brief(other)
        matches.append(dto)
    return jsonify({"matches": matches, **result})


@matching_bp.get("/matches/recap/weekly")
@jwt_required()
def weekly_recap():
    """Weekly private match recap (doc 1 §4.5) — personal-only, never ranked."""
    import datetime as _dt

    from app.services import groq_service

    viewer_id = uuid_module.UUID(get_jwt_identity())
    week_ago = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=7)
    matches = Match.query.filter(
        (Match.user_a_id == viewer_id) | (Match.user_b_id == viewer_id),
        Match.matched_at >= week_ago,
    ).count()
    match_ids = [m.id for m in Match.query.filter(
        (Match.user_a_id == viewer_id) | (Match.user_b_id == viewer_id)).all()]
    sent = Message.query.filter(
        Message.match_id.in_(match_ids), Message.sender_id == viewer_id,
        Message.created_at >= week_ago).count() if match_ids else 0
    received = Message.query.filter(
        Message.match_id.in_(match_ids), Message.sender_id != viewer_id,
        Message.created_at >= week_ago).count() if match_ids else 0

    try:
        recap = groq_service.generate_weekly_recap({
            "new_matches_this_week": matches,
            "messages_sent": sent,
            "messages_received": received,
        })
    except groq_service.GroqUnavailableError:
        return error_response("ai_unavailable_try_later", 503)
    return jsonify({"recap": recap, "stats": {
        "new_matches_this_week": matches, "messages_sent": sent,
        "messages_received": received}})


@matching_bp.post("/<match_id>/voice-call-log")
@jwt_required()
def log_call(match_id):
    viewer_id = uuid_module.UUID(get_jwt_identity())
    match = db.session.get(Match, uuid_module.UUID(match_id))
    if match is None or viewer_id not in (match.user_a_id, match.user_b_id):
        return error_response("match_not_found", 404)
    # TODO(milan): persist call duration/quality metrics for abuse detection.
    return jsonify({"logged": True})


@matching_bp.post("/presence/heartbeat")
@jwt_required()
def presence_heartbeat():
    """REST twin of the `presence:heartbeat` socket event.

    The socket path is the fast one, but a client whose socket is reconnecting
    (radio switch, doze, proxy idle-kill) goes dark and shows "Active 1h ago"
    while the user is plainly in the app. This writes the same two things the
    socket handler does — the Redis online marker and last_active_at — so
    presence stays correct as long as plain HTTP works."""
    from datetime import datetime, timezone

    from app.extensions import socketio
    from app.sockets import presence_store

    viewer_id = uuid_module.UUID(get_jwt_identity())
    user = db.session.get(User, viewer_id)
    if user is None:
        return error_response("not_found", 404)

    now = datetime.now(timezone.utc)
    # Unlike a socket id this marker has no disconnect event, so it carries its
    # own short TTL — otherwise a user would look online forever after closing
    # the app. The client beats every 60s; 150s tolerates one missed beat.
    presence_store.mark_active(str(viewer_id), ttl_seconds=150)

    last = user.last_active_at
    if last is not None and not last.tzinfo:
        last = last.replace(tzinfo=timezone.utc)
    if last is None or (now - last).total_seconds() >= 60:
        user.last_active_at = now
        db.session.commit()

    socketio.emit("presence:update", {
        "user_id": str(viewer_id),
        "online": True,
        "last_active_at": now.isoformat(),
    })
    return jsonify({"ok": True, "online": True})


@matching_bp.get("/presence/<uuid:user_id>")
@jwt_required()
def presence(user_id):
    """Cold-open presence for the chat header's living indicator (doc 8 §B
    signature presence dot). Combines the Redis online set with the user's
    last_active_at so the client can show online / active minutes ago /
    last seen date without waiting for a socket broadcast."""
    from datetime import datetime, timezone

    from app.sockets import presence_store

    user = db.session.get(User, user_id)
    if user is None:
        return error_response("not_found", 404)
    online = presence_store.is_online(str(user_id))
    last_active = getattr(user, "last_active_at", None)
    if last_active is not None and not last_active.tzinfo:
        last_active = last_active.replace(tzinfo=timezone.utc)
    minutes_ago = None
    if last_active is not None:
        minutes_ago = int((datetime.now(timezone.utc) - last_active).total_seconds() // 60)
    return jsonify({
        "user_id": str(user_id),
        "online": online,
        "last_active_at": last_active.isoformat() if last_active else None,
        "minutes_ago": minutes_ago,
    })
