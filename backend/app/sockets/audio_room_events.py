from flask import request

from app.extensions import socketio


def _token_sub():
    token = request.args.get("token") or None
    if not token:
        return None
    try:
        from flask_jwt_extended import decode_token

        return decode_token(token).get("sub")
    except Exception:
        return None


def register_audio_room_events(io):
    @io.on("audio_room:join")
    def on_join(data):
        user_id = _token_sub()
        room_id = (data or {}).get("room_id")
        if not room_id or not user_id:
            return {"ok": False}
        from flask_socketio import join_room

        join_room(f"audio_room:{room_id}")
        io.emit("audio_room:state", {
            "room_id": room_id,
            "event": "participant_joined",
            "user_id": user_id,
        }, room=f"audio_room:{room_id}")
        return {"ok": True}

    @io.on("audio_room:raise_hand")
    def on_raise_hand(data):
        user_id = _token_sub()
        room_id = (data or {}).get("room_id")
        if not room_id or not user_id:
            return
        io.emit("audio_room:state", {
            "room_id": room_id,
            "event": "hand_raised",
            "user_id": user_id,
        }, room=f"audio_room:{room_id}")
