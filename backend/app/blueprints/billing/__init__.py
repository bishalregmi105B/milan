import uuid as uuid_module

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import Payment, Subscription
from app.services.payment_service import ADAPTERS, SUBSCRIPTION_TIERS_NPR, get_adapter
from app.utils.serializers import error_response

billing_bp = Blueprint("billing", __name__)


@billing_bp.post("/checkout")
@jwt_required()
def checkout():
    user_id = uuid_module.UUID(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    provider = data.get("provider")
    tier = data.get("tier")
    if provider not in ADAPTERS:
        return error_response("unsupported_provider", 422)
    if tier not in SUBSCRIPTION_TIERS_NPR:
        return error_response("unsupported_tier", 422)

    amount_npr = SUBSCRIPTION_TIERS_NPR[tier]
    payment = Payment(user_id=user_id, provider=provider, amount_npr=amount_npr,
                      status="pending", purpose=f"subscription:{tier}")
    db.session.add(payment)
    db.session.commit()

    adapter = get_adapter(provider)
    initiation = adapter.initiate(amount_npr, {"id": str(user_id)})
    return jsonify({"payment_id": str(payment.id), "amount_npr": amount_npr, **initiation}), 201


@billing_bp.post("/webhooks/<provider>")
def webhook(provider):
    if provider not in ADAPTERS:
        return error_response("unsupported_provider", 404)
    payload = request.get_json(silent=True) or {}
    signature = request.headers.get("X-Signature")
    adapter = get_adapter(provider)

    if not adapter.verify_webhook(payload, signature):
        return error_response("invalid_signature", 401)

    provider_ref = payload.get("transaction_id") or payload.get("ref") or ""
    payment = Payment.query.filter_by(id=payload.get("payment_id")).first() if payload.get("payment_id") else None
    if payment is None:
        return error_response("payment_not_found", 404)
    # Replay/dedupe guard: a provider ref may complete only ONE payment ever.
    if provider_ref and Payment.query.filter(
            Payment.provider_ref == provider_ref,
            Payment.status == "completed",
            Payment.id != payment.id).first():
        return error_response("already_used", 409)
    # Strict transition: only pending can resolve. A failed payment can never
    # be resurrected by a later replay, and completed is final.
    if payment.status != "pending":
        return jsonify({"ok": True, "ignored": payment.status})
    payment.status = "completed" if payload.get("status") == "SUCCESS" else "failed"
    payment.provider_ref = provider_ref
    if payment.status == "completed" and (payment.purpose or "").startswith("subscription:"):
        from datetime import datetime, timedelta, timezone

        tier = payment.purpose.split(":", 1)[1]
        sub = Subscription.query.filter_by(user_id=payment.user_id, status="active").first()
        if sub is None:
            sub = Subscription(user_id=payment.user_id, tier=tier,
                               started_at=datetime.now(timezone.utc))
            db.session.add(sub)
        sub.tier = tier
        sub.renews_at = datetime.now(timezone.utc) + timedelta(days=30)
        from app.services.subscription_service import invalidate_tier_cache

        invalidate_tier_cache(payment.user_id)
        db.session.commit()
    return jsonify({"ok": True})


@billing_bp.get("/plans")
def plans():
    return jsonify({"tiers": [
        {"tier": tier, "price_npr": price} for tier, price in SUBSCRIPTION_TIERS_NPR.items()
    ]})


# ---------------------------------------------------------------------------
# Phase-1 manual QR payments (build brief §8): real wallet APIs need business
# KYC, so the flow is: pick plan → scan admin's static QR → pay in the wallet
# app → submit reference + screenshot here → ADMIN approves → entitlement
# activates. Entitlement NEVER activates on submission alone. Every decision
# is audit-logged; duplicate reference IDs and screenshots are flagged.
# ---------------------------------------------------------------------------

import hashlib

from flask import current_app

from app.extensions import limiter
from app.models import (PaymentAuditLog, PaymentQrCode, PaymentSubmission,
                        Subscription)
from app.services.notification_service import queue_notification

_METHODS = ("esewa", "khalti", "fonepay", "connectips")
_REVIEW_ESTIMATE_HOURS = 12


def _run_fraud_checks(user_id, method: str, reference_id: str, screenshot_hash: str | None) -> list[str]:
    flags: list[str] = []
    if PaymentSubmission.query.filter(
            PaymentSubmission.reference_id == reference_id,
            PaymentSubmission.user_id != user_id).first():
        flags.append("reference_used_by_other_user")
    if PaymentSubmission.query.filter(
            PaymentSubmission.reference_id == reference_id,
            PaymentSubmission.user_id == user_id,
            PaymentSubmission.status.in_(("pending", "approved"))).first():
        flags.append("duplicate_reference_same_user")
    if screenshot_hash and PaymentSubmission.query.filter(
            PaymentSubmission.screenshot_hash == screenshot_hash,
            PaymentSubmission.status.in_(("pending", "approved", "rejected"))).first():
        flags.append("duplicate_screenshot")
    if PaymentSubmission.query.filter_by(user_id=user_id, status="pending").count() >= 3:
        flags.append("too_many_pending")
    return flags




_DEMO_QR_LABELS = {
    "esewa": ("eSewa DEMO", "Milan Demo Merchant — 9800000000"),
    "khalti": ("Khalti DEMO", "Milan Demo Merchant — 9800000000"),
    "fonepay": ("FonePay DEMO", "Milan Demo Merchant"),
    "connectips": ("connectIPS DEMO", "Milan Demo Merchant"),
}


def _ensure_demo_qr(method: str) -> "PaymentQrCode":
    """Seed a clearly-labelled demo QR row so the checkout flow can be walked
    end-to-end in dev/demo environments."""
    import base64

    from app.extensions import db as _db

    label, account = _DEMO_QR_LABELS.get(method, (f"{method.upper()} DEMO", "Milan Demo"))
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="240" height="280">'
        '<rect width="240" height="280" rx="12" fill="#FFFFFF" stroke="#D2D7DE"/>'
        '<rect x="45" y="40" width="150" height="150" fill="none" stroke="#0B1520" stroke-width="3" stroke-dasharray="7 5"/>'
        '<text x="120" y="120" text-anchor="middle" font-family="sans-serif" font-size="15" fill="#0B1520">DEMO QR</text>'
        f'<text x="120" y="230" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#0B1520">{label}</text>'
        '</svg>'
    )
    data_url = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
    qr = PaymentQrCode(
        method=method,
        image_url=data_url[:512],
        account_label=account,
        instructions=("DEMO checkout: scan, pay any amount, then submit the "
                      "reference number — an admin approves it and your pass activates. "
                      "Replace via Admin → Upload QR."),
        is_active=True,
    )
    _db.session.add(qr)
    _db.session.commit()
    return qr


@billing_bp.get("/qr/<method>")
@jwt_required()
def get_qr(method):
    if method not in _METHODS:
        return error_response("unsupported_provider", 422)
    qr = PaymentQrCode.query.filter_by(method=method, is_active=True).first()
    if qr is None:
        # doc 8 §C9: demo rows for all four wallets so checkout is testable
        # end-to-end before the admin uploads real QRs. Replaced the moment
        # an admin POSTs /admin/qr/<method>.
        qr = _ensure_demo_qr(method)
    return jsonify({
        "configured": True,
        "method": method,
        "image_url": qr.image_url,
        "account_label": qr.account_label,
        "instructions": qr.instructions,
    })


@billing_bp.post("/submissions")
@jwt_required()
@limiter.limit("10 per day")
def submit_payment_proof():
    user_id = uuid_module.UUID(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    tier = data.get("tier")
    method = data.get("method")
    reference_id = (data.get("reference_id") or "").strip()
    if tier not in SUBSCRIPTION_TIERS_NPR:
        return error_response("unsupported_tier", 422)
    if method not in _METHODS:
        return error_response("unsupported_provider", 422)
    if not (6 <= len(reference_id) <= 120):
        return error_response("reference_id_invalid", 422,
                              message="Enter the transaction/reference ID from your wallet app.")

    amount_npr = SUBSCRIPTION_TIERS_NPR[tier]
    screenshot_url = data.get("screenshot_url")
    screenshot_hash = None
    if screenshot_url:
        screenshot_hash = hashlib.sha256(screenshot_url.encode()).hexdigest()

    submission = PaymentSubmission(
        user_id=user_id, tier=tier, amount_npr=amount_npr, method=method,
        reference_id=reference_id, screenshot_url=screenshot_url,
        screenshot_hash=screenshot_hash, note=(data.get("note") or "")[:500],
    )
    submission.fraud_flags = _run_fraud_checks(
        user_id, method, reference_id, screenshot_hash)
    db.session.add(submission)
    db.session.flush()
    db.session.add(PaymentAuditLog(
        submission_id=submission.id, admin_id=None, action="submitted",
        detail=f"{method} {amount_npr} NPR ref={reference_id} flags={submission.fraud_flags}"))
    db.session.commit()

    return jsonify({
        "id": str(submission.id),
        "status": submission.status,
        "fraud_flags": submission.fraud_flags,
        "review_estimate_hours": _REVIEW_ESTIMATE_HOURS,
        "message": ("Payment under review. Your pass unlocks only after our team "
                    "verifies the transaction — usually within 12 hours."),
    }), 201


@billing_bp.get("/submissions/mine")
@jwt_required()
def my_submissions():
    user_id = uuid_module.UUID(get_jwt_identity())
    rows = (PaymentSubmission.query.filter_by(user_id=user_id)
            .order_by(PaymentSubmission.created_at.desc()).limit(20).all())
    return jsonify({"submissions": [{
        "id": str(s.id), "tier": s.tier, "amount_npr": s.amount_npr,
        "method": s.method, "reference_id": s.reference_id,
        "status": s.status, "fraud_flags": s.fraud_flags,
        "rejection_reason": s.rejection_reason,
        "submitted_at": s.created_at.isoformat(),
        "reviewed_at": s.reviewed_at.isoformat() if s.reviewed_at else None,
    } for s in rows]})


def _grant_subscription(user_id, tier: str) -> None:
    """The ONLY path that activates an entitlement (admin approval or verified
    webhook). Never called on submission."""
    from datetime import datetime, timedelta, timezone

    sub = Subscription.query.filter_by(user_id=user_id, status="active").first()
    if sub is None:
        sub = Subscription(user_id=user_id, tier=tier,
                           started_at=datetime.now(timezone.utc))
        db.session.add(sub)
    sub.tier = tier
    sub.renews_at = datetime.now(timezone.utc) + timedelta(days=30)
    sub.status = "active"
    # kill the per-worker tier cache so the pass is usable immediately
    from app.services.subscription_service import invalidate_tier_cache

    invalidate_tier_cache(user_id)


@billing_bp.get("/admin/submissions")
@jwt_required()
def admin_list_submissions():
    if not _is_admin():
        return error_response("forbidden", 403)
    status = request.args.get("status", "pending")
    query = PaymentSubmission.query
    if status != "all":
        query = query.filter_by(status=status)
    rows = query.order_by(PaymentSubmission.created_at.asc()).limit(100).all()
    out = []
    for s in rows:
        from app.models import User

        user = db.session.get(User, s.user_id)
        out.append({
            "id": str(s.id), "user_id": str(s.user_id),
            "user_email": user.email if user else None,
            "tier": s.tier, "amount_npr": s.amount_npr, "method": s.method,
            "reference_id": s.reference_id, "screenshot_url": s.screenshot_url,
            "note": s.note, "status": s.status, "fraud_flags": s.fraud_flags,
            "submitted_at": s.created_at.isoformat(),
        })
    return jsonify({"submissions": out})


@billing_bp.post("/admin/submissions/<submission_id>/review")
@jwt_required()
@limiter.limit("60 per hour")
def admin_review_submission(submission_id):
    """Approve or reject with an audit log; approval grants the entitlement
    immediately and notifies the user; rejection requires a reason."""
    if not _is_admin():
        return error_response("forbidden", 403)
    admin_id = uuid_module.UUID(get_jwt_identity())
    submission = db.session.get(PaymentSubmission, uuid_module.UUID(submission_id))
    if submission is None:
        return error_response("not_found", 404)
    if submission.status != "pending":
        return error_response("already_reviewed", 409)

    data = request.get_json(silent=True) or {}
    decision = data.get("decision")
    if decision not in ("approve", "reject"):
        return error_response("decision_required", 422)
    reason = (data.get("reason") or "").strip()
    if decision == "reject" and not reason:
        return error_response("rejection_reason_required", 422)

    if decision == "approve":
        submission.status = "approved"
        _grant_subscription(submission.user_id, submission.tier)
        queue_notification(
            submission.user_id, "promo",
            "Milan pass activated 🎉",
            f"Your {submission.tier.title()} pass is live. Enjoy!",
            data={"type": "payment_approved"})
    else:
        submission.status = "rejected"
        submission.rejection_reason = reason[:300]
        queue_notification(
            submission.user_id, "promo",
            "Payment needs another look",
            f"We couldn't verify your payment ({submission.reference_id}). Reason: {reason[:120]} — you can resubmit.",
            data={"type": "payment_rejected", "submission_id": str(submission.id)})

    submission.reviewed_by = admin_id
    submission.reviewed_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    db.session.add(PaymentAuditLog(
        submission_id=submission.id, admin_id=admin_id, action=decision,
        detail=reason[:500] or None))
    db.session.commit()
    return jsonify({"id": str(submission.id), "status": submission.status})


def _is_admin() -> bool:
    from flask_jwt_extended import get_jwt

    return get_jwt().get("role") == "admin"


@billing_bp.post("/admin/qr/<method>")
@jwt_required()
@limiter.limit("10 per hour")
def admin_upload_qr(method):
    """Upload/replace the static payment QR for a wallet method. The image is
    stored via media_service and becomes live immediately."""
    from app.services import media_service

    if not _is_admin():
        return error_response("forbidden", 403)
    if method not in _METHODS:
        return error_response("unsupported_provider", 422)
    file = request.files.get("image")
    if file is None:
        return error_response("file_required", 422)
    admin_id = uuid_module.UUID(get_jwt_identity())
    result = media_service.upload_media(
        admin_id, "photo", file.read(), file.mimetype or "image/png",
        file.filename or "qr.png")
    qr = PaymentQrCode.query.filter_by(method=method).first()
    if qr is None:
        qr = PaymentQrCode(method=method)
        db.session.add(qr)
    qr.image_url = result["url"]
    qr.account_label = (request.form.get("account_label") or qr.account_label)
    qr.instructions = (request.form.get("instructions") or qr.instructions)
    qr.is_active = True
    db.session.commit()
    return jsonify({"method": method, "image_url": qr.image_url,
                    "account_label": qr.account_label})
