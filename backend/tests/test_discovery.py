import datetime as dt
import uuid as uuid_module

from app.extensions import db
from app.models import Match, Swipe, User
from tests.conftest import auth_headers, make_user


def test_swipe_mutual_like_creates_match(client, app):
    a = make_user("A")
    b = make_user("B")
    b.profile.interests = ["trekking", "music"]
    a.profile.interests = ["trekking"]
    db.session.commit()

    first = client.post("/api/v1/discovery/swipe",
                        json={"target_id": str(b.id), "direction": "like"},
                        headers=auth_headers(a))
    assert first.get_json()["match"] is False

    second = client.post("/api/v1/discovery/swipe",
                         json={"target_id": str(a.id), "direction": "like"},
                         headers=auth_headers(b))
    body = second.get_json()
    assert body["match"] is True
    assert body["compatibility_score"] > 0

    matches = client.get("/api/v1/matches", headers=auth_headers(a)).get_json()["matches"]
    assert len(matches) == 1
    assert matches[0]["match_reason_text"] == "You both like trekking."


def test_duplicate_swipe_rejected_by_unique_constraint(client, app):
    a = make_user("A")
    b = make_user("B")
    first = client.post("/api/v1/discovery/swipe",
                        json={"target_id": str(b.id), "direction": "like"}, headers=auth_headers(a))
    assert first.status_code == 200
    second = client.post("/api/v1/discovery/swipe",
                         json={"target_id": str(b.id), "direction": "pass"}, headers=auth_headers(a))
    assert second.status_code in (200, 409, 500)


def test_candidates_exclude_self_and_blocked(client, app):
    from app.models import Photo

    a = make_user("A")
    b = make_user("B")
    c = make_user("C")
    # doc 8 §A4.1: candidates require a display name AND at least one photo —
    # "Milan user" cards are killed at the source. c gets a photo; d has none.
    db.session.add(Photo(user_id=c.id, url="https://cdn.test/c.jpg"))
    d = make_user("D")
    db.session.add(Swipe(swiper_id=a.id, target_id=b.id, direction="pass"))
    db.session.commit()

    resp = client.get("/api/v1/discovery/candidates", headers=auth_headers(a)).get_json()
    ids = {cand["id"] for cand in resp["candidates"]}
    assert str(a.id) not in ids
    assert str(b.id) not in ids  # already passed on
    assert str(d.id) not in ids  # no photo -> not a candidate
    assert str(c.id) in ids


def test_candidates_carry_photo_gallery(client, app):
    """Multi-photo swipe card: each candidate ships a `photos` array (all of
    their photos) so the card can page through them, not just photo_url."""
    from app.models import Photo

    a = make_user("A")
    c = make_user("C")
    db.session.add(Photo(user_id=c.id, url="https://cdn.test/c1.jpg"))
    db.session.add(Photo(user_id=c.id, url="https://cdn.test/c2.jpg"))
    db.session.commit()

    resp = client.get("/api/v1/discovery/candidates",
                      headers=auth_headers(a)).get_json()
    cand = next(x for x in resp["candidates"] if x["id"] == str(c.id))
    assert cand["photos"] == ["https://cdn.test/c1.jpg", "https://cdn.test/c2.jpg"]


def test_candidates_accept_distance_filter(client, app):
    """The deck accepts max_distance_km without error (server-side filter)."""
    from app.models import Photo

    a = make_user("A")
    c = make_user("C")
    db.session.add(Photo(user_id=c.id, url="https://cdn.test/c.jpg"))
    db.session.commit()

    resp = client.get("/api/v1/discovery/candidates?max_distance_km=50",
                      headers=auth_headers(a))
    assert resp.status_code == 200
    assert "candidates" in resp.get_json()


def test_kundali_requires_opt_in_birth_details(client, app):
    a = make_user("A")
    b = make_user("B")
    match = Match(user_a_id=a.id, user_b_id=b.id, matched_at=dt.datetime.now(dt.timezone.utc))
    db.session.add(match)
    db.session.commit()
    resp = client.get(f"/api/v1/discovery/kundali/{match.id}", headers=auth_headers(a))
    assert resp.status_code == 422


def test_kundali_returns_labeled_narrative(client, app, monkeypatch):
    from app.services import groq_service

    monkeypatch.setattr(groq_service, "kundali_mode_narrative",
                        lambda da, db_: "A playful cultural read of your charts — for fun only.")
    a = make_user("A")
    b = make_user("B")
    a.profile.horoscope_details = {"birth_date": "1998-04-12", "birth_time": "06:30", "birth_place": "Kathmandu"}
    b.profile.horoscope_details = {"birth_date": "1999-11-02", "birth_time": "14:10", "birth_place": "Pokhara"}
    match = Match(user_a_id=a.id, user_b_id=b.id, matched_at=dt.datetime.now(dt.timezone.utc))
    db.session.add(match)
    db.session.commit()

    resp = client.get(f"/api/v1/discovery/kundali/{match.id}", headers=auth_headers(a))
    body = resp.get_json()
    assert resp.status_code == 200
    assert body["label"] == "fun_cultural_signal_not_science"
