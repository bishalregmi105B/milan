import datetime as dt
import uuid as uuid_module

from app.extensions import db
from app.models import Match
from tests.conftest import auth_headers, make_user


def _make_match(a, b) -> Match:
    match = Match(user_a_id=a.id, user_b_id=b.id, matched_at=dt.datetime.now(dt.timezone.utc))
    db.session.add(match)
    db.session.commit()
    return match


def test_send_message_persists_and_broadcasts(client, app, monkeypatch):
    sent = {}

    def fake_broadcast(match_id, payload):
        sent["match_id"] = match_id
        sent["payload"] = payload

    from app.sockets import chat_events

    monkeypatch.setattr(chat_events, "broadcast_message", fake_broadcast)

    a, b = make_user("A"), make_user("B")
    match = _make_match(a, b)
    resp = client.post(f"/api/v1/matches/{match.id}/messages",
                       json={"body": "Namaste! How's your week?"},
                       headers=auth_headers(a))
    assert resp.status_code == 201
    assert sent["match_id"] == str(match.id)
    assert sent["payload"]["body"] == "Namaste! How's your week?"


def test_flagged_message_blocked_before_delivery(client, app, monkeypatch):
    from app.services import groq_service

    monkeypatch.setattr(groq_service, "moderate_content",
                        lambda text: {"flagged": True, "categories": ["harassment"], "available": True})

    a, b = make_user("A"), make_user("B")
    match = _make_match(a, b)
    resp = client.post(f"/api/v1/matches/{match.id}/messages",
                       json={"body": "you are terrible"},
                       headers=auth_headers(a))
    assert resp.status_code == 422
    assert resp.get_json()["error"] == "message_blocked_by_moderation"


def test_non_participant_cannot_read_or_send(client, app):
    a, b = make_user("A"), make_user("B")
    outsider = make_user("C")
    match = _make_match(a, b)
    assert client.get(f"/api/v1/matches/{match.id}/messages",
                      headers=auth_headers(outsider)).status_code == 404
    assert client.post(f"/api/v1/matches/{match.id}/messages", json={"body": "hi"},
                       headers=auth_headers(outsider)).status_code == 404


def test_block_deactivates_match(client, app):
    a, b = make_user("A"), make_user("B")
    match = _make_match(a, b)
    resp = client.post("/api/v1/safety/blocks", json={"blocked_id": str(b.id)},
                       headers=auth_headers(a))
    assert resp.get_json()["blocked"] is True
    db.session.expire_all()
    assert db.session.get(Match, match.id).is_active is False


def test_scam_flag_created_by_async_scan(client, app, monkeypatch):
    from app.models import Message, ScamFlag
    from app.services import groq_service
    from app.tasks.moderation_tasks import scan_message_async

    monkeypatch.setattr(groq_service, "classify_scam_pattern",
                        lambda text: {"risk": "high", "categories": ["money_request"]})

    a, b = make_user("A"), make_user("B")
    match = _make_match(a, b)
    message = Message(match_id=match.id, sender_id=a.id,
                      body="Please send money to my account, my family needs it urgently.")
    db.session.add(message)
    db.session.commit()

    result = scan_message_async.run(str(message.id))
    assert result["scam_risk"] in ("low", "high")
    flags = ScamFlag.query.filter_by(message_id=message.id).all()
    assert len(flags) == 1
    assert "money_request" in flags[0].pattern_matched or flags[0].pattern_matched


def test_audio_media_type_round_trips(client, app):
    a, b = make_user("A"), make_user("B")
    match = _make_match(a, b)
    sent = client.post(
        f"/api/v1/matches/{match.id}/messages",
        json={"media_url": "/media/voice.m4a", "media_type": "audio"},
        headers=auth_headers(a),
    )
    assert sent.status_code == 201

    history = client.get(
        f"/api/v1/matches/{match.id}/messages", headers=auth_headers(b)
    ).get_json()["messages"]
    assert history[-1]["media_type"] == "audio"


def test_unsupported_video_media_type_is_rejected(client, app):
    a, b = make_user("A"), make_user("B")
    match = _make_match(a, b)
    response = client.post(
        f"/api/v1/matches/{match.id}/messages",
        json={"media_url": "/media/video.mp4", "media_type": "video"},
        headers=auth_headers(a),
    )
    assert response.status_code == 422
    assert response.get_json()["error"] == "invalid_media_type"


def test_snap_single_view_and_screenshot_notice(client, app):
    a, b = make_user("A"), make_user("B")
    match = _make_match(a, b)
    created = client.post(f"/api/v1/matches/{match.id}/snaps",
                          json={"media_url": "/media/snap.webp", "view_mode": "single_view"},
                          headers=auth_headers(a))
    snap_id = created.get_json()["id"]
    viewed = client.post(f"/api/v1/matches/snaps/{snap_id}/screenshot", headers=auth_headers(b))
    assert viewed.status_code == 200
    from app.models import Snap

    db.session.expire_all()
    assert db.session.get(Snap, uuid_module.UUID(snap_id)).screenshot_detected is True
