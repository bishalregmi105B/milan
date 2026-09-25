import pytest
from cryptography.fernet import Fernet

from app.config import validate_config


def _production_config(**overrides):
    config = {
        "SECRET_KEY": "s" * 48,
        "JWT_SECRET_KEY": "j" * 48,
        "ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "CORS_ALLOWED_ORIGINS": ["https://milan.app", "https://admin.milan.app"],
        "RATELIMIT_STORAGE_URI": "redis://localhost:6379/2",
        "SQLALCHEMY_DATABASE_URI": "postgresql+psycopg://prod:secret@db.example/milan",
        "CELERY_BROKER_URL": "redis://redis.example/0",
        "SPARROW_SMS_TOKEN": "configured",
        "SMTP_HOST": "smtp.example",
        "GOOGLE_CLIENT_ID": "google-client-id",
    }
    config.update(overrides)
    return config


def test_production_config_accepts_explicit_secure_values():
    validate_config(_production_config(), "prod")


def test_production_config_rejects_default_secrets():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_config(
            _production_config(SECRET_KEY="dev-only-change-me"), "prod"
        )


def test_production_config_rejects_identical_secrets():
    with pytest.raises(RuntimeError, match="different"):
        validate_config(
            _production_config(JWT_SECRET_KEY="s" * 48), "prod"
        )


def test_production_config_rejects_wildcard_or_local_cors():
    with pytest.raises(RuntimeError, match="CORS"):
        validate_config(
            _production_config(CORS_ALLOWED_ORIGINS=["*"]), "prod"
        )
    with pytest.raises(RuntimeError, match="https"):
        validate_config(
            _production_config(CORS_ALLOWED_ORIGINS=["http://localhost:3000"]),
            "prod",
        )


def test_production_config_requires_shared_services():
    with pytest.raises(RuntimeError, match="rate limiting"):
        validate_config(
            _production_config(RATELIMIT_STORAGE_URI="memory://"), "prod"
        )
    with pytest.raises(RuntimeError, match="rate limiting"):
        validate_config(_production_config(RATELIMIT_STORAGE_URI=""), "prod")
    with pytest.raises(RuntimeError, match="OTP_DEV_ECHO"):
        validate_config(_production_config(OTP_DEV_ECHO=True), "prod")


def test_production_config_treats_missing_providers_as_warnings():
    """A missing OTP channel or Google client only disables that sign-in
    method — it must NOT stop the backend (Groq companion chat and everything
    else) from booting. These warn, they do not raise."""
    validate_config(
        _production_config(SPARROW_SMS_TOKEN="", SMTP_HOST="", SMTP_USER="",
                           SMTP_PASSWORD="", GOOGLE_CLIENT_ID=""),
        "prod",
    )


def test_production_config_accepts_raw_highentropy_encryption_key():
    """crypto._fernet() derives a Fernet key from any strong secret, so the
    validator must accept a raw 63-char key exactly as the app uses it (and
    never demand a rotation that would orphan encrypted columns)."""
    raw = "n" * 63
    validate_config(_production_config(ENCRYPTION_KEY=raw), "prod")


def test_dev_config_is_not_subject_to_production_validation():
    validate_config(
        {
            "SECRET_KEY": "dev-only-change-me",
            "JWT_SECRET_KEY": "dev-only-change-me",
            "CORS_ALLOWED_ORIGINS": ["http://localhost:3000"],
        },
        "dev",
    )
