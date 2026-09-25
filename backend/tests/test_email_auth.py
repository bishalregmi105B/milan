"""Email-signup auth flow: mirrors the phone OTP contract."""
import re


def _request(client, email):
    return client.post("/api/v1/auth/otp/request", json={"email": email})


def test_email_otp_request_and_verify_creates_user(client, monkeypatch):
    logged = {}

    def fake_send(email, code):
        logged[email] = code
        return True

    from app.utils import otp as otp_util

    monkeypatch.setattr(otp_util, "send_email_otp", fake_send)
    resp = _request(client, "aasha@example.com")
    assert resp.status_code == 200
    assert resp.get_json()["sent"] is True
    code = logged["aasha@example.com"]
    assert re.fullmatch(r"\d{6}", code)

    resp = client.post("/api/v1/auth/otp/verify", json={
        "email": "aasha@example.com", "code": code, "date_of_birth": "1998-04-12",
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["email"] == "aasha@example.com"
    assert body["user"]["phone"] is None
    assert body["user"]["auth_provider"] == "email"

    # Second login: no DOB needed, same account.
    monkeypatch.setattr(otp_util, "send_email_otp", fake_send)
    _request(client, "aasha@example.com")
    resp = client.post("/api/v1/auth/otp/verify", json={
        "email": "aasha@example.com", "code": logged["aasha@example.com"],
    })
    assert resp.status_code == 200
    assert resp.get_json()["user"]["id"] == body["user"]["id"]


def test_email_otp_invalid_email(client):
    resp = _request(client, "not-an-email")
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["error"] == "invalid_email"
    assert "doesn't look right" in body["message"]


def test_email_otp_missing_identifier(client):
    resp = client.post("/api/v1/auth/otp/request", json={})
    assert resp.status_code == 422
    assert resp.get_json()["error"] == "identifier_required"


def test_email_verify_wrong_code(client, monkeypatch):
    from app.utils import otp as otp_util

    monkeypatch.setattr(otp_util, "send_email_otp", lambda e, c: True)
    _request(client, "bibek@example.com")
    resp = client.post("/api/v1/auth/otp/verify", json={
        "email": "bibek@example.com", "code": "000000",
    })
    assert resp.status_code == 401
    body = resp.get_json()
    assert body["error"] == "invalid_or_expired_otp"
    assert "expired" in body["message"]


def test_email_new_user_age_gate(client, monkeypatch):
    from app.utils import otp as otp_util

    logged = {}
    monkeypatch.setattr(otp_util, "send_email_otp",
                        lambda e, c: logged.setdefault(e, c) and True)
    _request(client, "priya@example.com")
    resp = client.post("/api/v1/auth/otp/verify", json={
        "email": "priya@example.com", "code": logged["priya@example.com"],
    })
    assert resp.status_code == 409
    body = resp.get_json()
    assert body["error"] == "onboarding_required"

    # The valid code remains available for the explicit age step.
    resp = client.post("/api/v1/auth/otp/verify", json={
        "email": "priya@example.com", "code": logged["priya@example.com"],
        "date_of_birth": "2015-01-01",
    })
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "age_gate_18_plus"


def test_email_user_suspended_cannot_login(client, monkeypatch):
    from app.extensions import db
    from app.models import User
    from app.utils import otp as otp_util

    logged = {}
    monkeypatch.setattr(otp_util, "send_email_otp",
                        lambda e, c: logged.update({e: c}) or True)
    _request(client, "sagar@example.com")
    resp = client.post("/api/v1/auth/otp/verify", json={
        "email": "sagar@example.com", "code": logged["sagar@example.com"],
        "date_of_birth": "1995-01-01",
    })
    assert resp.status_code == 200
    user = User.query.filter_by(email="sagar@example.com").first()
    user.account_status = "suspended"
    db.session.commit()

    _request(client, "sagar@example.com")
    resp = client.post("/api/v1/auth/otp/verify", json={
        "email": "sagar@example.com", "code": logged["sagar@example.com"],
    })
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "account_suspended"


def test_phone_error_responses_carry_messages(client):
    resp = client.post("/api/v1/auth/otp/request", json={"phone": "123"})
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["error"] == "invalid_phone"
    assert body["message"]
