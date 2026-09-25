from app.models import User
from tests.conftest import make_user


def test_otp_request_does_not_reveal_account_existence(client, monkeypatch):
    from app.blueprints import auth as auth_module

    user = make_user(phone="+9779812345670")
    monkeypatch.setattr(auth_module.otp_util, "send_sms_otp", lambda phone, code: False)

    known = client.post("/api/v1/auth/otp/request", json={"phone": user.phone})
    unknown = client.post("/api/v1/auth/otp/request", json={"phone": "+9779812345671"})

    assert known.status_code == unknown.status_code == 200
    assert known.get_json() == unknown.get_json()
    assert "account_exists" not in known.get_json()


def test_otp_request_enforces_resend_cooldown(client, monkeypatch):
    from app.blueprints import auth as auth_module

    monkeypatch.setattr(auth_module.otp_util, "send_sms_otp", lambda phone, code: True)
    phone = "+9779812345672"
    first = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    second = client.post("/api/v1/auth/otp/request", json={"phone": phone})

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.get_json()["error"] == "rate_limited"


def test_otp_provider_failure_does_not_log_code_or_identifier(client, monkeypatch, caplog):
    from app.blueprints import auth as auth_module

    code = "654321"
    phone = "+9779812345673"
    monkeypatch.setattr(auth_module, "new_otp", lambda length: code)
    monkeypatch.setattr(auth_module.otp_util, "send_sms_otp", lambda identifier, value: False)

    with caplog.at_level("INFO"):
        response = client.post("/api/v1/auth/otp/request", json={"phone": phone})

    assert response.status_code == 200
    assert code not in caplog.text
    assert phone not in caplog.text


def test_unknown_account_valid_code_requires_explicit_age_step(client, monkeypatch):
    from app.blueprints import auth as auth_module

    code = "112233"
    phone = "+9779812345674"
    monkeypatch.setattr(auth_module, "new_otp", lambda length: code)
    monkeypatch.setattr(auth_module.otp_util, "send_sms_otp", lambda identifier, value: True)
    client.post("/api/v1/auth/otp/request", json={"phone": phone})

    response = client.post("/api/v1/auth/otp/verify", json={
        "phone": phone,
        "code": code,
    })
    assert response.status_code == 409
    assert response.get_json()["error"] == "onboarding_required"
    assert User.query.filter_by(phone=phone).first() is None
