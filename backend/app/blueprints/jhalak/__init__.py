import uuid as uuid_module
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db, limiter
from app.models import (Circle, CircleMembership, JhalakSnap, JhalakSnapView,
                        LiveAudioRoom, Match, Message, Prompt, Reel, ReelLike,
                        Story, User)
from app.utils.pagination import cursor_paginate, paginate
from app.utils.serializers import error_response, user_brief

jhalak_bp = Blueprint("jhalak", __name__)

SNAP_TTL_HOURS = 24


def _snap_dto(snap: JhalakSnap, viewer_id) -> dict:
    """Feed payload: author identity + view state, NEVER the image URL —
    a snap's media is only revealed by POST /snaps/<id>/view, which burns
    the viewer's one look."""
    from app.utils.serializers import user_brief

    author = db.session.get(User, snap.user_id)
    already = db.session.query(JhalakSnapView.id).filter_by(
        snap_id=snap.id, viewer_id=viewer_id).first() is not None
    mine = snap.user_id == viewer_id
    return {
        "id": str(snap.id),
        "author": user_brief(author) if author else None,
        "caption": snap.caption,
        "filter_key": snap.filter_key,
        "posted_at": snap.posted_at.isoformat() if snap.posted_at else None,
        "expires_at": snap.expires_at.isoformat() if snap.expires_at else None,
        "view_count": snap.view_count or 0,
        "mine": mine,
        # mine => replayable; others => exactly one look
        "viewed": already and not mine,
        "media_url": snap.image_url if (mine or already) else None,
    }


def _friend_ids(user_id) -> set:
    """Accepted, active mutual matches — the circle a snap is shared with
    (§relationship model: Jhalaks are for people you actually matched with,
    not a public wall; the deeper version of 'status sharing')."""
    rows = Match.query.filter(
        Match.is_active.is_(True),
        (Match.user_a_id == user_id) | (Match.user_b_id == user_id),
        Match.kind == "human",
    ).all()
    return {m.user_b_id if m.user_a_id == user_id else m.user_a_id for m in rows}


@jhalak_bp.get("/snaps")
@jwt_required()
def snap_feed():
    """The Jhalak grid: live snaps from YOUR matches (plus your own) with WHO
    posted and whether you still have your one look — tiles only, no media."""
    viewer_id = uuid_module.UUID(get_jwt_identity())
    now = datetime.now(timezone.utc)
    friends = _friend_ids(viewer_id) | {viewer_id}
    snaps = (JhalakSnap.query.filter(JhalakSnap.expires_at > now,
                                     JhalakSnap.user_id.in_(friends))
             .order_by(JhalakSnap.posted_at.desc()).limit(100).all())
    return jsonify({"snaps": [_snap_dto(s, viewer_id) for s in snaps]})


@jhalak_bp.post("/snaps")
@jwt_required()
@limiter.limit("20 per hour")
def create_snap():
    """Post a Jhalak snap: uploaded image URL + optional caption/filter.
    Live for 24h; every other user can view it exactly once."""
    user_id = uuid_module.UUID(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    image_url = data.get("image_url")
    if not image_url:
        return error_response("image_url_required", 422)
    now = datetime.now(timezone.utc)
    snap = JhalakSnap(
        user_id=user_id,
        image_url=image_url[:512],
        caption=(data.get("caption") or "").strip()[:280] or None,
        filter_key=(data.get("filter_key") or "")[:24] or None,
        posted_at=now,
        expires_at=now + timedelta(hours=SNAP_TTL_HOURS),
    )
    db.session.add(snap)
    db.session.commit()

    from app.services.moderation_service import moderate_media_asset

    moderate_media_asset(subject_type="reel", subject_id=snap.id,
                         media_url=image_url)
    return jsonify({"id": str(snap.id), "expires_at": snap.expires_at.isoformat()}), 201


@jhalak_bp.post("/snaps/<snap_id>/view")
@jwt_required()
@limiter.limit("120 per hour")
def view_snap(snap_id):
    """Burn the viewer's single look and return the media URL. Second call
    from the same viewer gets `already_viewed` with no media — the burn row
    is created atomically so two racing requests cannot both win."""
    viewer_id = uuid_module.UUID(get_jwt_identity())
    snap = db.session.get(JhalakSnap, uuid_module.UUID(snap_id))
    if snap is None:
        return error_response("not_found", 404)
    now = datetime.now(timezone.utc)
    if snap.expires_at <= now:
        return error_response("not_found", 404)  # expired == gone

    mine = snap.user_id == viewer_id
    if not mine:
        from sqlalchemy.exc import IntegrityError

        existing = db.session.query(JhalakSnapView.id).filter_by(
            snap_id=snap.id, viewer_id=viewer_id).first()
        if existing is None:
            try:
                db.session.add(JhalakSnapView(
                    snap_id=snap.id, viewer_id=viewer_id, viewed_at=now))
                snap.view_count = (snap.view_count or 0) + 1
                db.session.commit()
            except IntegrityError:
                db.session.rollback()  # concurrent view already burned it

    return jsonify({
        "media_url": snap.image_url,
        "caption": snap.caption,
        "filter_key": snap.filter_key,
        "author": user_brief(db.session.get(User, snap.user_id)),
        "expires_at": snap.expires_at.isoformat(),
        "already_viewed": not mine and existing is not None,
    })


@jhalak_bp.post("/snaps/<snap_id>/react")
@jwt_required()
@limiter.limit("60 per hour")
def react_to_snap(snap_id):
    """Emoji reaction to a friend's snap — delivered as a real chat message
    into the thread you two already share (the reply surface, Instagram-
    instant style). Requires an accepted match: strangers cannot reach you
    through a snap."""
    viewer_id = uuid_module.UUID(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    emoji = (data.get("emoji") or "").strip()
    if not emoji or len(emoji) > 8:
        return error_response("emoji_required", 422)
    snap = db.session.get(JhalakSnap, uuid_module.UUID(snap_id))
    if snap is None:
        return error_response("not_found", 404)
    if snap.user_id == viewer_id:
        return error_response("cannot_react_to_own_snap", 422)
    if snap.user_id not in _friend_ids(viewer_id):
        return error_response("forbidden", 403)

    match = Match.query.filter(
        Match.is_active.is_(True),
        ((Match.user_a_id == viewer_id) & (Match.user_b_id == snap.user_id))
        | ((Match.user_a_id == snap.user_id) & (Match.user_b_id == viewer_id)),
    ).first()
    if match is None:
        return error_response("forbidden", 403)

    author = db.session.get(User, snap.user_id)
    author_name = (author.profile.display_name if author and author.profile else "them")
    message = Message(match_id=match.id, sender_id=viewer_id,
                      body=f"{emoji} — replying to {author_name}'s Jhalak")
    db.session.add(message)
    match.last_activity_at = db.func.now()
    db.session.commit()

    from app.sockets.chat_events import broadcast_message

    broadcast_message(str(match.id), {
        "id": str(message.id),
        "sender_id": str(viewer_id),
        "body": message.body,
        "media_url": None,
        "media_type": None,
        "created_at": message.created_at.isoformat(),
        "is_ai_suggested": False,
    })
    from app.services.notification_service import queue_notification

    queue_notification(
        snap.user_id, "messages",
        "New reply to your Jhalak",
        f"{emoji} — open the chat to reply.",
        data={"type": "message", "match_id": str(match.id)},
    )
    return jsonify({"sent": True, "match_id": str(match.id)})


@jhalak_bp.post("/snaps/<snap_id>/screenshot")
@jwt_required()
def report_screenshot(snap_id):
    """Self-reported screenshot — the author sees who saved their snap
    (mirrors the chat Snap screenshot flow, doc 3 §6)."""
    viewer_id = uuid_module.UUID(get_jwt_identity())
    snap = db.session.get(JhalakSnap, uuid_module.UUID(snap_id))
    if snap is None:
        return error_response("not_found", 404)
    row = db.session.query(JhalakSnapView).filter_by(
        snap_id=snap.id, viewer_id=viewer_id).first()
    if row is None:
        # screenshot before a registered view (screenshot from a push preview)
        row = JhalakSnapView(snap_id=snap.id, viewer_id=viewer_id,
                             viewed_at=datetime.now(timezone.utc),
                             screenshot_detected=True)
        snap.view_count = (snap.view_count or 0) + 1
        db.session.add(row)
    else:
        row.screenshot_detected = True
    db.session.commit()

    from app.services.notification_service import queue_notification

    viewer = db.session.get(User, viewer_id)
    queue_notification(
        snap.user_id, "messages",
        "Screenshot warning 📸",
        f"{viewer.profile.display_name if viewer and viewer.profile else 'Someone'} "
        "took a screenshot of your Jhalak.",
        data={"type": "snap_screenshot", "snap_id": str(snap.id)},
    )
    return jsonify({"recorded": True})


@jhalak_bp.get("/snaps/mine")
@jwt_required()
def my_snaps():
    """Author's own snaps — replayable for them, with per-viewer burn state
    and screenshot flags (the author's control screen)."""
    user_id = uuid_module.UUID(get_jwt_identity())
    now = datetime.now(timezone.utc)
    snaps = (JhalakSnap.query.filter_by(user_id=user_id)
             .filter(JhalakSnap.expires_at > now)
             .order_by(JhalakSnap.posted_at.desc()).all())
    out = []
    for snap in snaps:
        views = (JhalakSnapView.query.filter_by(snap_id=snap.id)
                 .order_by(JhalakSnapView.viewed_at.desc()).all())
        viewers = []
        for v in views:
            viewer = db.session.get(User, v.viewer_id)
            viewers.append({
                "name": viewer.profile.display_name if viewer and viewer.profile else "Someone",
                "viewed_at": v.viewed_at.isoformat(),
                "screenshot": v.screenshot_detected,
            })
        out.append({**_snap_dto(snap, user_id), "viewers": viewers})
    return jsonify({"snaps": out})


@jhalak_bp.delete("/snaps/<snap_id>")
@jwt_required()
def delete_snap(snap_id):
    """Author deletes their own snap — gone for everyone immediately."""
    user_id = uuid_module.UUID(get_jwt_identity())
    snap = db.session.get(JhalakSnap, uuid_module.UUID(snap_id))
    if snap is None or snap.user_id != user_id:
        return error_response("not_found", 404)
    db.session.query(JhalakSnapView).filter_by(snap_id=snap.id).delete()
    db.session.delete(snap)
    db.session.commit()
    return jsonify({"deleted": True})


# ── legacy reel endpoints — kept for account history; the app no longer uses
#    them (Jhalak v2 is snap-based). Stories/circles below are unchanged.

@jhalak_bp.get("/feed")
@jwt_required()
def feed():
    query = Reel.query.filter(Reel.moderation_status == "approved").order_by(Reel.created_at.desc())
    cursor = request.args.get("cursor")
    result = cursor_paginate(query, Reel.created_at, cursor, 10)
    return jsonify({
        "reels": [{
            "id": str(r.id),
            "user_id": str(r.user_id),
            "video_url": r.video_url,
            "thumbnail_url": r.thumbnail_url,
            "caption": r.caption,
            "like_count": r.like_count,
            "is_duet": r.is_duet,
        } for r in result["items"]],
        "next_cursor": result["next_cursor"],
    })


@jhalak_bp.post("/reels")
@jwt_required()
def upload_reel():
    user_id = uuid_module.UUID(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    video_url = data.get("video_url")
    if not video_url:
        return error_response("video_url_required", 422)
    reel = Reel(
        user_id=user_id,
        video_url=video_url,
        caption=(data.get("caption") or "")[:280],
        prompt_id=data.get("prompt_id"),
    )
    db.session.add(reel)
    db.session.commit()

    from app.services.moderation_service import moderate_media_asset

    moderate_media_asset(subject_type="reel", subject_id=reel.id, media_url=video_url)
    return jsonify({"id": str(reel.id)}), 201


@jhalak_bp.post("/reels/<reel_id>/duet")
@jwt_required()
def duet(reel_id):
    user_id = uuid_module.UUID(get_jwt_identity())
    original = db.session.get(Reel, uuid_module.UUID(reel_id))
    if original is None:
        return error_response("reel_not_found", 404)
    data = request.get_json(silent=True) or {}
    video_url = data.get("video_url")
    if not video_url:
        return error_response("video_url_required", 422)
    reel = Reel(user_id=user_id, video_url=video_url, is_duet=True, original_reel_id=original.id)
    db.session.add(reel)
    db.session.commit()
    return jsonify({"id": str(reel.id)}), 201


@jhalak_bp.post("/reels/<reel_id>/like")
@jwt_required()
def like(reel_id):
    user_id = uuid_module.UUID(get_jwt_identity())
    reel = db.session.get(Reel, uuid_module.UUID(reel_id))
    if reel is None:
        return error_response("reel_not_found", 404)
    existing = ReelLike.query.filter_by(reel_id=reel.id, user_id=user_id).first()
    if existing is not None:
        db.session.delete(existing)
        reel.like_count = max(0, reel.like_count - 1)
    else:
        db.session.add(ReelLike(reel_id=reel.id, user_id=user_id))
        reel.like_count += 1
    db.session.commit()
    return jsonify({"like_count": reel.like_count})


@jhalak_bp.get("/stories")
@jwt_required()
def stories():
    from datetime import datetime, timezone

    active = Story.query.filter(Story.expires_at > datetime.now(timezone.utc)).order_by(
        Story.posted_at.desc()).limit(100).all()
    return jsonify({"stories": [{
        "id": str(s.id),
        "user_id": str(s.user_id),
        "media_url": s.media_url,
        "posted_at": s.posted_at.isoformat(),
    } for s in active]})


@jhalak_bp.post("/stories")
@jwt_required()
def post_story():
    user_id = uuid_module.UUID(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    media_url = data.get("media_url")
    if not media_url:
        return error_response("media_url_required", 422)
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    story = Story(user_id=user_id, media_url=media_url, posted_at=now, expires_at=now + timedelta(hours=24))
    db.session.add(story)
    db.session.commit()
    return jsonify({"id": str(story.id)}), 201


@jhalak_bp.get("/circles")
@jwt_required()
def circles():
    rows = Circle.query.order_by(Circle.is_featured.desc(), Circle.name).all()
    return jsonify({"circles": [{
        "id": str(c.id),
        "name": c.name,
        "category": c.category,
        "description": c.description,
        "is_featured": c.is_featured,
        "member_count": CircleMembership.query.filter_by(circle_id=c.id).count(),
    } for c in rows]})


@jhalak_bp.post("/circles/<circle_id>/join")
@jwt_required()
def join_circle(circle_id):
    user_id = uuid_module.UUID(get_jwt_identity())
    circle = db.session.get(Circle, uuid_module.UUID(circle_id))
    if circle is None:
        return error_response("circle_not_found", 404)
    existing = CircleMembership.query.filter_by(circle_id=circle.id, user_id=user_id).first()
    if existing is None:
        db.session.add(CircleMembership(circle_id=circle.id, user_id=user_id))
        db.session.commit()
    return jsonify({"joined": True})


@jhalak_bp.get("/circles/<circle_id>/rooms")
@jwt_required()
def circle_rooms(circle_id):
    rooms = LiveAudioRoom.query.filter_by(circle_id=uuid_module.UUID(circle_id)).order_by(
        LiveAudioRoom.scheduled_at).all()
    return jsonify({"rooms": [{
        "id": str(r.id),
        "title": r.title,
        "scheduled_at": r.scheduled_at.isoformat(),
        "status": r.status,
        "host_id": str(r.host_id),
    } for r in rooms]})
