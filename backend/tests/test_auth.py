from datetime import date

from tests.conftest import auth_headers, make_user


def test_otp_request_sends_code(client, app):
    resp = client.post("/api/v1/auth/otp/request", json={"phone": "9812345678"})
    assert resp.status_code == 200
    assert resp.get_json()["sent"] is True
    from app.utils.otp import _otp_store

    assert any(key.startswith("otp:+9779812345678") for key in _otp_store)


def test_otp_request_rejects_invalid_phone(client):
    resp = client.post("/api/v1/auth/otp/request", json={"phone": "123"})
    assert resp.status_code == 422


def test_otp_verify_creates_user_and_issues_tokens(client, app):
    phone = "+9779811111111"
    from app.utils.otp import store_otp

    store_otp(phone, "123456")
    resp = client.post("/api/v1/auth/otp/verify", json={
        "phone": phone, "code": "123456", "date_of_birth": "2000-01-01",
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["has_profile"] is False


def test_age_gate_blocks_under_18(client, app):
    phone = "+9779822222222"
    from app.utils.otp import store_otp

    store_otp(phone, "654321")
    minor_year = date.today().year - 16
    resp = client.post("/api/v1/auth/otp/verify", json={
        "phone": phone, "code": "654321", "date_of_birth": f"{minor_year}-01-01",
    })
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "age_gate_18_plus"


def test_refresh_issues_new_access_token(client, app):
    user = make_user()
    refresh = client.post("/api/v1/auth/refresh",
                          headers={"Authorization": f"Bearer {make_refresh(user)}"})
    assert refresh.status_code == 200
    assert "access_token" in refresh.get_json()


def test_google_new_user_requires_real_dob(client, app, monkeypatch):
    class _Response:
        @staticmethod
        def json():
            return {
                "email": "new-google@example.com",
                "email_verified": "true",
                "aud": "google-client-id",
                "iss": "https://accounts.google.com",
            }

    monkeypatch.setattr("requests.get", lambda *args, **kwargs: _Response())
    app.config["GOOGLE_CLIENT_ID"] = "google-client-id"

    missing = client.post(
        "/api/v1/auth/google", json={"id_token": "token"}
    )
    assert missing.status_code == 409
    assert missing.get_json()["error"] == "onboarding_required"

    created = client.post(
        "/api/v1/auth/google",
        json={"id_token": "token", "date_of_birth": "1995-04-12"},
    )
    assert created.status_code == 200
    assert created.get_json()["user"]["email"] == "new-google@example.com"


def test_auth_rejects_non_string_identifier_and_dob(client):
    invalid_identifier = client.post(
        "/api/v1/auth/otp/request", json={"phone": 9812345678}
    )
    assert invalid_identifier.status_code == 422

    from app.utils import otp as otp_util

    phone = "+9779812345675"
    otp_util.store_otp(phone, "123456")
    invalid_dob = client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "code": "123456", "date_of_birth": 2000},
    )
    assert invalid_dob.status_code == 422
    assert invalid_dob.get_json()["error"] == "invalid_date_format"


def test_suspended_user_cannot_refresh(client, app):
    user = make_user()
    refresh = make_refresh(user)
    user.account_status = "suspended"
    from app.extensions import db

    db.session.commit()
    response = client.post(
        "/api/v1/auth/refresh", headers={"Authorization": f"Bearer {refresh}"}
    )
    assert response.status_code == 401
    assert response.get_json()["error"] == "account_suspended"


def make_refresh(user):
    from flask_jwt_extended import create_refresh_token

    return create_refresh_token(identity=str(user.id))
