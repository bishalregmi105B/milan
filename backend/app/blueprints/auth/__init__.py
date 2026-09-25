import uuid as uuid_module

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity

from app.extensions import db, limiter
from app.models import User
from app.utils import otp as otp_util
from app.utils.crypto import new_otp
from app.utils.serializers import error_response
from app.utils.validators import (
    normalize_email,
    normalize_phone,
    validate_email,
    validate_phone,
    validate_age_18,
)

auth_bp = Blueprint("auth", __name__)


def _resolve_identifier(data: dict):
    """Returns ((kind, value), None) or (None, error_response)."""
    phone_raw = data.get("phone")
    email_raw = data.get("email")
    phone = phone_raw.replace(" ", "") if isinstance(phone_raw, str) else ""
    email = email_raw.strip() if isinstance(email_raw, str) else ""
    if phone:
        if not validate_phone(phone):
            return None, error_response("invalid_phone", 422)
        return ("phone", normalize_phone(phone)), None
    if email:
        if not validate_email(email):
            return None, error_response("invalid_email", 422)
        return ("email", normalize_email(email)), None
    return None, error_response("identifier_required", 422)


@auth_bp.post("/otp/request")
@limiter.limit(lambda: current_app.config["OTP_RATE_LIMIT"])
def request_otp():
    data = request.get_json(silent=True) or {}
    identifier, err = _resolve_identifier(data)
    if err is not None:
        return err
    kind, value = identifier

    try:
        if not otp_util.reserve_otp_send(value):
            return error_response("rate_limited", 429)
    except RuntimeError:
        return error_response("otp_temporarily_unavailable", 503)

    code = new_otp(current_app.config["OTP_LENGTH"])
    try:
        otp_util.store_otp(value, code)
        sent = (otp_util.send_sms_otp(value, code)
                if kind == "phone"
                else otp_util.send_email_otp(value, code))
    except RuntimeError:
        return error_response("otp_temporarily_unavailable", 503)

    # Deliberately return the same response for an existing account, a new
    # account, and a provider outage. The client must not learn account
    # existence before the code is verified.
    if not sent:
        current_app.logger.warning("OTP delivery failed; returning a uniform request response")
    return jsonify({
        "sent": True,
        "resend_cooldown_seconds": current_app.config["OTP_RESEND_COOLDOWN_SECONDS"],
    })


def store_otp_and_send(phone: str, code: str) -> bool:
    """Kept for backward compatibility with existing callers/tests."""
    otp_util.store_otp(phone, code)
    return otp_util.send_sms_otp(phone, code)


@auth_bp.post("/otp/verify")
@limiter.limit("10 per 10 minutes", cost=1)
def verify_otp():
    data = request.get_json(silent=True) or {}
    identifier, err = _resolve_identifier(data)
    if err is not None:
        return err
    kind, value = identifier
    code_raw = data.get("code")
    code = code_raw if isinstance(code_raw, str) else ""
    dob_raw = data.get("date_of_birth")
    if dob_raw is not None and not isinstance(dob_raw, str):
        return error_response("invalid_date_format", 422)
    user = User.query.filter_by(phone=value).first() if kind == "phone" \
        else User.query.filter_by(email=value).first()

    # Do not consume the code merely to tell the client that onboarding is
    # required. Validate it first so a wrong code has the same failure shape
    # for known and unknown identifiers, then let the client submit the same
    # code again with a real DOB.
    if not dob_raw and (user is None or user.date_of_birth is None):
        try:
            code_is_valid = otp_util.peek_stored_otp(value, code)
        except RuntimeError:
            return error_response("otp_temporarily_unavailable", 503)
        if not code_is_valid:
            try:
                attempts_remaining = otp_util.consume_verify_attempt(value)
            except RuntimeError:
                return error_response("otp_temporarily_unavailable", 503)
            if not attempts_remaining:
                otp_util.destroy_otp(value)
            return error_response("invalid_or_expired_otp", 401)
        return error_response("onboarding_required", 409)

    # Brute-force guard: only failed verifications consume the attempt budget.
    try:
        verified = otp_util.verify_stored_otp(value, code)
    except RuntimeError:
        return error_response("otp_temporarily_unavailable", 503)
    if not verified:
        try:
            attempts_remaining = otp_util.consume_verify_attempt(value)
        except RuntimeError:
            return error_response("otp_temporarily_unavailable", 503)
        if not attempts_remaining:
            otp_util.destroy_otp(value)
        return error_response("invalid_or_expired_otp", 401)
    otp_util.clear_verify_attempts(value)
    otp_util.clear_otp_cooldown(value)

    parsed_dob = None
    if dob_raw:
        from datetime import datetime

        try:
            parsed_dob = datetime.strptime(dob_raw, "%Y-%m-%d").date()
        except ValueError:
            return error_response("invalid_date_format", 422)
    if user is None:
        if parsed_dob is None or not validate_age_18(parsed_dob):
            return error_response("age_gate_18_plus", 403)
        if kind == "phone":
            user = User(phone=value, date_of_birth=parsed_dob, auth_provider="phone")
        else:
            user = User(email=value, date_of_birth=parsed_dob, auth_provider="email")
        db.session.add(user)
        db.session.flush()
    elif user.account_status != "active":
        return error_response("account_suspended", 403)
    elif user.date_of_birth is None:
        if parsed_dob is None or not validate_age_18(parsed_dob):
            return error_response("age_gate_18_plus", 403)
        user.date_of_birth = parsed_dob
    elif not validate_age_18(user.date_of_birth):
        return error_response("age_gate_18_plus", 403)

    db.session.commit()
    access = create_access_token(identity=str(user.id))
    refresh = create_refresh_token(identity=str(user.id))
    return jsonify({
        "access_token": access,
        "refresh_token": refresh,
        "user": {"id": str(user.id), "phone": user.phone, "email": user.email,
                 "auth_provider": user.auth_provider,
                 "is_verified": user.is_verified,
                 "has_profile": user.profile is not None},
    })


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    try:
        user_id = uuid_module.UUID(identity)
    except (TypeError, ValueError, AttributeError):
        return error_response("invalid_or_missing_token", 401)
    user = db.session.get(User, user_id)
    if user is None or user.deleted_at is not None or user.account_status != "active":
        return error_response("account_suspended", 403)
    return jsonify({"access_token": create_access_token(identity=identity)})


@auth_bp.post("/google")
@limiter.limit("10 per minute")
def google_login():
    """Verify a Google ID token and issue a session only for an existing,
    age-eligible account. Google email verification is not age verification."""
    import requests as _requests
    from datetime import datetime

    data = request.get_json(silent=True) or {}
    id_token_raw = data.get("id_token")
    id_token = id_token_raw.strip() if isinstance(id_token_raw, str) else ""
    if not id_token:
        return error_response("invalid_or_missing_token", 422)

    try:
        info = _requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token}, timeout=10,
        ).json()
    except Exception:  # noqa: BLE001
        return error_response("network_error", 502)
    if "email" not in info or info.get("error"):
        return error_response("invalid_or_expired_otp", 401)

    expected_aud = current_app.config.get("GOOGLE_CLIENT_ID")
    if not expected_aud:
        return error_response("google_not_configured", 503)
    if info.get("aud") != expected_aud:
        return error_response("invalid_or_expired_otp", 401)
    if info.get("iss") not in {"https://accounts.google.com", "accounts.google.com"}:
        return error_response("invalid_or_expired_otp", 401)
    if str(info.get("email_verified", "")).lower() != "true":
        return error_response("invalid_or_expired_otp", 401)

    email_value = info.get("email")
    if not isinstance(email_value, str):
        return error_response("invalid_or_expired_otp", 401)
    email = normalize_email(email_value)
    user = User.query.filter_by(email=email).first()
    dob_raw = data.get("date_of_birth")
    if dob_raw is not None and not isinstance(dob_raw, str):
        return error_response("invalid_date_format", 422)
    parsed_dob = None
    if dob_raw:
        from datetime import datetime

        try:
            parsed_dob = datetime.strptime(dob_raw, "%Y-%m-%d").date()
        except ValueError:
            return error_response("invalid_date_format", 422)

    if user is None or user.date_of_birth is None:
        if parsed_dob is None:
            # Google proves the email, not age. The client must provide a
            # real date before a full session is issued.
            return error_response("onboarding_required", 409)
        if not validate_age_18(parsed_dob):
            return error_response("age_gate_18_plus", 403)
        if user is None:
            user = User(email=email, auth_provider="google",
                        date_of_birth=parsed_dob)
            db.session.add(user)
            db.session.flush()
        else:
            user.date_of_birth = parsed_dob
    if user.account_status != "active":
        return error_response("account_suspended", 403)
    if not validate_age_18(user.date_of_birth):
        return error_response("age_gate_18_plus", 403)
    db.session.commit()
    access = create_access_token(identity=str(user.id))
    refresh = create_refresh_token(identity=str(user.id))
    return jsonify({
        "access_token": access,
        "refresh_token": refresh,
        "user": {"id": str(user.id), "email": user.email,
                 "auth_provider": user.auth_provider,
                 "is_verified": user.is_verified,
                 "has_profile": user.profile is not None},
    })
