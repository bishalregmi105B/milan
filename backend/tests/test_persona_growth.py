"""§13 dynamic persona engine + Phase 3/4 endpoint tests.

All AI calls run against groq_mock (deterministic, offline) via the app's
TESTING mock belt plus conftest stubs.
"""
import uuid as uuid_module
from datetime import datetime, timedelta, timezone

from tests.conftest import auth_headers, make_user


def _premium_session(client, character_key="aarohi"):
    """Premium user + romantic session; returns (user, session_id)."""
    from app.extensions import db
    from app.models import Subscription

    user = make_user()
    db.session.add(Subscription(
        user_id=user.id, tier="premium",
        started_at=datetime.now(timezone.utc) - timedelta(days=5),
        status="active"))
    db.session.commit()
    resp = client.post(f"/api/v1/saathi/{character_key}/sessions",
                       headers=auth_headers(user))
    assert resp.status_code == 200, resp.get_json()
    return user, resp.get_json()["session_id"]


def test_roster_name_has_no_ai_tag(client, app):
    """doc 8 §E: the `· AI` suffix is gone from every surface — disclosure
    lives on the profile screen and the machine-readable `is_ai` flag."""
    from app.blueprints.saathi import ensure_characters_seeded

    ensure_characters_seeded()
    user = make_user()
    resp = client.get("/api/v1/saathi/characters", headers=auth_headers(user))
    chars = resp.get_json()["characters"]
    assert chars
    assert all("AI" not in c["name"] for c in chars)
    assert all(c.get("is_ai") is True for c in chars)


def test_session_dto_persona_and_hearts(client, app):
    user, sid = _premium_session(client)
    resp = client.get(f"/api/v1/saathi/sessions/{sid}", headers=auth_headers(user))
    body = resp.get_json()
    assert body["is_ai"] is True
    assert "AI" not in body["character_name"]
    assert body["persona"]["origins"] == "default"
    assert body["persona"]["style_mining_enabled"] is True
    assert body["hearts_balance"] == 0


def test_persona_train_from_history(client, app):
    user, sid = _premium_session(client)
    history = "\n".join(
        f"them: hey cutie {i} 😄" if i % 2 else f"me: hahaha {i}" for i in range(30))
    resp = client.post(f"/api/v1/saathi/sessions/{sid}/persona/train",
                       headers=auth_headers(user), json={"history": history})
    assert resp.status_code == 200, resp.get_json()
    data = resp.get_json()
    assert data["traits"]["origins"] == "imported"
    assert data["hearts_balance"] == 5

    resp2 = client.get(f"/api/v1/saathi/sessions/{sid}", headers=auth_headers(user))
    assert resp2.get_json()["persona"]["origins"] == "imported"


def test_persona_train_rejects_short(client, app):
    user, sid = _premium_session(client)
    resp = client.post(f"/api/v1/saathi/sessions/{sid}/persona/train",
                       headers=auth_headers(user), json={"history": "too short"})
    assert resp.status_code == 422


def test_persona_train_rejects_money_history(client, app):
    user, sid = _premium_session(client)
    history = "\n".join(f"them: send money to my account {i}" for i in range(30))
    resp = client.post(f"/api/v1/saathi/sessions/{sid}/persona/train",
                       headers=auth_headers(user), json={"history": history})
    assert resp.status_code == 422


def test_persona_settings_reset_and_mining(client, app):
    user, sid = _premium_session(client)
    resp = client.put(f"/api/v1/saathi/sessions/{sid}/persona/settings",
                      headers=auth_headers(user),
                      json={"style_mining_enabled": False, "reset": True})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["style_mining_enabled"] is False
    assert data["traits"]["origins"] == "default"


def test_realtime_mood_signals():
    from app.services import persona_service

    sad = persona_service.realtime_mood_signals("i feel so sad and alone today")
    assert sad["mood_hint"] == "sad"
    exam = persona_service.realtime_mood_signals("exam stress is killing me aile")
    assert exam["mood_hint"] == "stressed"
    assert "exam" in exam["context_tags"]
    neutral = persona_service.realtime_mood_signals("what are you up to?")
    assert neutral["mood_hint"] is None


def test_send_message_persists_user_mood(client, app):
    from app.extensions import db
    from app.models import SaathiSession

    user, sid = _premium_session(client)
    resp = client.post(f"/api/v1/saathi/sessions/{sid}/messages",
                       headers=auth_headers(user),
                       json={"body": "feeling low today, exam pressure"})
    assert resp.status_code == 200
    session = db.session.get(SaathiSession, uuid_module.UUID(sid))
    assert session.user_mood in ("stressed", "sad", None)


def test_diary_generate_and_list(client, app):
    user, sid = _premium_session(client)
    resp = client.post(f"/api/v1/saathi/sessions/{sid}/diary/generate",
                       headers=auth_headers(user))
    assert resp.status_code == 200, resp.get_json()
    entry = resp.get_json()
    assert entry["body"]
    resp2 = client.post(f"/api/v1/saathi/sessions/{sid}/diary/generate",
                        headers=auth_headers(user))
    assert resp2.get_json()["id"] == entry["id"]  # idempotent per day
    resp3 = client.get(f"/api/v1/saathi/sessions/{sid}/diary", headers=auth_headers(user))
    assert len(resp3.get_json()["entries"]) == 1


def test_mirror_flow(client, app):
    user, sid = _premium_session(client)
    resp = client.post(f"/api/v1/saathi/sessions/{sid}/mirror/ask",
                       headers=auth_headers(user))
    assert resp.status_code == 200, resp.get_json()
    q = resp.get_json()
    resp2 = client.post(f"/api/v1/saathi/mirror/{q['id']}/answer",
                        headers=auth_headers(user),
                        json={"reflection": "my momo ritual helps"})
    assert resp2.status_code == 200
    assert resp2.get_json()["hearts_balance"] == 3


def test_quest_flow(client, app):
    user, sid = _premium_session(client)
    resp = client.get(f"/api/v1/saathi/sessions/{sid}/quests", headers=auth_headers(user))
    assert resp.status_code == 200, resp.get_json()
    quest = resp.get_json()["quests"][0]
    resp2 = client.post(f"/api/v1/saathi/quests/{quest['id']}/progress",
                        headers=auth_headers(user), json={"steps": 1})
    data = resp2.get_json()
    assert data["completed"] is True
    assert data["hearts_balance"] >= quest["reward_points"]
    resp3 = client.post(f"/api/v1/saathi/quests/{quest['id']}/freeze",
                        headers=auth_headers(user))
    assert resp3.status_code == 200
    resp4 = client.post(f"/api/v1/saathi/quests/{quest['id']}/freeze",
                        headers=auth_headers(user))
    assert resp4.status_code == 409


def test_capsule_flow(client, app):
    user, sid = _premium_session(client)
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    resp = client.post(f"/api/v1/saathi/sessions/{sid}/capsules",
                       headers=auth_headers(user),
                       json={"title": "open me later", "content": "a little note",
                             "unlock_at": future})
    assert resp.status_code == 200, resp.get_json()
    capsule = resp.get_json()
    assert capsule["sealed"] is True
    resp2 = client.post(f"/api/v1/saathi/capsules/{capsule['id']}/open",
                        headers=auth_headers(user))
    assert resp2.status_code == 409  # still sealed
    resp3 = client.get(f"/api/v1/saathi/sessions/{sid}/capsules",
                       headers=auth_headers(user))
    assert resp3.get_json()["capsules"][0]["content"] is None


def test_recap_card(client, app):
    user, sid = _premium_session(client)
    resp = client.post(f"/api/v1/saathi/sessions/{sid}/recap",
                       headers=auth_headers(user), json={"period": "week"})
    assert resp.status_code == 200, resp.get_json()
    card = resp.get_json()
    assert card["payload"]["period"] == "week"
    assert card["watermark"].endswith("Milan")
    assert card["share_token"]


def test_hearts_ledger(client, app):
    user, sid = _premium_session(client)
    resp = client.get("/api/v1/saathi/hearts", headers=auth_headers(user))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["balance"] >= 0
    assert isinstance(data["ledger"], list)


def test_persona_block_injection(client, app):
    """Learned persona must reach the system prompt builder."""
    from app.extensions import db
    from app.models import SaathiPersonaProfile
    from app.services import persona_service

    user, sid = _premium_session(client)
    persona = SaathiPersonaProfile.query.filter_by(
        session_id=uuid_module.UUID(sid)).first()
    assert persona is not None
    persona.traits = {**persona.traits, "vibe": "sunset chaser",
                      "nickname_for_user": "starlight"}
    persona.persona_prompt = "keep the tone dreamy"
    db.session.commit()
    block = persona_service.persona_prompt_block(persona)
    assert "sunset chaser" in block
    assert "starlight" in block
    assert "dreamy" in block


def test_style_mining_requires_volume(client, app):
    """Fewer than 12 real messages -> None (no premature conclusions)."""
    from app.services import persona_service

    user, sid = _premium_session(client)
    assert persona_service.mine_style_digest(user.id) is None
