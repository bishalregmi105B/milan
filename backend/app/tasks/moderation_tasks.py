import logging
import uuid as uuid_module

from app.extensions import celery_app, db
from app.models import Message, ModerationEvent, WallpaperUpload
from app.services.moderation_service import scan_message_deep

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.moderation_tasks.scan_message_async")
def scan_message_async(message_id: str) -> dict:
    message = db.session.get(Message, uuid_module.UUID(message_id))
    if message is None or not message.body:
        return {"skipped": True}
    result = scan_message_deep(
        message.body,
        message_id=message.id,
        match_id=message.match_id,
        sender_id=message.sender_id,
    )
    return {
        "message_id": message_id,
        "flagged": result["moderation"].get("flagged", False),
        "scam_risk": result["scam"].get("risk"),
    }


@celery_app.task(name="app.tasks.moderation_tasks.moderate_wallpaper_upload")
def moderate_wallpaper_upload(upload_id: str) -> dict:
    """Same moderation pass as profile photos before a wallpaper is usable (doc 4 §9)."""
    upload = db.session.get(WallpaperUpload, uuid_module.UUID(upload_id))
    if upload is None:
        return {"skipped": True}
    from app.services.groq_service import moderate_content

    result = moderate_content(f"[user-uploaded chat wallpaper] {upload.media_url}")
    if result.get("available"):
        upload.moderation_status = "rejected" if result["flagged"] else "approved"
    else:
        upload.moderation_status = "pending"
    db.session.add(ModerationEvent(
        subject_type="wallpaper",
        subject_id=upload.id,
        source="wallpaper_moderation",
        action=upload.moderation_status,
        categories=result.get("categories", []),
    ))
    db.session.commit()
    return {"upload_id": upload_id, "status": upload.moderation_status}


def record_duplicate_flag(user_id: str, duplicate_of_user_id: str, similarity: float) -> None:
    db.session.add(ModerationEvent(
        subject_type="face_embedding",
        subject_id=uuid_module.UUID(user_id),
        source="dedupe_face_embeddings",
        action="duplicate_detected",
        details={"duplicate_of_user_id": duplicate_of_user_id, "similarity": similarity},
    ))
