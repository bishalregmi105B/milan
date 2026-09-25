import uuid as uuid_module

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import DeviceToken, Notification, NotificationPreference, User
from app.utils.serializers import error_response
from app.utils.validators import ALLOWED_NOTIFICATION_CATEGORIES

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.get("/preferences")
@jwt_required()
def get_preferences():
    user_id = uuid_module.UUID(get_jwt_identity())
    prefs = NotificationPreference.query.filter_by(user_id=user_id).all()
    by_category = {p.category: p for p in prefs}
    return jsonify({"preferences": [{
        "category": category,
        "enabled": by_category[category].enabled if category in by_category else True,
        "max_per_day": by_category[category].max_per_day if category in by_category else default_cap(category),
    } for category in ALLOWED_NOTIFICATION_CATEGORIES]})


def default_cap(category: str) -> int:
    from app.services.notification_service import CATEGORY_DEFAULT_CAPS

    return CATEGORY_DEFAULT_CAPS.get(category, 3)


@notifications_bp.put("/preferences")
@jwt_required()
def put_preferences():
    user_id = uuid_module.UUID(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    entries = data.get("preferences", [])
    for entry in entries:
        category = entry.get("category")
        if category not in ALLOWED_NOTIFICATION_CATEGORIES:
            continue
        pref = NotificationPreference.query.filter_by(user_id=user_id, category=category).first()
        if pref is None:
            pref = NotificationPreference(user_id=user_id, category=category)
            db.session.add(pref)
        if "enabled" in entry:
            pref.enabled = bool(entry["enabled"])
        if "max_per_day" in entry:
            pref.max_per_day = max(0, min(int(entry["max_per_day"]), 20))
    db.session.commit()
    return jsonify({"updated": True})


@notifications_bp.post("/devices")
@jwt_required()
def register_device():
    user_id = uuid_module.UUID(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    platform = data.get("platform")
    if not token or platform not in ("android", "ios"):
        return error_response("token_and_platform_required", 422)
    existing = DeviceToken.query.filter_by(token=token).first()
    if existing is None:
        db.session.add(DeviceToken(user_id=user_id, platform=platform, token=token))
        db.session.commit()
    return jsonify({"ok": True})


@notifications_bp.get("/feed")
@jwt_required()
def notification_feed():
    user_id = uuid_module.UUID(get_jwt_identity())
    rows = Notification.query.filter_by(user_id=user_id).order_by(
        Notification.created_at.desc()).limit(100).all()
    return jsonify({"notifications": [{
        "id": str(n.id),
        "category": n.category,
        "title": n.title,
        "body": n.body,
        "sent_at": n.sent_at.isoformat() if n.sent_at else None,
        "opened_at": n.opened_at.isoformat() if n.opened_at else None,
    } for n in rows]})


@notifications_bp.post("/feed/open/<notification_id>")
@jwt_required()
def mark_opened(notification_id):
    from datetime import datetime, timezone

    user_id = uuid_module.UUID(get_jwt_identity())
    row = db.session.get(Notification, uuid_module.UUID(notification_id))
    if row is None or row.user_id != user_id:
        return error_response("not_found", 404)
    row.opened_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"ok": True})
