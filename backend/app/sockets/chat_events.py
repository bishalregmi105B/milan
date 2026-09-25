import logging
import time

from flask import request

from app.extensions import db, socketio

logger = logging.getLogger(__name__)

_room_last_typing: dict[str, float] = {}
TYPING_DEBOUNCE_SECONDS = 2.0


def register_chat_events(io):
    @io.on("connect")
    def on_connect(auth=None):
        """The client sends its JWT via handshake auth (`setAuth({'token': …})`).
        Decode it once here and keep the identity on the socket session so
        later events — typing, presence — never need a token in the payload
        (doc 8 §C9). Connections without a valid token are rejected."""
        token = (auth or {}).get("token") if isinstance(auth, dict) else None
        token = token or request.args.get("token")
        claims = _decode_claims(token)
        if not claims or not claims.get("sub"):
            logger.warning("socket connect rejected: no valid token")
            return False
        # flask_socketio's managed session (save_session on the raw server
        # object raised inside the connect handler — an exception there drops
        # EVERY connection, which is exactly the live-chat bug we hit).
        from flask import session as flask_session

        flask_session["user_id"] = claims["sub"]
        logger.info("socket connected user=%s", claims["sub"])

    @io.on("chat:join")
    def on_join(data):
        match_id = (data or {}).get("match_id")
        if not match_id:
            return {"ok": False, "error": "match_id_required"}
        user_id = _socket_user_id()
        if not user_id:
            # legacy clients may still pass a token in the payload
            claims = _decode_claims((data or {}).get("token") or _handshake_token())
            user_id = claims.get("sub") if claims else None
        if not user_id or not _participant(user_id, match_id):
            logger.warning("chat:join denied user=%s match=%s", user_id, match_id)
            return {"ok": False, "error": "forbidden"}
        from flask_socketio import join_room

        join_room(f"match:{match_id}")
        logger.info("chat:join ok user=%s match=%s", user_id, match_id)
        return {"ok": True}

    @io.on("chat:typing_start")
    def on_typing_start(data):
        _emit_typing_authenticated(data, True)

    @io.on("chat:typing_stop")
    def on_typing_stop(data):
        _emit_typing_authenticated(data, False)


def _handshake_token() -> str | None:
    """Token from the connect URL query string, if the client put it there."""
    return request.args.get("token")


def _participant(user_id: str, match_id) -> bool:
    """Is this user a member of the match? `match_id` arrives as a STRING over
    the socket while the column is a Uuid — coerce or the lookup silently
    misses and every room join is denied."""
    import uuid as uuid_module

    from app.models import Match

    try:
        key = match_id if isinstance(match_id, uuid_module.UUID) \
            else uuid_module.UUID(str(match_id))
    except (ValueError, TypeError, AttributeError):
        return False
    match = db.session.get(Match, key)
    if match is None:
        return False
    return str(user_id) in (str(match.user_a_id), str(match.user_b_id))


def _socket_user_id() -> str | None:
    """Identity captured at handshake — never read from the event payload."""
    from flask import session as flask_session

    try:
        return flask_session.get("user_id")
    except Exception:
        return None


def _emit_typing_authenticated(data, is_typing: bool) -> None:
    """Typing events are authenticated: the sender identity comes from the
    JWT stored at handshake (never the payload), and the sender must be a
    participant of the match — otherwise anyone could type into any room
    as anyone (doc 8 §A2.1/§A2.3)."""
    match_id = (data or {}).get("match_id")
    if not match_id:
        return
    user_id = _socket_user_id()
    if not user_id:
        return
    if not _participant(user_id, match_id):
        return
    _emit_typing({"match_id": match_id, "user_id": user_id}, is_typing)


def _decode_claims(token: str | None) -> dict | None:
    if not token:
        return None
    try:
        from flask_jwt_extended import decode_token

        return decode_token(token)
    except Exception:
        return None


def _emit_typing(data, is_typing: bool) -> None:
    match_id = data.get("match_id")
    user_id = data.get("user_id")
    if not match_id or not user_id:
        return
    key = f"{match_id}:{user_id}"
    now = time.monotonic()
    if is_typing and now - _room_last_typing.get(key, 0) < TYPING_DEBOUNCE_SECONDS:
        return
    _room_last_typing[key] = now
    socketio.emit(
        "chat:typing",
        {"match_id": match_id, "user_id": user_id, "typing": is_typing},
        room=f"match:{match_id}",
    )


def _authorized_for_match(token: str | None, match_id: str) -> bool:
    token = token or _handshake_token()
    claims = _decode_claims(token) if token else None
    user_id = claims.get("sub") if claims else _socket_user_id()
    return bool(user_id) and _participant(user_id, match_id)


def broadcast_message(match_id: str, payload: dict) -> None:
    socketio.emit("chat:message", {"match_id": match_id, **payload}, room=f"match:{match_id}")


def broadcast_typing(match_id: str, user_id: str, is_typing: bool) -> None:
    """Server-initiated typing indicator — used by companion replies so an AI
    thread shows the same typing bubble a human thread does (§14)."""
    socketio.emit(
        "chat:typing",
        {"match_id": match_id, "user_id": user_id, "typing": is_typing},
        room=f"match:{match_id}",
    )
