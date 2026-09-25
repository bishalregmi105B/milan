import datetime as dt
import uuid as uuid_module

from app.extensions import db
from app.models import Match, Notification, NotificationPreference
from tests.conftest import auth_headers, make_user


def test_should_send_respects_category_cap(app):
    from app.services.notification_service import should_send

    user = make_user()
    for _ in range(5):
        db.session.add(Notification(user_id=user.id, category="matches", title="t", body="b",
                                    sent_at=dt.datetime.now(dt.timezone.utc)))
    db.session.commit()
    assert should_send(user.id, "matches") is False
    assert should_send(user.id, "messages") is True


def test_should_send_respects_disabled_preference(app):
    from app.services.notification_service import should_send

    user = make_user()
    db.session.add(NotificationPreference(user_id=user.id, category="promo",
                                          enabled=False, max_per_day=3))
    db.session.commit()
    assert should_send(user.id, "promo") is False


def test_queue_notification_suppressed_by_cap(app):
    from app.services.notification_service import queue_notification

    user = make_user()
    for _ in range(5):
        queue_notification(user.id, "matches", "t", "b")
    assert queue_notification(user.id, "matches", "one more", "b") is False


def test_saathi_proactive_check_never_exceeds_daily_cap(app, client, monkeypatch):
    """The initiative engine's daily cap gate (doc 8 §C5): free tier allows
    `proactive_daily` auto-texts per Kathmandu day, then she stays quiet."""
    import uuid as uuid_module

    from app.extensions import db
    from app.models import SaathiSession
    from app.services import initiative_engine
    from app.tasks.companion_tasks import companion_initiative_tick
    from tests.test_saathi import _start_session

    monkeypatch.setattr("app.tasks.companion_tasks._quiet_hours_active", lambda: False)
    monkeypatch.setattr(initiative_engine, "score",
                        lambda session, day=None: (50.0, "silence_curve", "been a while"))
    monkeypatch.setattr(initiative_engine, "generate",
                        lambda session, character, trigger, note, day=None: "hello! how was your day")

    user = make_user()
    session_id = _start_session(client, user)  # provisions match + companion
    session = db.session.get(SaathiSession, uuid_module.UUID(session_id))
    session.proactive_opt_in = True
    db.session.commit()

    result = companion_initiative_tick.run()
    assert result["sent"] == 1

    # at/over the cap: no more auto-texts today
    session_id = db.session.query(SaathiSession.id).filter_by(user_id=user.id).scalar()
    session = db.session.get(SaathiSession, session_id)
    session.proactive_messages_today = 99
    db.session.commit()
    result2 = companion_initiative_tick.run()
    assert result2["sent"] == 0


def test_opted_out_sessions_get_no_proactive_messages(app, client, monkeypatch):
    import uuid as uuid_module

    from app.extensions import db
    from app.models import SaathiSession
    from app.services import initiative_engine
    from app.tasks.companion_tasks import companion_initiative_tick
    from tests.test_saathi import _start_session

    monkeypatch.setattr("app.tasks.companion_tasks._quiet_hours_active", lambda: False)
    monkeypatch.setattr(initiative_engine, "score",
                        lambda session, day=None: (50.0, "silence_curve", "been a while"))
    monkeypatch.setattr(initiative_engine, "generate",
                        lambda session, character, trigger, note, day=None: "hello!")

    user = make_user()
    session_id = _start_session(client, user)

    # user pauses her initiative (the Saathi settings toggle)
    session = db.session.get(SaathiSession, uuid_module.UUID(session_id))
    session.proactive_opt_in = False
    db.session.commit()

    result = companion_initiative_tick.run()
    assert result["sent"] == 0


def test_unconsented_or_suspended_users_get_no_proactive_messages(app, client, monkeypatch):
    import uuid as uuid_module

    from app.extensions import db
    from app.models import SaathiSession
    from app.services import initiative_engine
    from app.tasks.companion_tasks import companion_initiative_tick
    from tests.test_saathi import _start_session

    monkeypatch.setattr("app.tasks.companion_tasks._quiet_hours_active", lambda: False)
    monkeypatch.setattr(initiative_engine, "score",
                        lambda session, day=None: (50.0, "silence_curve", "been a while"))
    monkeypatch.setattr(initiative_engine, "generate",
                        lambda session, character, trigger, note, day=None: "hello!")

    unconsented = make_user(consented=False)
    suspended = make_user()
    session_id = _start_session(client, suspended)
    session = db.session.get(SaathiSession, uuid_module.UUID(session_id))
    session.proactive_opt_in = True
    suspended.account_status = "suspended"
    db.session.commit()

    result = companion_initiative_tick.run()
    assert result["sent"] == 0


def test_due_deferred_reply_is_delivered_once(app, client, monkeypatch):
    import uuid as uuid_module

    from datetime import datetime, timedelta, timezone
    from app.extensions import db
    from app.models import SaathiSession
    from app.tasks.companion_tasks import deliver_due_deferred_replies
    from tests.test_saathi import _start_session

    session_id = _start_session(client, make_user())
    session = db.session.get(SaathiSession, uuid_module.UUID(session_id))
    session.deferred_reply_body = "sorry, I had class — what did I miss?"
    session.deferred_reply_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.session.commit()

    delivered = {}
    monkeypatch.setattr(
        "app.tasks.companion_tasks.companion_account_service.deliver_companion_message",
        lambda target, body, **kwargs: delivered.setdefault("body", body) or {"id": "m1"},
    )

    result = deliver_due_deferred_replies.run()
    assert result["delivered"] == 1
    db.session.expire_all()
    session = db.session.get(SaathiSession, uuid_module.UUID(session_id))
    assert delivered["body"].startswith("sorry")
    assert session.deferred_reply_body is None


def test_preferences_roundtrip(client, app):
    user = make_user()
    put = client.put("/api/v1/notifications/preferences",
                     json={"preferences": [{"category": "saathi", "enabled": False}]},
                     headers=auth_headers(user))
    assert put.status_code == 200
    got = client.get("/api/v1/notifications/preferences", headers=auth_headers(user)).get_json()
    saathi_pref = next(p for p in got["preferences"] if p["category"] == "saathi")
    assert saathi_pref["enabled"] is False


def test_admin_analytics_requires_role(client, app):
    user = make_user()
    resp = client.get("/api/v1/admin/analytics/overview", headers=auth_headers(user))
    assert resp.status_code == 403


def test_admin_analytics_overview(client, app):
    admin = make_user(role="admin")
    a, b = make_user("A"), make_user("B")
    db.session.add(Match(user_a_id=a.id, user_b_id=b.id,
                         matched_at=dt.datetime.now(dt.timezone.utc)))
    db.session.commit()
    resp = client.get("/api/v1/admin/analytics/overview", headers=auth_headers(admin))
    body = resp.get_json()
    assert resp.status_code == 200
    assert body["dau"] >= 3
    assert body["matches_7d"] == 1
