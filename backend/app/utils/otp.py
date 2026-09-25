import hashlib
import time

from flask import current_app

_otp_store: dict[str, tuple[str, float]] = {}
_redis_client = None


def _is_production() -> bool:
    return current_app.config.get("MILAN_ENV") in {"prod", "production"}


def _hash_code(code: str) -> str:
    return hashlib.sha256(str(code).encode("utf-8")).hexdigest()


def reserve_otp_send(identifier: str) -> bool:
    """Reserve a resend slot once, shared by all workers when Redis exists."""
    ttl = int(current_app.config["OTP_RESEND_COOLDOWN_SECONDS"])
    key = f"otp_sent:{identifier}"
    client = _redis()
    if client:
        try:
            return bool(client.set(key, "1", nx=True, ex=ttl))
        except Exception as exc:  # noqa: BLE001
            if _is_production():
                raise RuntimeError("OTP cooldown store unavailable") from exc
    if _is_production():
        raise RuntimeError("OTP cooldown store unavailable")
    now = time.time()
    entry = _otp_store.get(key)
    if entry is not None and entry[1] > now:
        return False
    _otp_store[key] = ("1", now + ttl)
    return True


def _redis():
    """Shared Redis-backed OTP store so all gunicorn workers see the same
    codes (memory dict is per-process and breaks multi-worker deployments).
    Falls back to the in-process dict when Redis is unreachable; tests pin
    the memory store so assertions are deterministic without a Redis daemon."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        if current_app.config.get("TESTING"):
            _redis_client = False
            return _redis_client
        import os

        import redis as redis_lib

        url = os.environ.get("OTP_REDIS_URL") or os.environ.get(
            "CELERY_BROKER_URL", "redis://localhost:6379/0"
        )
        client = redis_lib.Redis.from_url(url, db=5, socket_connect_timeout=2)
        client.ping()
        _redis_client = client
    except Exception:  # noqa: BLE001 — fall back to memory on any Redis failure
        current_app.logger.warning("Redis OTP store unavailable; using in-process memory")
        _redis_client = False
    return _redis_client


def store_otp(phone: str, code: str) -> None:
    ttl = current_app.config["OTP_TTL_SECONDS"]
    digest = _hash_code(code)
    client = _redis()
    if client:
        try:
            client.setex(f"otp:{phone}", ttl, digest)
            return
        except Exception as exc:  # noqa: BLE001
            if _is_production():
                raise RuntimeError("OTP store unavailable") from exc
    if _is_production():
        raise RuntimeError("OTP store unavailable")
    _otp_store[f"otp:{phone}"] = (digest, time.time() + ttl)


def peek_stored_otp(phone: str, code: str) -> bool:
    """Check an OTP without consuming it, for the onboarding-required step."""
    key = f"otp:{phone}"
    digest = _hash_code(code)
    client = _redis()
    if client:
        try:
            stored = client.get(key)
            return stored is not None and stored.decode() == digest
        except Exception as exc:  # noqa: BLE001
            if _is_production():
                raise RuntimeError("OTP store unavailable") from exc
    if _is_production():
        raise RuntimeError("OTP store unavailable")
    entry = _otp_store.get(key)
    if entry is None:
        return False
    stored_digest, expires_at = entry
    if time.time() > expires_at:
        _otp_store.pop(key, None)
        return False
    return stored_digest == digest


def verify_stored_otp(phone: str, code: str) -> bool:
    key = f"otp:{phone}"
    digest = _hash_code(code)
    client = _redis()
    if client:
        try:
            getdel = getattr(client, "getdel", None)
            stored = getdel(key) if getdel is not None else client.get(key)
            if getdel is None and stored is not None:
                client.delete(key)
            return stored is not None and stored.decode() == digest
        except Exception as exc:  # noqa: BLE001
            if _is_production():
                raise RuntimeError("OTP store unavailable") from exc
    if _is_production():
        raise RuntimeError("OTP store unavailable")
    entry = _otp_store.get(key)
    if entry is None:
        return False
    stored_digest, expires_at = entry
    if time.time() > expires_at:
        _otp_store.pop(key, None)
        return False
    if stored_digest != digest:
        return False
    _otp_store.pop(key, None)
    return True


def send_sms_otp(phone: str, code: str) -> bool:
    token = current_app.config.get("SPARROW_SMS_TOKEN")
    from_addr = current_app.config.get("SPARROW_SMS_FROM", "Milan")
    if not token:
        if current_app.config.get("OTP_DEV_ECHO"):
            current_app.logger.info("OTP provider is not configured; local echo mode is enabled")
            return True
        current_app.logger.warning("OTP provider is not configured; refusing to send an SMS")
        return False
    import requests

    try:
        resp = requests.post(
            "https://sms.sparrowsms.com/v2/sms",
            data={"token": token, "from": from_addr, "to": phone,
                  "text": f"Milan: your verification code is {code}"},
            timeout=10,
        )
        return resp.status_code == 200
    except requests.RequestException:
        current_app.logger.exception("Sparrow SMS send failed")
        return False


def send_email_otp(email: str, code: str) -> bool:
    """SMTP when configured; otherwise the code is logged (dev mode) like SMS."""
    host = current_app.config.get("SMTP_HOST")
    if not host:
        if current_app.config.get("OTP_DEV_ECHO"):
            current_app.logger.info("OTP provider is not configured; local echo mode is enabled")
            return True
        current_app.logger.warning("OTP provider is not configured; refusing to send an email")
        return False
    import smtplib
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["Subject"] = "Your Milan verification code"
    msg["From"] = current_app.config.get("SMTP_FROM", "Milan <no-reply@milan.app>")
    msg["To"] = email
    msg.set_content(
        f"Welcome to Milan.\n\nYour verification code is {code}.\n"
        f"It expires in {current_app.config['OTP_TTL_SECONDS'] // 60} minutes.\n"
        "If you didn't request this, you can safely ignore this email."
    )
    try:
        port = int(current_app.config.get("SMTP_PORT", 587))
        user = current_app.config.get("SMTP_USER")
        password = current_app.config.get("SMTP_PASSWORD")
        use_tls = bool(current_app.config.get("SMTP_USE_TLS", True))
        if use_tls:
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.ehlo()
                server.starttls()
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        else:
            # Plain SMTP (e.g. local Postfix on 127.0.0.1:25).
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.ehlo()
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        return True
    except (smtplib.SMTPException, OSError):
        current_app.logger.exception("Email OTP send failed for %s", email)
        return False


_VERIFY_ATTEMPTS = 5


def consume_verify_attempt(identifier: str) -> bool:
    """Record one failed verification attempt and report whether budget remains."""
    key = f"otp_attempts:{identifier}"
    client = _redis()
    if client:
        try:
            count = client.incr(key)
            if count == 1:
                client.expire(key, 600)
            return int(count) <= _VERIFY_ATTEMPTS
        except Exception as exc:  # noqa: BLE001
            if _is_production():
                raise RuntimeError("OTP attempt store unavailable") from exc
    if _is_production():
        raise RuntimeError("OTP attempt store unavailable")
    entry = _otp_store.get(key)
    count = (int(entry[0]) + 1) if entry else 1
    _otp_store[key] = (count, time.time() + 600)
    return count <= _VERIFY_ATTEMPTS


def clear_verify_attempts(identifier: str) -> None:
    key = f"otp_attempts:{identifier}"
    client = _redis()
    if client:
        try:
            client.delete(key)
            return
        except Exception as exc:  # noqa: BLE001
            if _is_production():
                raise RuntimeError("OTP attempt store unavailable") from exc
    _otp_store.pop(key, None)


def clear_otp_cooldown(identifier: str) -> None:
    key = f"otp_sent:{identifier}"
    client = _redis()
    if client:
        try:
            client.delete(key)
            return
        except Exception as exc:  # noqa: BLE001
            if _is_production():
                raise RuntimeError("OTP cooldown store unavailable") from exc
    _otp_store.pop(key, None)


def destroy_otp(identifier: str) -> None:
    key = f"otp:{identifier}"
    client = _redis()
    if client:
        try:
            client.delete(key)
            return
        except Exception:  # noqa: BLE001
            pass
    _otp_store.pop(key, None)
