import os
from datetime import timedelta
from urllib.parse import urlparse


_WEAK_SECRETS = {
    "",
    "change-me",
    "change-me-too",
    "dev-only-change-me",
    "dev-only-change-me-too",
    "secret",
    "test-key",
}


def _is_weak_secret(value: object) -> bool:
    text = str(value or "").strip()
    return text.lower() in _WEAK_SECRETS or len(text) < 32


def validate_config(config, environment: str) -> None:
    """Fail closed for production configuration without breaking dev/tests.

    Flask's ``from_object`` reads class attributes and never calls a config
    class constructor, so production validation must be a pure function called
    by the application factory after loading the class.
    """
    env = (environment or "").strip().lower()
    if env not in {"prod", "production"}:
        return

    errors: list[str] = []
    secret = str(config.get("SECRET_KEY") or "")
    jwt_secret = str(config.get("JWT_SECRET_KEY") or "")
    if _is_weak_secret(secret):
        errors.append("SECRET_KEY must be a strong non-default value")
    if _is_weak_secret(jwt_secret):
        errors.append("JWT_SECRET_KEY must be a strong non-default value")
    if secret and secret == jwt_secret:
        errors.append("SECRET_KEY and JWT_SECRET_KEY must be different")

    encryption_key = str(config.get("ENCRYPTION_KEY") or "")
    if not encryption_key:
        errors.append("MILAN_ENCRYPTION_KEY is required")
    elif _is_weak_secret(encryption_key):
        errors.append("MILAN_ENCRYPTION_KEY must be a strong non-default value")
    else:
        # Validate the key the SAME way app.utils.crypto._fernet() consumes it:
        # a raw high-entropy secret is derived into a Fernet key (padded/trimmed
        # to 32 bytes, base64'd). Rejecting such a key as "not a Fernet key"
        # would fail a key the app uses happily — and rotating it to a fresh
        # Fernet key would silently orphan every already-encrypted phone/
        # location column in the database.
        try:
            import base64

            from cryptography.fernet import Fernet

            candidate = encryption_key
            if len(candidate) < 44 or not candidate.endswith("="):
                candidate = base64.urlsafe_b64encode(
                    candidate.encode().ljust(32)[:32]).decode()
            Fernet(candidate.encode())
        except (ValueError, TypeError):
            errors.append("MILAN_ENCRYPTION_KEY must be a valid encryption secret")

    origins = [str(origin).strip() for origin in (config.get("CORS_ALLOWED_ORIGINS") or [])]
    if not origins or "*" in origins:
        errors.append("production CORS origins must be explicit and non-wildcard")
    for origin in origins:
        parsed = urlparse(origin)
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append("production CORS origins must use https URLs")
            break

    rate_limit_storage = str(config.get("RATELIMIT_STORAGE_URI") or "").strip()
    if not rate_limit_storage or rate_limit_storage.startswith("memory://"):
        errors.append("production rate limiting must use Redis or another shared store")
    if "milan:milan@localhost" in str(config.get("SQLALCHEMY_DATABASE_URI") or ""):
        errors.append("production database URI must not use the local development credentials")
    if not str(config.get("CELERY_BROKER_URL") or "").startswith(("redis://", "rediss://")):
        errors.append("production Celery broker must use Redis")
    if config.get("OTP_DEV_ECHO"):
        errors.append("OTP_DEV_ECHO must be disabled in production")

    # Optional delivery providers are NOT security-critical: a missing OTP
    # channel or Google client only disables that sign-in method (the routes
    # already degrade gracefully), so they warn rather than block boot. Making
    # them hard failures previously kept an otherwise-healthy backend — Groq
    # companion chat included — from starting at all.
    warnings: list[str] = []
    smtp_ready = bool(config.get("SMTP_HOST") and config.get("SMTP_USER")
                      and config.get("SMTP_PASSWORD"))
    if not config.get("SPARROW_SMS_TOKEN") and not smtp_ready:
        warnings.append("no OTP delivery provider configured (SMS token or full "
                        "SMTP) — phone/email login cannot send codes")
    if not config.get("GOOGLE_CLIENT_ID"):
        warnings.append("GOOGLE_CLIENT_ID not set — Google sign-in is disabled")

    if errors:
        raise RuntimeError("Invalid production configuration: " + "; ".join(errors))

    if warnings:
        import logging

        logging.getLogger("app.config").warning(
            "production config warnings: %s", "; ".join(warnings))


class BaseConfig:
    SECRET_KEY = os.environ.get("MILAN_SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.environ.get("MILAN_JWT_SECRET_KEY", os.environ.get("MILAN_SECRET_KEY", "dev-only-change-me"))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_ERROR_401_MESSAGE = "Authentication required"

    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    GROQ_BASE_URL = os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

    SPARROW_SMS_TOKEN = os.environ.get("SPARROW_SMS_TOKEN", "")
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    ONESIGNAL_APP_ID = os.environ.get("ONESIGNAL_APP_ID", "")
    ONESIGNAL_API_KEY = os.environ.get("ONESIGNAL_API_KEY", "")
    ESEWA_SECRET_KEY = os.environ.get("ESEWA_SECRET_KEY", "")
    SPARROW_SMS_FROM = os.environ.get("SPARROW_SMS_FROM", "Milan")

    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM = os.environ.get("SMTP_FROM", "Milan <no-reply@milan.app>")
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "1") == "1"

    MEDIA_S3_ENDPOINT = os.environ.get("MEDIA_S3_ENDPOINT", "")
    MEDIA_S3_BUCKET = os.environ.get("MEDIA_S3_BUCKET", "milan-media")
    MEDIA_S3_ACCESS_KEY = os.environ.get("MEDIA_S3_ACCESS_KEY", "")
    MEDIA_S3_SECRET_KEY = os.environ.get("MEDIA_S3_SECRET_KEY", "")
    MEDIA_CDN_BASE_URL = os.environ.get("MEDIA_CDN_BASE_URL", "")

    ESEWA_MERCHANT_CODE = os.environ.get("ESEWA_MERCHANT_CODE", "")
    KHALTI_SECRET_KEY = os.environ.get("KHALTI_SECRET_KEY", "")
    FONEPAY_MERCHANT_ID = os.environ.get("FONEPAY_MERCHANT_ID", "")
    CONNECTIPS_MERCHANT_ID = os.environ.get("CONNECTIPS_MERCHANT_ID", "")

    ENCRYPTION_KEY = os.environ.get("MILAN_ENCRYPTION_KEY", "")

    CORS_ALLOWED_ORIGINS = [
        origin.strip()
        for origin in os.environ.get(
            "MILAN_CORS_ORIGINS",
            # Dev default includes local web/app origins so the browser and
            # emulator can actually reach this API out of the box.
            "http://localhost:3000,http://127.0.0.1:3000,"
            "http://localhost:8080,http://10.0.2.2:3000,"
            "https://milan.app,https://admin.milan.app"
            if os.environ.get("MILAN_ENV", os.environ.get("FLASK_ENV", "dev")) != "prod"
            else "https://milan.app,https://admin.milan.app",
        ).split(",")
        if origin.strip()
    ]

    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    CACHE_TYPE = "SimpleCache"

    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

    SAATHI_PROACTIVE_DAILY_CAP_DEFAULT = int(os.environ.get("SAATHI_PROACTIVE_DAILY_CAP", "1"))
    SAATHI_MEMORY_SUMMARY_EVERY_TURNS = int(os.environ.get("SAATHI_MEMORY_SUMMARY_EVERY_TURNS", "20"))
    SAATHI_RAW_CONTEXT_TURNS = 10
    # Realism engine (master plan §4): proactive quiet hours are Asia/Kathmandu
    # local; sends inside the window are deferred to its end unless the user
    # messaged in the last 30 minutes.
    SAATHI_QUIET_HOURS = (23, 7)
    SAATHI_DELAYED_REPLY_RATE = float(os.environ.get("SAATHI_DELAYED_REPLY_RATE", "0.08"))

    # ── Companion context engine (doc 8 §C2) ──────────────────────────────
    # The old fixed 10-turn window + full memory dump meant month 3 of a
    # relationship cost 40x month 1 and then silently truncated. These bound
    # the prompt so a 2,000-message bond costs the same per turn as a new one.
    COMPANION_CONTEXT_TOKEN_BUDGET = int(
        os.environ.get("COMPANION_CONTEXT_TOKEN_BUDGET", "3000"))
    COMPANION_COMPACT_EVERY_TURNS = int(
        os.environ.get("COMPANION_COMPACT_EVERY_TURNS", "24"))
    COMPANION_RAW_TURNS_MIN = int(os.environ.get("COMPANION_RAW_TURNS_MIN", "6"))
    COMPANION_RAW_TURNS_MAX = int(os.environ.get("COMPANION_RAW_TURNS_MAX", "24"))
    # Initiative engine (doc 8 §C5): how often the scorer runs, and how often a
    # dangling question earns one soft follow-up.
    COMPANION_INITIATIVE_TICK_MINUTES = int(
        os.environ.get("COMPANION_INITIATIVE_TICK_MINUTES", "10"))
    COMPANION_DOUBLE_TEXT_RATE = float(
        os.environ.get("COMPANION_DOUBLE_TEXT_RATE", "0.25"))

    # Optional premium TTS (master plan §12.1): when empty, edge-tts is primary.
    ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
    ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "")

    OTP_RATE_LIMIT = os.environ.get("MILAN_OTP_RATELIMIT", "5 per 10 minutes")
    OTP_LENGTH = 6
    OTP_TTL_SECONDS = 300
    OTP_RESEND_COOLDOWN_SECONDS = 60
    # Never log or return OTPs implicitly. Test/dev can opt into a local echo
    # explicitly; production validation keeps this disabled.
    OTP_DEV_ECHO = os.environ.get("OTP_DEV_ECHO", "0") == "1"

    MAX_PHOTOS_PER_PROFILE = 6
    MIN_PHOTOS_PER_PROFILE = 2


class DevConfig(BaseConfig):
    DEBUG = True
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://milan:milan@localhost:5432/milan"
    )


class TestConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL", "sqlite://")
    GROQ_API_KEY = "test-key"
    ENCRYPTION_KEY = ""
    MEDIA_S3_ENDPOINT = ""
    SPARROW_SMS_TOKEN = ""
    RATELIMIT_ENABLED = False
    OTP_DEV_ECHO = True


class StagingConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://milan:milan@localhost:5432/milan"
    )


class ProdConfig(BaseConfig):
    DEBUG = False
    PROPAGATE_EXCEPTIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://milan:milan@localhost:5432/milan"
    )


config_by_name = {
    "dev": DevConfig,
    "test": TestConfig,
    "staging": StagingConfig,
    "prod": ProdConfig,
}
