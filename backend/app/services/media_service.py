import logging
import uuid as uuid_module

from flask import current_app

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_VIDEO_BYTES = 100 * 1024 * 1024


def _object_key(user_id, kind: str, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"{kind}/{user_id}/{uuid_module.uuid4().hex}.{ext}"


def upload_media(user_id, kind: str, data: bytes, content_type: str, filename: str) -> dict:
    """Upload to S3-compatible object storage (DO Spaces) behind the CDN.
    Returns {url, key}. Compression/transcode is triggered async via Celery."""
    if kind in ("photo", "wallpaper") and content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError("unsupported image type")
    if kind == "video" and content_type not in ALLOWED_VIDEO_TYPES:
        raise ValueError("unsupported video type")
    limit = MAX_VIDEO_BYTES if kind == "video" else MAX_IMAGE_BYTES
    if len(data) > limit:
        raise ValueError("file too large")

    endpoint = current_app.config.get("MEDIA_S3_ENDPOINT")
    bucket = current_app.config.get("MEDIA_S3_BUCKET")
    cdn_base = current_app.config.get("MEDIA_CDN_BASE_URL")
    key = _object_key(user_id, kind, filename)

    if endpoint and current_app.config.get("MEDIA_S3_ACCESS_KEY"):
        import boto3

        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=current_app.config["MEDIA_S3_ACCESS_KEY"],
            aws_secret_access_key=current_app.config["MEDIA_S3_SECRET_KEY"],
        )
        client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
    else:
        # MockStorageBackend (dev): real on-disk persistence served by the
        # /media/<key> static route — uploads are inspectable locally.
        import pathlib as _pathlib

        root = _pathlib.Path(current_app.instance_path) / "uploads"
        target = root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        logger.info("stored %d bytes at %s", len(data), target)

    # Always serve via the /media/ nginx alias — without that prefix the URL
    # falls through to the API and 404s (the disk layout is <kind>/<user>/
    # <file> under uploads/, exposed only through the /media/ location).
    url = f"{cdn_base.rstrip('/')}/media/{key}" if cdn_base else f"/media/{key}"
    return {"url": url, "key": key}


def trigger_video_transcode(key: str) -> None:
    from app.extensions import dispatch
    from app.tasks.media_tasks import transcode_video

    dispatch(transcode_video, key)


def trigger_wallpaper_moderation(upload_id) -> None:
    from app.extensions import dispatch
    from app.tasks.moderation_tasks import moderate_wallpaper_upload

    dispatch(moderate_wallpaper_upload, str(upload_id))


def fetch_media_bytes(url: str) -> bytes | None:
    """Read a stored media object by URL — local /media/<key> paths come from
    disk; CDN/object-storage URLs are fetched over HTTPS. Returns None on any
    failure (callers degrade gracefully)."""
    import requests as _requests
    from flask import current_app

    try:
        if url.startswith("/media/"):
            import os
            from pathlib import Path

            uploads = Path(current_app.instance_path) / "uploads"
            path = uploads / url[len("/media/"):]
            return path.read_bytes() if path.exists() else None
        if url.startswith("http"):
            resp = _requests.get(url, timeout=20)
            if resp.status_code == 200:
                return resp.content
        return None
    except Exception:  # noqa: BLE001
        current_app.logger.exception("fetch_media_bytes failed for %s", url[:120])
        return None
