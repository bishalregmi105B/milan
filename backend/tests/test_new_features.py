import io

import pytest

from app.extensions import db
from tests.conftest import auth_headers, make_admin, make_user


def test_media_upload_photo(client, app):
    user = make_user()
    resp = client.post("/api/v1/media/upload?kind=photo",
                       data={"file": (io.BytesIO(b"jpegbytes"), "me.jpg", "image/jpeg")},
                       content_type="multipart/form-data", headers=auth_headers(user))
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["kind"] == "photo"
    assert body["photo_id"]
    assert body["url"].startswith("/media/")


def test_media_upload_rejects_bad_type(client, app):
    user = make_user()
    resp = client.post("/api/v1/media/upload?kind=photo",
                       data={"file": (io.BytesIO(b"x"), "f.exe", "application/octet-stream")},
                       content_type="multipart/form-data", headers=auth_headers(user))
    assert resp.status_code == 422


def test_calibration_endpoint_and_ranking_bias(client, app):
    from app.models import PreferenceCalibration

    user = make_user("Viewer")
    target = make_user("Target")
    target.profile.interests = ["trekking"]
    from app.extensions import db
    db.session.commit()

    for label in ("like", "like", "maybe"):
        resp = client.post("/api/v1/discovery/calibration",
                           json={"target_id": str(target.id), "photo_url": "/media/x.jpg",
                                 "label": label},
                           headers=auth_headers(user))
        assert resp.status_code == 200
    rows = PreferenceCalibration.query.filter_by(user_id=user.id).all()
    assert len(rows) == 3

    bad = client.post("/api/v1/discovery/calibration", json={"label": "love"},
                      headers=auth_headers(user))
    assert bad.status_code == 422


def test_candidates_include_blur_until_match_flag(client, app):
    a = make_user("A")
    b = make_user("B")
    b.discreet_mode = True
    # candidates require a photo (doc 8 §A4.1)
    from app.models import Photo
    db.session.add(Photo(user_id=b.id, url="https://cdn.test/b.jpg"))
    db.session.commit()

    body = client.get("/api/v1/discovery/candidates", headers=auth_headers(a)).get_json()
    cand = next(c for c in body["candidates"] if c["id"] == str(b.id))
    assert cand["is_blurred"] is True


def test_weekly_recap_endpoint(client, app, monkeypatch):
    from app.services import groq_service

    monkeypatch.setattr(groq_service, "generate_weekly_recap",
                        lambda activity: "A quiet week — one new match. Try sending the first message!")
    user = make_user()
    resp = client.get("/api/v1/matches/recap/weekly", headers=auth_headers(user))
    assert resp.status_code == 200
    body = resp.get_json()
    assert "quiet week" in body["recap"]
    assert body["stats"]["new_matches_this_week"] == 0


def test_saathi_voice_endpoint(client, app, monkeypatch):
    from app.services import groq_service

    monkeypatch.setattr(groq_service, "transcribe_audio", lambda b: "I feel nervous about texting first.")
    monkeypatch.setattr(groq_service, "saathi_respond_full",
                        lambda s, c, m, **kwargs: {"reply": "That's common! Try starting with a question about their trek.",
                                                   "segments": ["That's common! Try starting with a question about their trek."],
                                                   "read_delay_seconds": 1.0, "typing_delay_seconds": 2.0})
    monkeypatch.setattr(groq_service, "synthesize_speech", lambda text, voice_key=None: b"\x11\x22mp3bytes")

    user = make_user()
    # Voice notes are a Plus-tier capability (master plan §6) — grant a pass.
    import datetime as _dt

    from app.extensions import db
    from app.models import Subscription

    db.session.add(Subscription(user_id=user.id, tier="plus",
                                started_at=_dt.datetime.now(_dt.timezone.utc), status="active"))
    db.session.commit()
    session_id = client.post("/api/v1/saathi/asha/sessions",
                             headers=auth_headers(user)).get_json()["session_id"]
    resp = client.post(f"/api/v1/saathi/sessions/{session_id}/voice",
                       data={"audio": (io.BytesIO(b"webm"), "clip.webm", "audio/webm")},
                       content_type="multipart/form-data", headers=auth_headers(user))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["transcript"].startswith("I feel nervous")
    assert body["is_ai"] is True


def test_admin_verification_queue_and_resolve(client, app):
    from app.extensions import db
    from app.models import LivenessCheck

    admin = make_admin(role="admin") if False else make_user(role="admin")
    subject = make_user("Pending Person")
    check = LivenessCheck(user_id=subject.id, status="failed",
                          failure_reason="low_confidence", passed=False)
    db.session.add(check)
    db.session.commit()

    queue = client.get("/api/v1/admin/verification-queue", headers=auth_headers(admin))
    ids = [item["id"] for item in queue.get_json()["queue"]]
    assert str(check.id) in ids

    resolved = client.post(f"/api/v1/admin/verification-queue/{check.id}/resolve",
                           json={"decision": "approve"}, headers=auth_headers(admin))
    assert resolved.status_code == 200
    db.session.expire_all()
    db.session.refresh(subject)
    assert subject.is_verified is True


def test_admin_preset_crud_and_retire(client, app):
    admin = make_user(role="admin")
    created = client.post("/api/v1/admin/personalization/presets",
                          json={"key": "test_pack_one", "pack": "brand", "name": "Test One",
                                "wallpaper_type": "solid", "wallpaper_value": "#1F6F54",
                                "bubble_color_sent": "#F5A623", "bubble_color_received": "#DCEFE7"},
                          headers=auth_headers(admin))
    assert created.status_code == 201
    preset_id = created.get_json()["id"]

    dup = client.post("/api/v1/admin/personalization/presets",
                      json={"key": "test_pack_one", "pack": "brand", "name": "Dup",
                            "wallpaper_type": "solid", "wallpaper_value": "#000000",
                            "bubble_color_sent": "#111111", "bubble_color_received": "#222222"},
                      headers=auth_headers(admin))
    assert dup.status_code == 409

    retired = client.delete(f"/api/v1/admin/personalization/presets/{preset_id}",
                            headers=auth_headers(admin))
    assert retired.get_json()["retired"] is True

    public = client.get("/api/v1/personalization/presets", headers=auth_headers(make_user())).get_json()
    assert all(p["key"] != "test_pack_one" for p in public["presets"])


def test_admin_analytics_history_series(client, app):
    admin = make_user(role="admin")
    resp = client.get("/api/v1/admin/analytics/history", headers=auth_headers(admin))
    series = resp.get_json()["series"]
    assert len(series) == 30
    assert {"date", "signups", "matches", "revenue_npr"} <= set(series[0].keys())


def test_admin_case_context_scam_thread(client, app):
    import datetime as dt

    from app.extensions import db
    from app.models import Match, Message, ScamFlag

    admin = make_user(role="admin")
    a, b = make_user("A"), make_user("B")
    match = Match(user_a_id=a.id, user_b_id=b.id, matched_at=dt.datetime.now(dt.timezone.utc))
    db.session.add(match)
    db.session.flush()
    msg = Message(match_id=match.id, sender_id=a.id,
                  body="Send money to my account please.")
    db.session.add(msg)
    flag = ScamFlag(message_id=msg.id, match_id=match.id, flagged_user_id=a.id,
                    pattern_matched=["money_request"], confidence=0.9, risk_level="high")
    db.session.add(flag)
    db.session.commit()

    ctx = client.get(f"/api/v1/admin/moderation/cases/scam_flag/{flag.id}",
                     headers=auth_headers(admin)).get_json()
    assert ctx["risk_level"] == "high"
    assert any("money" in (m["body"] or "") for m in ctx["thread_preview"])


def test_admin_user_detail_counts(client, app):
    admin = make_user(role="admin")
    user = make_user("Detail User")
    resp = client.get(f"/api/v1/admin/users/{user.id}", headers=auth_headers(admin))
    body = resp.get_json()
    assert body["user"]["phone_masked"].startswith("***")
    assert body["reports_against"] == 0
