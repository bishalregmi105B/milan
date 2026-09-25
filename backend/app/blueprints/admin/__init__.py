import uuid as uuid_module
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from app.extensions import db
from app.models import (
    Circle,
    Match,
    ModerationEvent,
    Notification,
    Payment,
    Report,
    SaathiSession,
    ScamFlag,
    User,
)
from app.services.moderation_service import record_admin_action
from app.utils.pagination import paginate
from app.utils.serializers import error_response

admin_bp = Blueprint("admin", __name__)


def require_admin():
    claims = get_jwt()
    if claims.get("role") not in ("moderator", "admin", "founder"):
        return False
    return True


def admin_required(fn):
    from functools import wraps

    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        if not require_admin():
            return error_response("forbidden", 403)
        return fn(*args, **kwargs)

    return wrapper


@admin_bp.get("/moderation/queue")
@admin_required
def moderation_queue():
    open_reports = Report.query.filter_by(status="open").order_by(Report.created_at.desc()).all()
    unreviewed_flags = ScamFlag.query.filter_by(reviewed=False).order_by(
        ScamFlag.confidence.desc()).limit(100).all()

    items = []
    for report in open_reports:
        severity = "high" if report.reason in (
            "scam", "scam_or_fraud", "harassment", "threat", "threats", "underage",
        ) else "normal"
        items.append({
            "case_type": "report",
            "id": str(report.id),
            "severity": severity,
            "reason": report.reason,
            "target_id": str(report.target_id),
            "reporter_id": str(report.reporter_id),
            "created_at": report.created_at.isoformat(),
        })
    for flag in unreviewed_flags:
        items.append({
            "case_type": "scam_flag",
            "id": str(flag.id),
            "severity": flag.risk_level,
            "patterns": flag.pattern_matched,
            "confidence": flag.confidence,
            "match_id": str(flag.match_id) if flag.match_id else None,
            "flagged_user_id": str(flag.flagged_user_id) if flag.flagged_user_id else None,
            "created_at": flag.created_at.isoformat(),
        })

    severity_order = {"high": 0, "low": 1, "normal": 2}
    items.sort(key=lambda i: (severity_order.get(i["severity"], 3), i["created_at"]), reverse=False)
    return jsonify({"queue": items})


@admin_bp.post("/moderation/cases/<case_type>/<case_id>/resolve")
@admin_required
def resolve_case(case_type, case_id):
    actor_id = uuid_module.UUID(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    if action not in ("dismiss", "warn_user", "suspend", "escalate"):
        return error_response("invalid_action", 422)

    if case_type == "report":
        row = db.session.get(Report, uuid_module.UUID(case_id))
        if row is None:
            return error_response("not_found", 404)
        row.status = {"dismiss": "dismissed", "warn_user": "warned",
                      "suspend": "suspended", "escalate": "escalated"}[action]
        row.resolution_note = data.get("note")
        if action == "suspend":
            target = db.session.get(User, row.target_id)
            if target is not None:
                target.account_status = "suspended"
    elif case_type == "scam_flag":
        row = db.session.get(ScamFlag, uuid_module.UUID(case_id))
        if row is None:
            return error_response("not_found", 404)
        row.reviewed = True
        if action == "suspend" and row.flagged_user_id:
            target = db.session.get(User, row.flagged_user_id)
            if target is not None:
                target.account_status = "suspended"
    else:
        return error_response("invalid_case_type", 422)

    db.session.commit()
    if case_type == "report" and action == "dismiss":
        from app.services import trust_service

        target = db.session.get(User, row.target_id)
        if target is not None:
            trust_service.refresh(target)
    record_admin_action(case_type, row.id, action, actor_id, data.get("note"))
    return jsonify({"resolved": True})


@admin_bp.get("/users")
@admin_required
def users():
    query = User.query.order_by(User.created_at.desc())
    result = paginate(query, request.args.get("page", 1, type=int), request.args.get("per_page", 25, type=int))
    rows = result.pop("items")
    return jsonify({"users": [{
        "id": str(u.id),
        "phone_masked": _mask_phone(u.phone) if u.phone else _mask_email(u.email),
        "is_verified": u.is_verified,
        "account_status": u.account_status,
        "role": u.role,
        "created_at": u.created_at.isoformat(),
    } for u in rows], **result})


def _mask_phone(phone: str | None) -> str:
    return f"***{phone[-4:]}" if phone and len(phone) >= 4 else "***"


def _mask_email(email: str | None) -> str:
    if not email or "@" not in email:
        return "***"
    local, _, domain = email.partition("@")
    return f"{local[:2]}***@{domain}" if local else f"***@{domain}"


@admin_bp.post("/users/<user_id>/status")
@admin_required
def set_user_status(user_id):
    actor_id = uuid_module.UUID(get_jwt_identity())
    user = db.session.get(User, uuid_module.UUID(user_id))
    if user is None:
        return error_response("not_found", 404)
    data = request.get_json(silent=True) or {}
    status = data.get("account_status")
    if status not in ("active", "suspended", "banned"):
        return error_response("invalid_status", 422)
    user.account_status = status
    db.session.commit()
    record_admin_action("user", user.id, f"set_status:{status}", actor_id, data.get("note"))
    return jsonify({"ok": True})


@admin_bp.get("/analytics/overview")
@admin_required
def analytics_overview():
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    dau = User.query.filter(User.updated_at >= day_ago).count()
    wau = User.query.filter(User.updated_at >= week_ago).count()
    mau = User.query.filter(User.updated_at >= month_ago).count()
    matches_7d = Match.query.filter(Match.matched_at >= week_ago).count()
    swipes_7d_rows = db.session.execute(
        db.text("SELECT COUNT(*) FROM swipes WHERE created_at >= :since"),
        {"since": week_ago},
    ).scalar() or 0
    match_rate = round(matches_7d / max(swipes_7d_rows / 2.0, 1), 4)
    revenue_npr = db.session.query(db.func.coalesce(db.func.sum(Payment.amount_npr), 0)).filter(
        Payment.status == "completed").scalar()
    pending_verifications = ModerationEvent.query.filter_by(action="pending").count()

    return jsonify({
        "dau": dau, "wau": wau, "mau": mau,
        "matches_7d": matches_7d,
        "match_rate_7d": match_rate,
        "revenue_npr_total": int(revenue_npr),
        "generated_at": now.isoformat(),
    })


@admin_bp.get("/analytics/saathi")
@admin_required
def analytics_saathi():
    """Aggregate-only Saathi health metrics — never individual transcripts."""
    total_sessions = SaathiSession.query.count()
    opted_in = SaathiSession.query.filter_by(proactive_opt_in=True).count()
    paused = SaathiSession.query.filter_by(is_paused=True).count()
    crisis_flagged_sessions = SaathiSession.query.filter_by(crisis_flagged=True).count()
    cap_hit_today = SaathiSession.query.filter(
        SaathiSession.proactive_messages_today >= 1,
        SaathiSession.proactive_cap_date == datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    ).count()
    return jsonify({
        "total_sessions": total_sessions,
        "proactive_opt_in_count": opted_in,
        "paused_count": paused,
        "crisis_flagged_sessions_aggregate": crisis_flagged_sessions,
        "sessions_hitting_daily_cap_today": cap_hit_today,
    })


@admin_bp.get("/verification-queue")
@admin_required
def verification_queue():
    """Liveness checks the automated pass didn't cleanly resolve (doc 6 §2)."""
    from app.models import LivenessCheck, Profile

    pending = LivenessCheck.query.filter(
        (LivenessCheck.passed.is_(None)) | (LivenessCheck.status == "failed")
    ).order_by(LivenessCheck.created_at.desc()).limit(100).all()
    items = []
    for check in pending:
        user = db.session.get(User, check.user_id)
        profile = getattr(user, "profile", None) if user else None
        items.append({
            "id": str(check.id),
            "user_id": str(check.user_id),
            "display_name": profile.display_name if profile else None,
            "status": check.status,
            "passed": check.passed,
            "failure_reason": check.failure_reason,
            "created_at": check.created_at.isoformat(),
        })
    return jsonify({"queue": items})


@admin_bp.post("/verification-queue/<check_id>/resolve")
@admin_required
def resolve_verification(check_id):
    actor_id = uuid_module.UUID(get_jwt_identity())
    from app.models import LivenessCheck

    check = db.session.get(LivenessCheck, case_uuid(check_id))
    if check is None:
        return error_response("not_found", 404)
    data = request.get_json(silent=True) or {}
    decision = data.get("decision")
    if decision not in ("approve", "reject"):
        return error_response("invalid_decision", 422)
    check.status = "complete"
    check.passed = decision == "approve"
    user = db.session.get(User, check.user_id)
    if user is not None:
        user.is_verified = check.passed
    db.session.commit()
    record_admin_action("liveness_check", check.id, f"manual_{decision}", actor_id,
                        data.get("note"))
    return jsonify({"resolved": True})


def case_uuid(value: str):
    try:
        return uuid_module.UUID(value)
    except ValueError:
        return None


@admin_bp.get("/circles")
@admin_required
def admin_circles():
    from app.models import Circle, CircleMembership

    rows = Circle.query.order_by(Circle.is_featured.desc(), Circle.name).all()
    return jsonify({"circles": [{
        "id": str(c.id),
        "name": c.name,
        "category": c.category,
        "description": c.description,
        "is_featured": c.is_featured,
        "member_count": CircleMembership.query.filter_by(circle_id=c.id).count(),
    } for c in rows]})


@admin_bp.post("/circles/<circle_id>/feature")
@admin_required
def feature_circle(circle_id):
    actor_id = uuid_module.UUID(get_jwt_identity())
    from app.models import Circle

    circle = db.session.get(Circle, uuid_module.UUID(circle_id))
    if circle is None:
        return error_response("not_found", 404)
    data = request.get_json(silent=True) or {}
    circle.is_featured = bool(data.get("featured", True))
    db.session.commit()
    record_admin_action("circle", circle.id,
                        "featured" if circle.is_featured else "unfeatured", actor_id)
    return jsonify({"is_featured": circle.is_featured})


@admin_bp.post("/circles/<circle_id>/rooms")
@admin_required
def schedule_room(circle_id):
    import datetime as _dt

    actor_id = uuid_module.UUID(get_jwt_identity())
    from app.models import LiveAudioRoom

    circle = db.session.get(Circle, uuid_module.UUID(circle_id))
    if circle is None:
        return error_response("not_found", 404)
    data = request.get_json(silent=True) or {}
    scheduled_raw = data.get("scheduled_at")
    try:
        scheduled = _dt.datetime.fromisoformat(scheduled_raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return error_response("invalid_scheduled_at", 422)
    room = LiveAudioRoom(circle_id=circle.id, host_id=actor_id,
                         title=data.get("title"), scheduled_at=scheduled)
    db.session.add(room)
    db.session.commit()
    return jsonify({"id": str(room.id)}), 201


@admin_bp.get("/personalization/presets")
@admin_required
def admin_presets():
    from app.models import ChatThemePreset

    rows = ChatThemePreset.query.order_by(ChatThemePreset.sort_order).all()
    return jsonify({"presets": [{
        "id": str(p.id), "key": p.key, "pack": p.pack, "name": p.name,
        "wallpaper_type": p.wallpaper_type, "wallpaper_value": p.wallpaper_value,
        "bubble_color_sent": p.bubble_color_sent,
        "bubble_color_received": p.bubble_color_received,
        "is_active": p.is_active,
    } for p in rows]})


@admin_bp.post("/personalization/presets")
@admin_required
def create_preset():
    actor_id = uuid_module.UUID(get_jwt_identity())
    from app.models import ChatThemePreset

    data = request.get_json(silent=True) or {}
    required = ["key", "pack", "name", "wallpaper_type", "wallpaper_value",
                "bubble_color_sent", "bubble_color_received"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return error_response("missing_fields", 422, fields=missing)
    if ChatThemePreset.query.filter_by(key=data["key"]).first() is not None:
        return error_response("key_exists", 409)
    preset = ChatThemePreset(
        key=data["key"][:64], pack=data["pack"], name=data["name"],
        wallpaper_type=data["wallpaper_type"], wallpaper_value=data["wallpaper_value"],
        bubble_color_sent=data["bubble_color_sent"],
        bubble_color_received=data["bubble_color_received"],
        bubble_shape=data.get("bubble_shape", "rounded"),
        sort_order=int(data.get("sort_order", 0)),
    )
    db.session.add(preset)
    db.session.commit()
    record_admin_action("chat_theme_preset", preset.id, "created", actor_id)
    return jsonify({"id": str(preset.id)}), 201


@admin_bp.delete("/personalization/presets/<preset_id>")
@admin_required
def retire_preset(preset_id):
    """Retire (deactivate) a preset — never hard-delete; existing references stay valid."""
    actor_id = uuid_module.UUID(get_jwt_identity())
    from app.models import ChatThemePreset

    preset = db.session.get(ChatThemePreset, uuid_module.UUID(preset_id))
    if preset is None:
        return error_response("not_found", 404)
    preset.is_active = False
    db.session.commit()
    record_admin_action("chat_theme_preset", preset.id, "retired", actor_id)
    return jsonify({"retired": True})


@admin_bp.put("/saathi-characters/<character_id>/default-theme")
@admin_required
def set_character_default_theme(character_id):
    """Set each Saathi character's signature default theme (doc 6 §2)."""
    actor_id = uuid_module.UUID(get_jwt_identity())
    from app.models import SaathiCharacter

    character = db.session.get(SaathiCharacter, uuid_module.UUID(character_id))
    if character is None:
        return error_response("not_found", 404)
    data = request.get_json(silent=True) or {}
    from app.models import ChatThemePreset

    preset = ChatThemePreset.query.filter_by(key=str(data.get("preset_key"))).first() \
        if data.get("preset_key") else None
    character.default_theme_preset_id = preset.id if preset else None
    db.session.commit()
    record_admin_action("saathi_character", character.id, "set_default_theme", actor_id,
                        data.get("preset_key"))
    return jsonify({"ok": True})


@admin_bp.get("/analytics/history")
@admin_required
def analytics_history():
    """Daily time-series for recharts (doc 6 §2): aggregates computed in SQL."""
    import datetime as _dt

    since = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=30)

    def daily_counts(model, column):
        rows = db.session.execute(
            db.text(
                f"SELECT DATE({column}) AS day, COUNT(*) AS n FROM {model.__tablename__} "
                f"WHERE {column} >= :since GROUP BY DATE({column}) ORDER BY day"
            ),
            {"since": since},
        ).all()
        return {str(r[0]): int(r[1]) for r in rows}

    users_day = daily_counts(User, "created_at")
    matches_day = daily_counts(Match, "matched_at")
    payments_rows = db.session.execute(
        db.text(
            "SELECT DATE(created_at) AS day, SUM(amount_npr) AS total FROM payments "
            "WHERE status = 'completed' AND created_at >= :since "
            "GROUP BY DATE(created_at) ORDER BY day"
        ),
        {"since": since},
    ).all()
    revenue_day = {str(r[0]): int(r[1] or 0) for r in payments_rows}

    series = []
    for offset in range(29, -1, -1):
        day = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=offset)).date().isoformat()
        series.append({
            "date": day,
            "signups": users_day.get(day, 0),
            "matches": matches_day.get(day, 0),
            "revenue_npr": revenue_day.get(day, 0),
        })
    return jsonify({"series": series})


@admin_bp.get("/moderation/cases/<case_type>/<case_id>")
@admin_required
def case_context(case_type, case_id):
    """Full thread context + user history for case detail (doc 6 §2)."""
    cid = case_uuid(case_id)
    if cid is None:
        return error_response("invalid_case_id", 422)

    context: dict = {"case_type": case_type, "case_id": case_id}
    if case_type == "report":
        row = db.session.get(Report, cid)
        if row is None:
            return error_response("not_found", 404)
        target = db.session.get(User, row.target_id)
        context.update({
            "reason": row.reason,
            "details": row.details,
            "status": row.status,
            "target": {
                "id": str(target.id),
                "account_status": target.account_status,
                "is_verified": target.is_verified,
                "reports_against": Report.query.filter_by(target_id=target.id).count(),
            } if target else None,
        })
    elif case_type == "scam_flag":
        from app.models import Message

        row = db.session.get(ScamFlag, cid)
        if row is None:
            return error_response("not_found", 404)
        thread: list[dict] = []
        if row.match_id:
            messages = Message.query.filter_by(match_id=row.match_id).order_by(
                Message.created_at.asc()).limit(50).all()
            thread = [{"sender_id": str(m.sender_id), "body": m.body,
                       "created_at": m.created_at.isoformat()} for m in messages]
        context.update({
            "patterns": row.pattern_matched,
            "confidence": row.confidence,
            "risk_level": row.risk_level,
            "thread_preview": thread[-10:],
        })
    else:
        return error_response("invalid_case_type", 422)
    return jsonify(context)


@admin_bp.get("/users/<user_id>")
@admin_required
def user_detail(user_id):
    uid = case_uuid(user_id)
    if uid is None:
        return error_response("invalid_user_id", 422)
    user = db.session.get(User, uid)
    if user is None:
        return error_response("not_found", 404)
    profile = getattr(user, "profile", None)
    from app.models import FaceEmbedding, Photo

    return jsonify({
        "user": {
            "id": str(user.id),
            "phone_masked": _mask_phone(user.phone) if user.phone else _mask_email(user.email),
            "account_status": user.account_status,
            "role": user.role,
            "is_verified": user.is_verified,
            "intent_mode": user.intent_mode,
            "created_at": user.created_at.isoformat(),
        },
        "profile": {
            "display_name": profile.display_name if profile else None,
            "bio": profile.bio if profile else None,
            "photo_count": Photo.query.filter_by(user_id=user.id).count(),
        },
        "reports_filed": Report.query.filter_by(reporter_id=user.id).count(),
        "reports_against": Report.query.filter_by(target_id=user.id).count(),
        "has_face_embedding": FaceEmbedding.query.filter_by(user_id=user.id).count() > 0,
    })


@admin_bp.get("/audit-log")
@admin_required
def audit_log():
    rows = ModerationEvent.query.order_by(ModerationEvent.created_at.desc()).limit(200).all()
    return jsonify({"events": [{
        "id": str(e.id),
        "subject_type": e.subject_type,
        "subject_id": str(e.subject_id) if e.subject_id else None,
        "source": e.source,
        "action": e.action,
        "categories": e.categories,
        "actor_id": str(e.actor_id) if e.actor_id else None,
        "created_at": e.created_at.isoformat(),
    } for e in rows]})
