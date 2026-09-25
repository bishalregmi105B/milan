import uuid as uuid_module

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db, limiter
from app.models import Block, Report, User
from app.utils.serializers import error_response, parse_uuid
from app.utils.validators import ALLOWED_REPORT_TARGET_TYPES

safety_bp = Blueprint("safety", __name__)


@safety_bp.post("/reports")
@jwt_required()
@limiter.limit("10 per hour")
def file_report():
    reporter_id = uuid_module.UUID(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    reason_raw = data.get("reason")
    reason = reason_raw.strip() if isinstance(reason_raw, str) else ""
    target_id = data.get("target_id")
    target_type = data.get("target_type", "user")
    if not reason:
        return error_response("reason_required", 422)
    if target_type not in ALLOWED_REPORT_TARGET_TYPES:
        return error_response("invalid_target_type", 422)
    target_uuid = parse_uuid(target_id)
    if target_uuid is None:
        return error_response("invalid_target_id", 422)
    target_ref_raw = data.get("target_ref")
    target_ref = parse_uuid(target_ref_raw) if target_ref_raw else None
    if target_ref_raw and target_ref is None:
        return error_response("invalid_target_ref", 422)
    target = db.session.get(User, target_uuid)
    if target is None:
        return error_response("target_not_found", 404)
    existing = Report.query.filter_by(
        reporter_id=reporter_id,
        target_id=target.id,
        status="open",
    ).first()
    if existing is not None:
        return jsonify({"id": str(existing.id), "status": existing.status}), 200
    report = Report(
        reporter_id=reporter_id,
        target_id=target.id,
        target_type=target_type,
        target_ref=target_ref,
        reason=reason[:64],
        details=data.get("details"),
        evidence_urls=data.get("evidence_urls", []),
    )
    db.session.add(report)
    db.session.commit()
    # doc 8 §C2: a fresh open report immediately weighs on the target's score.
    from app.services import trust_service

    trust_service.refresh(target)
    return jsonify({"id": str(report.id), "status": report.status}), 201


@safety_bp.post("/blocks")
@jwt_required()
def block_user():
    blocker_id = uuid_module.UUID(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    blocked_uuid = parse_uuid(data.get("blocked_id"))
    if blocked_uuid is None:
        return error_response("invalid_target_id", 422)
    blocked = db.session.get(User, blocked_uuid)
    if blocked is None:
        return error_response("target_not_found", 404)
    if blocked.id == blocker_id:
        return error_response("cannot_block_self", 422)
    existing = Block.query.filter_by(blocker_id=blocker_id, blocked_id=blocked.id).first()
    if existing is None:
        db.session.add(Block(blocker_id=blocker_id, blocked_id=blocked.id))
        from app.models import Match

        Match.query.filter(
            ((Match.user_a_id == blocker_id) & (Match.user_b_id == blocked.id))
            | ((Match.user_a_id == blocked.id) & (Match.user_b_id == blocker_id)),
        ).update({"is_active": False}, synchronize_session=False)
        db.session.commit()
    return jsonify({"blocked": True})


@safety_bp.get("/blocks")
@jwt_required()
def block_list():
    blocker_id = uuid_module.UUID(get_jwt_identity())
    rows = Block.query.filter_by(blocker_id=blocker_id).all()
    items = []
    for row in rows:
        user = db.session.get(User, row.blocked_id)
        items.append({"id": str(row.blocked_id),
                      "display_name": user.profile.display_name if user and user.profile else None})
    return jsonify({"blocked": items})


@safety_bp.delete("/blocks/<user_id>")
@jwt_required()
def unblock(user_id):
    blocker_id = uuid_module.UUID(get_jwt_identity())
    deleted = Block.query.filter_by(blocker_id=blocker_id, blocked_id=user_id).delete()
    db.session.commit()
    return jsonify({"unblocked": bool(deleted)})
