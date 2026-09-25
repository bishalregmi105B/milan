import uuid as uuid_module

import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.extensions import db as _db
from app.models import Profile, User


@pytest.fixture()
def app(monkeypatch):
    app = create_app("test")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(autouse=True)
def stub_celery_delay(monkeypatch):
    from app.extensions import celery_app

    monkeypatch.setattr(celery_app.Task, "delay", lambda self, *a, **kw: None, raising=False)


@pytest.fixture(autouse=True)
def mock_groq(monkeypatch):
    from app.services import groq_service

    monkeypatch.setattr(groq_service, "moderate_content",
                        lambda text: {"flagged": False, "categories": [], "available": True})
    monkeypatch.setattr(groq_service, "check_prompt_injection", lambda text: False)
    monkeypatch.setattr(groq_service, "classify_scam_pattern",
                        lambda text: {"risk": "none", "categories": []})
    monkeypatch.setattr(groq_service, "explain_match", lambda signals: "You both like trekking.")
    monkeypatch.setattr(groq_service, "generate_proactive_message",
                        lambda session_id, mtype, note=None, **kwargs: None)


@pytest.fixture()
def client(app):
    return app.test_client()


def make_user(display_name: str = "Test User", *, consented: bool = True, **kwargs) -> User:
    from datetime import date as _date, timedelta as _timedelta

    # every real account passes the 18+ gate, so it always has a DOB — give
    # fixtures one too (24 years old) unless the test overrides it
    if "date_of_birth" not in kwargs:
        kwargs["date_of_birth"] = _date.today() - _timedelta(days=24 * 365 + 90)
    user = User(phone=kwargs.pop("phone", f"+97798{uuid_module.uuid4().hex[:8]}"), **kwargs)
    if consented:
        from app.models.base import utcnow as _utcnow

        user.saathi_intro_accepted_at = _utcnow()
        user.saathi_terms_version = "2026-09-01"
    _db.session.add(user)
    _db.session.flush()
    _db.session.add(Profile(user_id=user.id, display_name=display_name))
    _db.session.commit()
    return user


def auth_headers(user: User) -> dict:
    token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}


def make_admin(**kwargs) -> User:
    return make_user(role="admin", **kwargs)
