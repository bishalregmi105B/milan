import uuid as uuid_module

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db, limiter
from app.models import ChatTheme, ChatThemePreset, DoodleOverlay, Match, SaathiSession, WallpaperUpload
from app.services import media_service
from app.utils.serializers import error_response
from app.utils.validators import ALLOWED_SCOPES, validate_theme_payload

personalization_bp = Blueprint("personalization", __name__)

FACTORY_DEFAULT = {
    "wallpaper_type": "preset",
    "wallpaper_value": "brand_marigold_warm",
    "bubble_color_sent": "#F5A623",
    "bubble_color_received": "#F3DCE2",
    "bubble_shape": "rounded",
    "doodle_overlay_id": None,
    "text_scale": None,
    "dark_mode_brightness": None,
}


def _theme_dto(theme: ChatTheme | None) -> dict:
    if theme is None:
        return {**FACTORY_DEFAULT, "scope": "global", "scope_id": None, "is_factory_default": True}
    return {
        "scope": theme.scope,
        "scope_id": str(theme.scope_id) if theme.scope_id else None,
        "wallpaper_type": theme.wallpaper_type,
        "wallpaper_value": theme.wallpaper_value,
        "bubble_color_sent": theme.bubble_color_sent,
        "bubble_color_received": theme.bubble_color_received,
        "bubble_shape": theme.bubble_shape,
        "doodle_overlay_id": str(theme.doodle_overlay_id) if theme.doodle_overlay_id else None,
        "text_scale": theme.text_scale,
        "dark_mode_brightness": theme.dark_mode_brightness,
        "is_factory_default": False,
    }


def _resolve(user_id, scope: str = "global", scope_id=None) -> dict:
    override = None
    if scope != "global" and scope_id is not None:
        override = ChatTheme.query.filter_by(
            user_id=user_id, scope=scope, scope_id=scope_id).first()
    dto = _theme_dto(override)
    if override is None:
        global_theme = ChatTheme.query.filter_by(user_id=user_id, scope="global").first()
        dto = _theme_dto(global_theme)
        dto["scope"] = scope
        dto["scope_id"] = str(scope_id) if scope_id else None
    return dto


@personalization_bp.get("/theme")
@jwt_required()
def get_global_theme():
    user_id = uuid_module.UUID(get_jwt_identity())
    return jsonify(_resolve(user_id))


@personalization_bp.put("/theme")
@jwt_required()
def put_global_theme():
    user_id = uuid_module.UUID(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    cleaned, errors = validate_theme_payload(data)
    if errors:
        return error_response("invalid_theme", 422, details=errors)

    theme = ChatTheme.query.filter_by(user_id=user_id, scope="global").first()
    if theme is None:
        theme = ChatTheme(user_id=user_id, scope="global")
        db.session.add(theme)
    for field, value in cleaned.items():
        setattr(theme, field, value)
    db.session.commit()
    return jsonify(_theme_dto(theme))


@personalization_bp.delete("/theme")
@jwt_required()
def reset_global_theme():
    user_id = uuid_module.UUID(get_jwt_identity())
    deleted = ChatTheme.query.filter_by(user_id=user_id, scope="global").delete()
    db.session.commit()
    return jsonify({"reset": bool(deleted), **_resolve(user_id)})


def _check_scope_access(user_id, scope: str, scope_id):
    if scope not in ("match", "saathi_session"):
        return False
    sid = uuid_module.UUID(str(scope_id))
    if scope == "match":
        match = db.session.get(Match, sid)
        return match is not None and user_id in (match.user_a_id, match.user_b_id)
    session = db.session.get(SaathiSession, sid)
    return session is not None and session.user_id == user_id


@personalization_bp.get("/theme/<scope>/<scope_id>")
@jwt_required()
def get_scoped_theme(scope, scope_id):
    user_id = uuid_module.UUID(get_jwt_identity())
    if scope not in ALLOWED_SCOPES or scope == "global":
        return error_response("invalid_scope", 422)
    if not _check_scope_access(user_id, scope, scope_id):
        return error_response("not_found", 404)
    return jsonify(_resolve(user_id, scope, uuid_module.UUID(scope_id)))


@personalization_bp.put("/theme/<scope>/<scope_id>")
@jwt_required()
def put_scoped_theme(scope, scope_id):
    user_id = uuid_module.UUID(get_jwt_identity())
    if scope not in ALLOWED_SCOPES or scope == "global":
        return error_response("invalid_scope", 422)
    if not _check_scope_access(user_id, scope, scope_id):
        return error_response("not_found", 404)

    data = request.get_json(silent=True) or {}
    cleaned, errors = validate_theme_payload(data)
    if errors:
        return error_response("invalid_theme", 422, details=errors)

    sid = uuid_module.UUID(scope_id)
    theme = ChatTheme.query.filter_by(user_id=user_id, scope=scope, scope_id=sid).first()
    if theme is None:
        theme = ChatTheme(user_id=user_id, scope=scope, scope_id=sid)
        db.session.add(theme)
    for field, value in cleaned.items():
        setattr(theme, field, value)
    db.session.commit()
    return jsonify(_theme_dto(theme))


@personalization_bp.delete("/theme/<scope>/<scope_id>")
@jwt_required()
def reset_scoped_theme(scope, scope_id):
    """DELETE reverts that scope to the global default (doc 4 §3)."""
    user_id = uuid_module.UUID(get_jwt_identity())
    if scope not in ALLOWED_SCOPES or scope == "global":
        return error_response("invalid_scope", 422)
    deleted = ChatTheme.query.filter_by(
        user_id=user_id, scope=scope, scope_id=uuid_module.UUID(scope_id)).delete()
    db.session.commit()
    return jsonify({"reset": bool(deleted), **_resolve(user_id, scope, uuid_module.UUID(scope_id))})


@personalization_bp.post("/theme/upload")
@jwt_required()
@limiter.limit("10 per hour")
def upload_wallpaper():
    user_id = uuid_module.UUID(get_jwt_identity())
    file = request.files.get("image")
    if file is None:
        return error_response("image_required", 422)
    try:
        result = media_service.upload_media(
            user_id, "wallpaper", file.read(), file.mimetype or "", file.filename or "wallpaper.jpg"
        )
    except ValueError as exc:
        return error_response(str(exc), 422)

    upload = WallpaperUpload(user_id=user_id, media_url=result["url"], moderation_status="pending")
    db.session.add(upload)
    db.session.commit()

    from app.extensions import dispatch
    from app.tasks.moderation_tasks import moderate_wallpaper_upload

    dispatch(moderate_wallpaper_upload, str(upload.id))
    return jsonify({
        "upload_id": str(upload.id),
        "url": result["url"],
        "moderation_status": upload.moderation_status,
        "usable": False,
    }), 201


@personalization_bp.get("/presets")
@jwt_required()
def presets():
    rows = ChatThemePreset.query.filter_by(is_active=True).order_by(ChatThemePreset.sort_order).all()
    doodles = {str(d.id): d.name for d in DoodleOverlay.query.filter_by(is_active=True)}
    return jsonify({"presets": [{
        "id": str(p.id),
        "key": p.key,
        "pack": p.pack,
        "name": p.name,
        "wallpaper_type": p.wallpaper_type,
        "wallpaper_value": p.wallpaper_value,
        "wallpaper_value_dark": p.wallpaper_value_dark,
        "bubble_color_sent": p.bubble_color_sent,
        "bubble_color_received": p.bubble_color_received,
        "bubble_shape": p.bubble_shape,
        "doodle_overlay_id": str(p.doodle_overlay_id) if p.doodle_overlay_id else None,
    } for p in rows], "doodles": doodles})
