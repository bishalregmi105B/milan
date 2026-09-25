import uuid as uuid_module
from datetime import datetime, timezone

from flask import request

from app.extensions import db, socketio
from app.models import User


def _socket_user_id() -> str | None:
    """Identity for socket events ALWAYS comes from the JWT captured at
    handshake (stored in the flask_socketio session by chat_events.on_connect)
    — never from the event payload, which a client could spoof."""
    from flask import session as flask_session

    try:
        return flask_session.get("user_id")
    except Exception:
        return None


def register_presence_events(io):
    @io.on("presence:heartbeat")
    def on_heartbeat(data):
        user_id = _socket_user_id()
        if not user_id:
            return {"ok": False}
        from flask_socketio import join_room

        from app.sockets import presence_store

        presence_store.register_connection(user_id, request.sid)
        join_room(f"user:{user_id}")
        io.emit("presence:update", {"user_id": user_id, "online": True,
                                    "last_active_at": (data or {}).get("at")})
        # last_active_at feeds discovery's activity-recency signal (§C8) —
        # throttle the write to at most one per minute per user.
        _touch_last_active(user_id)
        return {"ok": True}

    @io.on("disconnect")
    def on_disconnect():
        user_id = _socket_user_id()
        if not user_id:
            return
        from app.sockets import presence_store

        presence_store.remove_connection(user_id, request.sid)
        try:
            if not presence_store.is_online(user_id):
                io.emit("presence:update", {"user_id": user_id, "online": False})
        except Exception:
            pass


def _touch_last_active(user_id: str) -> None:
    """Write-through of activity, at most once a minute (heartbeat cadence is
    the client's choice — the DB write is ours to bound)."""
    now = datetime.now(timezone.utc)
    try:
        user = db.session.get(User, uuid_module.UUID(user_id))
    except (ValueError, TypeError):
        return
    if user is None:
        return
    last = user.last_active_at
    if last is not None:
        last = last if last.tzinfo else last.replace(tzinfo=timezone.utc)
        if (now - last).total_seconds() < 60:
            return
    user.last_active_at = now
    db.session.commit()
