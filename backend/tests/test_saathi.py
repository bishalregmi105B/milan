import uuid as uuid_module

from tests.conftest import auth_headers, make_user


def _start_session(client, user, character_key="aarohi"):
    # aarohi is a free-tier companion (doc 8 roster); asha/bibek need a pass.
    resp = client.post(f"/api/v1/saathi/{character_key}/sessions", headers=auth_headers(user))
    assert resp.status_code == 200
    return resp.get_json()["session_id"]


def test_characters_seeded_from_curated_roster(client, app):
    user = make_user()
    resp = client.get("/api/v1/saathi/characters", headers=auth_headers(user))
    keys = {c["key"] for c in resp.get_json()["characters"]}
    assert {"asha", "bibek", "priya", "sagar"} <= keys


def test_send_message_returns_ai_labeled_reply(client, app, monkeypatch):
    from app.services import groq_service

    monkeypatch.setattr(groq_service, "saathi_respond_full",
                        lambda session_id, character_id, msg, **kwargs: {
                            "reply": "Practice openers by asking about their trek.",
                            "segments": ["Practice openers by asking about their trek."],
                            "read_delay_seconds": 1.0,
                            "typing_delay_seconds": 1.2,
                        })

    user = make_user()
    session_id = _start_session(client, user)
    resp = client.post(f"/api/v1/saathi/sessions/{session_id}/messages",
                       json={"body": "I never know how to start chats."},
                       headers=auth_headers(user))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["is_ai"] is True
    assert "trek" in body["reply"]
    assert body["typing_delay_seconds"] == 1.2


def test_crisis_keywords_surface_resource_card(client, app, monkeypatch):
    from app.services import groq_service

    monkeypatch.setattr(groq_service, "saathi_respond",
                        lambda s, c, m: "You matter. Let me share some support resources.")

    user = make_user()
    session_id = _start_session(client, user)
    resp = client.post(f"/api/v1/saathi/sessions/{session_id}/messages",
                       json={"body": "sometimes I feel like ending my life"},
                       headers=auth_headers(user))
    assert resp.get_json()["show_crisis_card"] is True
    from app.models import SaathiSession
    from app.extensions import db

    session = db.session.get(SaathiSession, uuid_module.UUID(session_id))
    assert session.crisis_flagged is True


def test_memory_view_delete_and_clear(client, app):
    from app.extensions import db
    from app.models import SaathiMemoryItem

    user = make_user()
    session_id = _start_session(client, user)
    item = SaathiMemoryItem(session_id=uuid_module.UUID(session_id),
                            summary_text="Practicing conversation openers", category="practice")
    db.session.add(item)
    db.session.commit()

    listed = client.get(f"/api/v1/saathi/sessions/{session_id}/memory", headers=auth_headers(user))
    items = listed.get_json()["items"]
    assert len(items) == 1

    deleted = client.delete(f"/api/v1/saathi/sessions/{session_id}/memory/{items[0]['id']}",
                            headers=auth_headers(user))
    assert deleted.status_code == 200
    remaining = client.get(f"/api/v1/saathi/sessions/{session_id}/memory", headers=auth_headers(user))
    assert remaining.get_json()["items"] == []


def test_proactive_settings_pause_and_opt_in(client, app):
    user = make_user()
    session_id = _start_session(client, user)
    resp = client.put(f"/api/v1/saathi/sessions/{session_id}/settings",
                      json={"proactive_opt_in": True, "is_paused": False},
                      headers=auth_headers(user))
    assert resp.status_code == 200
    assert resp.get_json()["proactive_opt_in"] is True
    # doc 8 §C7: the tier table owns the cap — free tier gets 2 auto-texts/day
    assert resp.get_json()["proactive_daily_cap"] == 2


def test_other_users_session_is_404(client, app):
    owner = make_user()
    intruder = make_user()
    session_id = _start_session(client, owner)
    resp = client.post(f"/api/v1/saathi/sessions/{session_id}/messages",
                       json={"body": "hello"}, headers=auth_headers(intruder))
    assert resp.status_code == 404


def test_new_session_proactive_is_off_by_default(client, app):
    from datetime import date, timedelta
    from app.extensions import db
    from app.models import SaathiSession

    user = make_user()
    session_id = _start_session(client, user)
    session = db.session.get(SaathiSession, uuid_module.UUID(session_id))
    assert session.proactive_opt_in is False


def test_saathi_requires_consent(client, app):
    user = make_user(consented=False)
    response = client.post(
        "/api/v1/saathi/aarohi/sessions", headers=auth_headers(user)
    )
    assert response.status_code == 403
    assert response.get_json()["error"] == "saathi_access_required"

    roster = client.get("/api/v1/saathi/characters", headers=auth_headers(user))
    assert roster.status_code == 403


def test_saathi_rejects_underage_or_suspended_user(client, app):
    from datetime import date, timedelta

    # Underage and suspended accounts are blocked at the JWT boundary
    # (user_lookup_loader in the app factory), so every authenticated route —
    # Saathi included — returns 401 before its own body ever runs. This is the
    # stronger posture: the account is unusable app-wide, not just here.
    underage = make_user(
        date_of_birth=date.today() - timedelta(days=16 * 365 + 30)
    )
    minor_response = client.post(
        "/api/v1/saathi/aarohi/sessions", headers=auth_headers(underage)
    )
    assert minor_response.status_code == 401

    suspended = make_user()
    suspended.account_status = "suspended"
    from app.extensions import db

    db.session.commit()
    suspended_response = client.post(
        "/api/v1/saathi/aarohi/sessions", headers=auth_headers(suspended)
    )
    assert suspended_response.status_code == 401


def test_companion_chat_reply_is_synchronous(client, app, monkeypatch):
    """Texting a companion match returns her reply in the HTTP body
    (companion_reply.messages) — never companion_pending. The reply is
    generated inline, so a dropped socket frame can't leave the user stuck on a
    typing bubble with no message (the reported bug)."""
    from app.services import groq_service

    monkeypatch.setattr(
        groq_service, "saathi_respond_full",
        lambda session_id, character_id, msg, **kwargs: {
            "reply": "hey! khana khayeu?",
            "segments": ["hey!", "khana khayeu?"],
            "typing_delay_seconds": 1.0,
        })

    user = make_user()
    start = client.post("/api/v1/saathi/aarohi/sessions",
                        headers=auth_headers(user))
    match_id = start.get_json()["match_id"]

    resp = client.post(f"/api/v1/matches/{match_id}/messages",
                       json={"body": "hi"}, headers=auth_headers(user))
    assert resp.status_code == 201
    body = resp.get_json()
    # not the async socket-only path
    assert body.get("companion_pending") in (None, False)
    texts = [m["body"] for m in body["companion_reply"]["messages"]]
    assert texts == ["hey!", "khana khayeu?"]


def test_companion_reply_does_not_defer_when_user_is_waiting(app, monkeypatch):
    """A reactive reply must never be deferred, even when her presence says she
    is asleep/busy — parking a direct reply for hours is the 'she never replied'
    bug. `should_defer` is short-circuited on the reactive path and never
    consulted."""
    from app.services import (groq_service, language_engine, realism_engine)

    called = {"defer": False}

    def _tripwire(state, **kwargs):
        called["defer"] = True
        return True

    # Force the real (non-mock) pipeline but keep it fully offline.
    monkeypatch.setattr(groq_service, "_mock_mode", lambda: False)
    monkeypatch.setattr(groq_service, "check_prompt_injection", lambda text: False)
    monkeypatch.setattr(groq_service, "_chat",
                        lambda *a, **k: "hey! khana khayeu?")
    monkeypatch.setattr(groq_service, "moderate_content",
                        lambda text: {"flagged": False, "categories": [], "available": True})
    monkeypatch.setattr(language_engine, "violates", lambda reply, style: None)
    monkeypatch.setattr(realism_engine, "should_defer", _tripwire)

    user = make_user()
    from app.models import SaathiCharacter
    from app.services import companion_account_service

    with app.app_context():
        from app.blueprints.saathi import ensure_characters_seeded

        ensure_characters_seeded()
        character = SaathiCharacter.query.filter_by(key="aarohi").first()
        _match, session = companion_account_service.ensure_companion_match(
            user.id, character)
        result = groq_service.saathi_respond_full(
            str(session.id), str(session.character_id), "hey", reactive=True)

    assert called["defer"] is False  # never even asked — reactive wins
    assert result.get("deferred") is not True
    assert result.get("reply")
