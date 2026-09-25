from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db, limiter
from app.models import Photo
from app.services import media_service
from app.utils.serializers import error_response

media_bp = Blueprint("media", __name__, url_prefix="/media")


@media_bp.post("/upload")
@jwt_required()
@limiter.limit("60 per hour")
def upload():
    import uuid as uuid_module

    user_id = uuid_module.UUID(get_jwt_identity())
    file = request.files.get("file")
    kind = request.args.get("kind", "photo")
    if file is None:
        return error_response("file_required", 422)
    try:
        result = media_service.upload_media(
            user_id, kind, file.read(), file.mimetype or "", file.filename or "upload.bin"
        )
    except ValueError as exc:
        return error_response(str(exc), 422)

    if kind == "video":
        media_service.trigger_video_transcode(result["key"])
    if kind == "photo":
        photo = Photo(user_id=user_id, url=result["url"], order_index=999,
                      moderation_status="pending")
        db.session.add(photo)
        db.session.commit()
        from app.services.moderation_service import moderate_media_asset

        moderate_media_asset(subject_type="photo", subject_id=photo.id, media_url=result["url"])
        result["photo_id"] = str(photo.id)
    return jsonify({**result, "kind": kind}), 201
