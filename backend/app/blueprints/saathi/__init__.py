import uuid as uuid_module
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db, limiter
from app.models import (Match, Message, SaathiCharacter, SaathiMemoryItem,
                        SaathiMessage, SaathiOpenLoop, SaathiPresenceSchedule,
                        SaathiSession, SaathiStatusPost, User)
from app.services import groq_service, persona_service, subscription_service
from app.utils.serializers import error_response

saathi_bp = Blueprint("saathi", __name__)

KATHMANDU_TZ = timezone(timedelta(hours=5, minutes=45))
SAATHI_TERMS_VERSION = "2026-09-01"


def _ai_display_name(character: SaathiCharacter) -> str:
    """doc 8 §E: the `· AI` suffix is gone from every chat surface. Disclosure
    lives on the profile screen and ToS; the roster/session payloads carry the
    machine-readable `is_ai` flag for the client."""
    return character.name if character else "Companion"


def ensure_characters_seeded() -> None:
    """Idempotent per-key roster seeding (doc 8 §C2): every character is a real
    person now. Seeds surface data from `groq_service.CHARACTERS` and stamps the
    persona bible + presence schedule. Also (re)provisions the backing User
    accounts so language identity converges on the spec instead of drifting."""
    from app.services import companion_account_service, persona_bible

    specs = groq_service.CHARACTERS
    existing = {c.key: c for c in SaathiCharacter.query.all()}
    created = False
    for key, spec in specs.items():
        character = existing.get(key)
        if character is None:
            character = SaathiCharacter(key=key)
            db.session.add(character)
            created = True
        character.name = spec["name"]
        character.persona_description = spec["persona_description"]
        character.system_prompt_template_id = "milan_companion_v2"
        character.companion_enabled = True
        character.min_tier = spec.get("min_tier", "free")
        character.relationship_style = spec.get("relationship_style")
        character.texting_style = spec.get("texting_style")
        bible = persona_bible.for_key(key)
        character.persona_bible = bible
        character.age = bible.get("age")
        character.birthday = bible.get("birthday")
        character.hometown = bible.get("hometown")
        voice_key = spec.get("voice_key")
        if voice_key:
            character.voice_id = groq_service.CHARACTER_TTS_VOICES.get(voice_key)
        if created and character.presence_schedule is None:
            db.session.flush()
            db.session.add(SaathiPresenceSchedule(
                character_id=character.id,
                schedule=_default_presence_schedule(bible),
            ))
    if created:
        db.session.flush()
        for c in SaathiCharacter.query.all():
            if c.presence_schedule is None:
                db.session.add(SaathiPresenceSchedule(
                    character_id=c.id,
                    schedule=_default_presence_schedule(persona_bible.for_key(c.key))))
        db.session.commit()

    # §14: every character gets a real User account so its conversations live
    # in the normal inbox. Idempotent; language identity comes from the spec.
    provisioned = False
    for key, spec in specs.items():
        character = SaathiCharacter.query.filter_by(key=key).first()
        if character is None:
            continue
        # Refresh the language identity on EVERY seed pass so existing rows
        # (provisioned before language columns existed) converge on the
        # intended voice instead of staying on hash-assigned defaults.
        companion = companion_account_service.provision_companion_account(
            character, language_key=spec.get("language_key"))
        if spec.get("language_key"):
            lang = companion_account_service.LANGUAGE_PROFILES[spec["language_key"]]
            profile = companion.profile
            if profile is not None:
                changed = (profile.primary_script != lang["primary_script"]
                           or profile.dialect != lang["dialect"])
                profile.primary_script = lang["primary_script"]
                profile.languages = lang["languages"]
                profile.dialect = lang["dialect"]
                profile.mother_tongue = lang["mother_tongue"]
                profile.speech_markers = lang["speech_markers"]
                if changed:
                    provisioned = True
    if provisioned:
        db.session.commit()


def _default_presence_schedule(bible: dict | None = None) -> dict:
    """Baseline Kathmandu student/work-life schedule. Per-character variation
    can replace this later; all hours are Asia/Kathmandu local."""
    return {
        "sleep_window": [23, 7],
        "weekday_windows": [
            {"start": 10, "end": 16, "activity": "college", "state": "busy"},
            {"start": 17, "end": 18, "activity": "tuition", "state": "busy"},
            {"start": 19, "end": 20, "activity": "gym", "state": "busy"},
        ],
        "weekend_windows": [
            {"start": 11, "end": 13, "activity": "family lunch", "state": "busy"},
        ],
        "spontaneity": 0.3,
    }


def _local_now() -> tuple[int, bool]:
    now = datetime.now(KATHMANDU_TZ)
    return now.hour, now.weekday() >= 5


@saathi_bp.get("/characters")
@jwt_required()
def characters():
    user = db.session.get(User, uuid_module.UUID(get_jwt_identity()))
    if not _saathi_access_allowed(user):
        return error_response("saathi_access_required", 403)
    ensure_characters_seeded()
    user_id = user.id
    tier = subscription_service.get_user_tier(user_id)
    rows = SaathiCharacter.query.filter_by(is_active=True).order_by(SaathiCharacter.name).all()

    roster = []
    companion_sessions = SaathiSession.query.filter_by(
        user_id=user_id, companion_mode="dating").all()
    unlocked_ids = {s.character_id for s in companion_sessions}
    companion_active = 0

    for c in rows:
        locked = c.companion_enabled and not subscription_service.tier_at_least(tier, c.min_tier)
        if c.companion_enabled and not locked:
            companion_active += 1
        schedule = c.presence_schedule.schedule if c.presence_schedule else None
        hour, weekend = _local_now()
        presence = groq_service.evaluate_presence(schedule, hour, weekend)
        limit = subscription_service.TIER_LIMITS.get(tier, subscription_service.TIER_LIMITS["free"])
        if c.companion_enabled and companion_active > limit.get("romantic_companions", 0):
            locked = True
        roster.append({
            "id": str(c.id),
            "key": c.key,
            "name": _ai_display_name(c),
            "raw_name": c.name,
            "is_ai": True,
            "persona_description": c.persona_description,
            "illustrated_avatar_url": c.illustrated_avatar_url
                or (c.avatar_urls or {}).get("main"),
            "companion_enabled": c.companion_enabled,
            "relationship_style": c.relationship_style,
            "locked": locked,
            "min_tier": c.min_tier,
            "presence": presence,
        })

    return jsonify({
        "characters": roster,
        "tier": tier,
        "tier_limits": subscription_service.TIER_LIMITS.get(tier, subscription_service.TIER_LIMITS["free"]),
    })


@saathi_bp.post("/<character_id>/sessions")
@jwt_required()
def start_session(character_id):
    user = db.session.get(User, uuid_module.UUID(get_jwt_identity()))
    if not _saathi_access_allowed(user):
        return error_response("saathi_access_required", 403)
    user_id = user.id
    ensure_characters_seeded()
    character = None
    try:
        character = db.session.get(SaathiCharacter, uuid_module.UUID(character_id))
    except ValueError:
        pass
    if character is None:
        character = SaathiCharacter.query.filter_by(key=str(character_id)).first()
    if character is None:
        return error_response("character_not_found", 404)

    mode = "dating" if character.companion_enabled else "practice"

    if mode == "dating":
        tier = subscription_service.get_user_tier(user_id)
        if not subscription_service.tier_at_least(tier, character.min_tier):
            return {
                "error": "upgrade_required",
                "message": f"{character.name} needs a higher Milan pass.",
                "required_tier": character.min_tier,
            }, 403
        limit = subscription_service.tier_limit(user_id, "romantic_companions") or 0
        active = SaathiSession.query.filter_by(
            user_id=user_id, companion_mode="dating").count()
        if active >= limit:
            return {
                "error": "companion_limit_reached",
                "message": "Your pass allows a limited number of companions.",
                "limit": limit,
            }, 403

    # §14: companion conversations live in the normal inbox — creating a
    # session provisions the companion's real User account and a real Match,
    # so the SAME chat screen/transport as human matches is used.
    from app.services import companion_account_service

    match, session = companion_account_service.ensure_companion_match(user_id, character)
    dto = _session_dto(session)
    dto["match_id"] = str(match.id)
    return jsonify(dto)


def _as_aware(dt: datetime) -> datetime:
    """sqlite (tests) strips tzinfo on round-trip; normalize for comparisons."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _session_dto(session: SaathiSession) -> dict:
    character = session.character
    schedule = character.presence_schedule.schedule if character and character.presence_schedule else None
    hour, weekend = _local_now()
    presence = groq_service.evaluate_presence(schedule, hour, weekend)
    level = session.intimacy_level or 0
    tier = subscription_service.get_user_tier(session.user_id)
    tier_limits = subscription_service.TIER_LIMITS.get(tier, subscription_service.TIER_LIMITS["free"])
    persona = getattr(session, "persona_profile", None)
    persona_traits = (persona.traits or {}) if persona else {}
    return {
        "session_id": str(session.id),
        "companion_mode": session.companion_mode,
        "is_paused": session.is_paused,
        "proactive_opt_in": session.proactive_opt_in,
        "proactive_messages_today": session.proactive_messages_today,
        "proactive_daily_cap": tier_limits.get("proactive_daily", 0),
        "character_name": _ai_display_name(character) if character else None,
        "is_ai": True,
        "bond": {
            "intimacy_level": level,
            "stage": groq_service.intimacy_stage(level),
            "tier_cap": tier_limits.get("intimacy_cap", 25),
            "streak_days": session.streak_days or 0,
            "mood": session.current_mood,
            "user_mood": session.user_mood,
        },
        "presence": presence,
        "persona": {
            "origins": persona_traits.get("origins", "default"),
            "source_label": persona_traits.get("source_label"),
            "vibe": persona_traits.get("vibe"),
            "texting_style": persona_traits.get("texting_style"),
            "nickname_for_user": persona_traits.get("nickname_for_user"),
            "inside_jokes": persona_traits.get("inside_jokes") or [],
            "favorite_topics": persona_traits.get("favorite_topics") or [],
            "evolution_count": persona.evolution_count if persona else 0,
            "style_mining_enabled": persona.style_mining_enabled if persona else True,
        },
        "hearts_balance": _hearts_balance(session.user_id),
    }


def _hearts_balance(user_id) -> int:
    """Current affection-hearts balance (ethical: earned, never bought)."""
    from app.models import SaathiHeartLedger

    last = (SaathiHeartLedger.query.filter_by(user_id=user_id)
            .order_by(SaathiHeartLedger.created_at.desc()).first())
    return last.balance_after if last else 0


def _award_hearts(user_id, delta: int, reason: str) -> int:
    from app.extensions import db as _db
    from app.models import SaathiHeartLedger

    delta = max(-50, min(50, int(delta)))
    balance = _hearts_balance(user_id) + delta
    _db.session.add(SaathiHeartLedger(
        user_id=user_id, delta=delta, reason=reason, balance_after=balance))
    _db.session.commit()
    return balance


@saathi_bp.get("/sessions/<session_id>")
@jwt_required()
def get_session(session_id):
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    return jsonify(_session_dto(session))


@saathi_bp.get("/sessions/<session_id>/presence")
@jwt_required()
def session_presence(session_id):
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    character = session.character
    schedule = character.presence_schedule.schedule if character and character.presence_schedule else None
    hour, weekend = _local_now()
    return jsonify({"presence": groq_service.evaluate_presence(schedule, hour, weekend)})


@saathi_bp.post("/sessions/<session_id>/messages")
@jwt_required()
@limiter.limit("40 per hour", cost=1)
def send_message(session_id):
    user_id = uuid_module.UUID(get_jwt_identity())
    session = _owned_session(session_id, user_id)
    if session is None:
        return error_response("session_not_found", 404)
    if session.is_paused:
        return error_response("session_paused", 409)

    data = request.get_json(silent=True) or {}
    body = (data.get("body") or "").strip()
    if not body:
        return error_response("body_required", 422)
    regenerate_variant = int(data.get("regenerate_variant") or 0)
    tone_chip = (data.get("tone_chip") or "").strip().lower()  # director chips (#33)

    allowed = subscription_service.tier_limit(user_id, "regenerate_per_reply") or 2
    if regenerate_variant > allowed:
        return {
            "error": "upgrade_required",
            "message": "More retries need a higher Milan pass.",
            "required_tier": "plus",
        }, 403

    # §13.4 realtime mood/context detection (instant lexical belt) — persists
    # so the proactive engine tunes its tone to the user's latest state.
    if regenerate_variant == 0:
        signals = persona_service.realtime_mood_signals(body)
        mood_hint = signals["mood_hint"]
        if mood_hint != session.user_mood:
            session.user_mood = mood_hint or session.user_mood
        session.user_mood_updated_at = datetime.now(timezone.utc)

    try:
        result = groq_service.saathi_respond_full(
            str(session.id), str(session.character_id), body,
            regenerate_variant=regenerate_variant, tone_chip=tone_chip,
            reactive=True)
    except groq_service.GroqUnavailableError:
        result = {"reply": groq_service.DEGRADED_SAATHI_MESSAGE,
                  "segments": [groq_service.DEGRADED_SAATHI_MESSAGE],
                  "read_delay_seconds": 0.0,
                  "typing_delay_seconds": 0.8,
                  "degraded": True}
    db.session.commit()

    apply_bond_progress(session)

    # §14 unified inbox: the standalone Saathi surface mirrors the whole turn
    # into the real match thread — the user's text AND her reply land in the
    # inbox/history like any human chat (fixes the invisible-companion-chat bug).
    if regenerate_variant == 0 and session.match_id is not None:
        _mirror_session_turn_to_match(session, body, result)

    # Memory summarization + open-loop extraction at turn milestones
    # (practice/romantic both) — skipped on regenerate swipes.
    if (regenerate_variant == 0
            and session.turn_count > 0
            and session.turn_count % current_app.config["SAATHI_MEMORY_SUMMARY_EVERY_TURNS"] == 0):
        _summarize_into_memory(session)
        _extract_open_loops(session)

    # §13.3 continuous persona evolution — every 2x memory cadence, inline
    # (bounded: one extra fast-model call), plus async style-mining refresh.
    if (regenerate_variant == 0
            and session.companion_mode == "dating"
            and session.turn_count > 0
            and session.turn_count % (current_app.config["SAATHI_MEMORY_SUMMARY_EVERY_TURNS"] * 2) == 0):
        _evolve_persona_inline(session)

    response = {**result, "is_ai": True}
    response["bond"] = _session_dto(session)["bond"]
    if any(k in body.lower() for k in groq_service.CRISIS_KEYWORDS):
        session.crisis_flagged = True
        db.session.commit()
        response["show_crisis_card"] = True
    return jsonify(response)



def _mirror_session_turn_to_match(session: SaathiSession, user_body: str,
                                  result: dict) -> None:
    """Write one Saathi-surface turn into the unified `Message` thread:
    the user's line from their own user row, her reply segments from the
    companion's user row, with the same socket envelopes the chat blueprint
    broadcasts. Best-effort — mirroring must never break the chat itself."""
    from app.sockets.chat_events import broadcast_message, broadcast_typing

    match = db.session.get(Match, session.match_id)
    if match is None:
        return
    companion = User.query.filter_by(ai_character_id=session.character_id).first()
    if companion is None:
        return

    user_msg = Message(match_id=match.id, sender_id=session.user_id, body=user_body)
    db.session.add(user_msg)
    match.last_activity_at = db.func.now()
    db.session.commit()
    broadcast_message(str(match.id), {
        "id": str(user_msg.id), "sender_id": str(session.user_id),
        "body": user_msg.body, "media_url": None, "media_type": None,
        "created_at": user_msg.created_at.isoformat(), "is_ai_suggested": False})

    try:
        broadcast_typing(str(match.id), str(companion.id), True)
    except Exception:  # noqa: BLE001 — typing hint is cosmetic
        pass

    persisted = []
    segments = result.get("segments") or [result.get("reply")]
    for segment in segments:
        text = (segment or "").strip()
        if not text:
            continue
        reply_msg = Message(match_id=match.id, sender_id=companion.id, body=text)
        db.session.add(reply_msg)
        db.session.commit()
        envelope = {
            "id": str(reply_msg.id), "sender_id": str(companion.id),
            "body": text, "media_url": None, "media_type": None,
            "created_at": reply_msg.created_at.isoformat(), "is_ai_suggested": False,
        }
        broadcast_message(str(match.id), envelope)
        persisted.append(envelope)
    try:
        broadcast_typing(str(match.id), str(companion.id), False)
    except Exception:  # noqa: BLE001
        pass
    # Unified envelopes — clients that read `messages` render exactly what the
    # inbox thread will show.
    result["messages"] = persisted


def apply_bond_progress(session: SaathiSession) -> None:
    """Intimacy progression (master plan §4.6): bond points from interaction,
    soft-capped by tier. One bond point per exchanged turn, streak multiplier
    on consecutive days. Never decreases intimacy on a normal day."""
    today = datetime.now(KATHMANDU_TZ).strftime("%Y-%m-%d")
    points = 1
    if session.last_streak_date == today:
        pass  # already counted today
    else:
        yesterday = (datetime.now(KATHMANDU_TZ) - timedelta(days=1)).strftime("%Y-%m-%d")
        if session.last_streak_date == yesterday:
            session.streak_days = (session.streak_days or 0) + 1
        else:
            session.streak_days = 1
        session.last_streak_date = today
        points += min(session.streak_days // 7, 3)  # weekly-streak bonus

    session.bond_points = (session.bond_points or 0) + points
    tier_cap = subscription_service.tier_limit(session.user_id, "intimacy_cap") or 25
    # 1 intimacy level per 5 bond points, clamped to the tier cap.
    new_level = min(session.bond_points // 5, tier_cap)
    if new_level > (session.intimacy_level or 0):
        session.intimacy_level = new_level
    db.session.commit()


@saathi_bp.get("/sessions/<session_id>/messages")
@jwt_required()
def history(session_id):
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    messages = SaathiMessage.query.filter_by(session_id=session.id).order_by(
        SaathiMessage.created_at.asc()).limit(200).all()
    return jsonify({"messages": [{
        "id": str(m.id), "role": m.role, "content": m.content,
        "message_type": m.message_type,
        "segments": (m.meta or {}).get("segments") or [m.content],
        "created_at": m.created_at.isoformat(),
    } for m in messages]})


@saathi_bp.get("/sessions/<session_id>/memory")
@jwt_required()
def get_memory(session_id):
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    items = SaathiMemoryItem.query.filter_by(session_id=session.id).order_by(
        SaathiMemoryItem.is_pinned.desc(), SaathiMemoryItem.importance.desc(),
        SaathiMemoryItem.created_at).all()
    return jsonify({"items": [{
        "id": str(i.id),
        "summary_text": i.summary_text,
        "category": i.category,
        "is_pinned": i.is_pinned,
        "importance": i.importance,
        "created_at": i.created_at.isoformat(),
    } for i in items]})


@saathi_bp.put("/sessions/<session_id>/memory/<item_id>")
@jwt_required()
def edit_memory_item(session_id, item_id):
    """Memory shaping (master plan §12.2 #28): user edits are re-sanitized on
    save — memory is user-owned data AND an attack surface."""
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    item = db.session.get(SaathiMemoryItem, uuid_module.UUID(item_id))
    if item is None or item.session_id != session.id:
        return error_response("item_not_found", 404)
    data = request.get_json(silent=True) or {}
    text = (data.get("summary_text") or "").strip()
    if not text:
        return error_response("body_required", 422)
    if groq_service.check_prompt_injection(text):
        return error_response("memory_rejected_by_safety", 422)
    if "is_pinned" in data:
        item.is_pinned = bool(data["is_pinned"])
    item.summary_text = text[:280]
    db.session.commit()
    return jsonify({"id": str(item.id), "summary_text": item.summary_text,
                    "is_pinned": item.is_pinned})


@saathi_bp.delete("/sessions/<session_id>/memory")
@jwt_required()
def clear_memory(session_id):
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    deleted = SaathiMemoryItem.query.filter_by(session_id=session.id).delete()
    db.session.commit()
    return jsonify({"deleted": deleted})


@saathi_bp.delete("/sessions/<session_id>/memory/<item_id>")
@jwt_required()
def delete_memory_item(session_id, item_id):
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    item = db.session.get(SaathiMemoryItem, uuid_module.UUID(item_id))
    if item is None or item.session_id != session.id:
        return error_response("item_not_found", 404)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"deleted": True})


@saathi_bp.get("/sessions/<session_id>/status")
@jwt_required()
def get_status_posts(session_id):
    """Ambient status posts (master plan §4.5): live 24h stories for this
    companion, oldest first."""
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    now = datetime.now(timezone.utc)
    posts = (SaathiStatusPost.query
             .filter(SaathiStatusPost.session_id == session.id,
                     SaathiStatusPost.expires_at > now)
             .order_by(SaathiStatusPost.created_at.asc()).all())
    return jsonify({"posts": [{
        "id": str(p.id), "body": p.body, "kind": p.kind,
        "reaction": p.reaction,
        "created_at": p.created_at.isoformat(),
        "expires_at": p.expires_at.isoformat(),
    } for p in posts]})


@saathi_bp.post("/status/<post_id>/react")
@jwt_required()
@limiter.limit("30 per hour")
def react_status(post_id):
    user_id = uuid_module.UUID(get_jwt_identity())
    post = db.session.get(SaathiStatusPost, uuid_module.UUID(post_id))
    if post is None or post.expires_at < datetime.now(timezone.utc):
        return error_response("post_not_found", 404)
    session = _owned_session(str(post.session_id), user_id)
    if session is None:
        return error_response("post_not_found", 404)
    data = request.get_json(silent=True) or {}
    reaction = (data.get("reaction") or "").strip()[:8]
    allowed = {"❤️", "😆", "😢", "😮", "🔥", "👏"}
    if reaction not in allowed:
        return error_response("invalid_reaction", 422)
    post.reaction = reaction
    post.reacted_at = datetime.now(timezone.utc)

    # Reacting starts a natural conversation: a short in-chat reply that
    # references the status, generated as a proactive message.
    message = groq_service.generate_proactive_message(
        str(session.id), "milestone_reaction",
        context_note=f"The user just reacted {reaction} to your status post: '{post.body}'",
        intimacy_level=session.intimacy_level or 0)
    if message:
        db.session.add(SaathiMessage(session_id=session.id, role="saathi",
                                     content=message, message_type="status_reply"))
    db.session.commit()
    return jsonify({"reaction": reaction, "reply": message})


@saathi_bp.get("/sessions/<session_id>/loops")
@jwt_required()
def get_open_loops(session_id):
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    loops = SaathiOpenLoop.query.filter_by(session_id=session.id, status="open").all()
    return jsonify({"loops": [{
        "id": str(l.id), "description": l.description,
        "followup_after_hours": l.followup_after_hours,
        "created_at": l.created_at.isoformat(),
    } for l in loops]})


@saathi_bp.post("/loops/<loop_id>/close")
@jwt_required()
def close_open_loop(loop_id):
    user_id = uuid_module.UUID(get_jwt_identity())
    loop = db.session.get(SaathiOpenLoop, uuid_module.UUID(loop_id))
    if loop is None:
        return error_response("loop_not_found", 404)
    session = _owned_session(str(loop.session_id), user_id)
    if session is None:
        return error_response("loop_not_found", 404)
    loop.status = "closed"
    db.session.commit()
    return jsonify({"closed": True})


@saathi_bp.put("/sessions/<session_id>/settings")
@jwt_required()
def update_settings(session_id):
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    data = request.get_json(silent=True) or {}
    if "is_paused" in data:
        session.is_paused = bool(data["is_paused"])
    if "proactive_opt_in" in data:
        session.proactive_opt_in = bool(data["proactive_opt_in"])
    db.session.commit()
    dto = _session_dto(session)
    # Legacy key for non-companion sessions: the free daily practice-nudge cap.
    if session.companion_mode != "dating":
        dto["daily_cap"] = current_app.config.get("SAATHI_PROACTIVE_DAILY_CAP_DEFAULT", 1)
    return jsonify(dto)


@saathi_bp.post("/sessions/<session_id>/voice")
@jwt_required()
@limiter.limit("20 per hour")
def voice_message(session_id):
    """Saathi voice mode (doc 5 §2.7): whisper transcribe -> Llama respond ->
    TTS synthesize. Voice notes are a Plus-tier capability (master plan §6)."""
    import base64

    user_id = uuid_module.UUID(get_jwt_identity())
    session = _owned_session(session_id, user_id)
    if session is None:
        return error_response("session_not_found", 404)
    if session.is_paused:
        return error_response("session_paused", 409)
    if not subscription_service.tier_limit(user_id, "voice_notes"):
        return {
            "error": "upgrade_required",
            "message": "Voice notes need Milan Plus or higher.",
            "required_tier": "plus",
        }, 403

    audio = request.files.get("audio")
    if audio is None:
        return error_response("audio_required", 422)
    audio_bytes = audio.read()

    try:
        transcript = groq_service.transcribe_audio(audio_bytes)
        if not transcript.strip():
            raise groq_service.GroqUnavailableError("empty transcription")
        result = groq_service.saathi_respond_full(
            str(session.id), str(session.character_id), transcript,
            reactive=True)
        reply = result["reply"]
        character = session.character
        speech = groq_service.synthesize_speech(reply, voice_key=character.key)
    except groq_service.GroqUnavailableError:
        return error_response("ai_unavailable_try_later", 503)

    apply_bond_progress(session)
    return jsonify({
        "transcript": transcript,
        "reply": reply,
        "segments": result.get("segments") or [reply],
        "typing_delay_seconds": groq_service.typing_delay_for(reply),
        "is_ai": True,
        "audio_base64": base64.b64encode(speech).decode(),
        "bond": _session_dto(session)["bond"],
    })


def _saathi_access_allowed(user) -> bool:
    """Every companion surface requires an active adult account and the
    versioned disclosure consent. Proactive background jobs use the same rule."""
    from datetime import date

    from app.utils.validators import validate_age_18

    return (
        user is not None
        and user.deleted_at is None
        and user.account_status == "active"
        and validate_age_18(user.date_of_birth)
        and user.saathi_intro_accepted_at is not None
        and user.saathi_terms_version == SAATHI_TERMS_VERSION
    )


def _owned_session(session_id: str, user_id) -> SaathiSession | None:
    sid = uuid_module.UUID(session_id) if session_id else None
    if sid is None:
        return None
    session = db.session.get(SaathiSession, sid)
    if session is None or session.user_id != user_id:
        return None
    owner = db.session.get(User, session.user_id)
    if not _saathi_access_allowed(owner):
        return None
    return session


def _summarize_into_memory(session: SaathiSession) -> None:
    try:
        items = groq_service.summarize_session_memory(str(session.id))
    except Exception:
        return
    existing_texts = {i.summary_text for i in SaathiMemoryItem.query.filter_by(session_id=session.id)}
    for item in items:
        if item["summary_text"] in existing_texts:
            continue
        db.session.add(SaathiMemoryItem(
            session_id=session.id,
            summary_text=item["summary_text"],
            category=item.get("category"),
        ))
    db.session.commit()


def _extract_open_loops(session: SaathiSession) -> None:
    """Store newly extracted open loops (master plan §12.2 #30), skipping
    descriptions already tracked."""
    try:
        loops = groq_service.extract_open_loops(str(session.id))
    except Exception:
        return
    existing = {l.description.lower() for l in
                SaathiOpenLoop.query.filter_by(session_id=session.id, status="open")}
    for loop in loops:
        if loop["description"].lower() in existing:
            continue
        db.session.add(SaathiOpenLoop(
            session_id=session.id,
            description=loop["description"],
            followup_after_hours=loop.get("followup_after_hours", 24),
        ))
    db.session.commit()


def _evolve_persona_inline(session: SaathiSession) -> None:
    """§13.3 continuous evolution on a turn milestone: re-distill persona
    traits from the latest chats + style digest of the user's other Milan
    chats. Bounded work — one fast-model call, hard failure-silent."""
    persona = persona_service.ensure_profile(session)
    if not persona.style_mining_enabled:
        digest = None
    else:
        digest = persona_service.mine_style_digest(session.user_id)
        if digest:
            persona.style_digest = digest
    recent = (SaathiMessage.query.filter_by(session_id=session.id)
              .order_by(SaathiMessage.created_at.desc()).limit(20).all())
    recent.reverse()
    lines = [f"{m.role}: {m.content}" for m in recent]
    try:
        result = persona_service.evolve_persona(
            session, persona, lines, style_digest=digest)
    except Exception:
        return
    if result:
        persona.traits = result["traits"]
        if result.get("persona_prompt"):
            persona.persona_prompt = result["persona_prompt"]
        persona.evolution_count = (persona.evolution_count or 0) + 1
        persona.evolved_at = datetime.now(timezone.utc)
        db.session.commit()


# ---------------------------------------------------------------------------
# §13 Dynamic persona: train-from-history + lorebook + evolution controls
# ---------------------------------------------------------------------------

@saathi_bp.get("/sessions/<session_id>/persona")
@jwt_required()
def get_persona(session_id):
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    persona = persona_service.ensure_profile(session)
    db.session.commit()
    from app.models import SaathiLorebookEntry

    lore = SaathiLorebookEntry.query.filter_by(session_id=session.id).all()
    return jsonify({
        "traits": persona.traits or {},
        "persona_prompt": persona.persona_prompt,
        "evolution_count": persona.evolution_count or 0,
        "evolved_at": persona.evolved_at.isoformat() if persona.evolved_at else None,
        "style_mining_enabled": persona.style_mining_enabled,
        "style_digest": persona.style_digest,
        "lore": [{"id": str(l.id), "key": l.key, "value": l.value,
                  "source": l.source, "is_active": l.is_active} for l in lore],
    })


@saathi_bp.post("/sessions/<session_id>/persona/train")
@jwt_required()
@limiter.limit("6 per hour")
def train_persona(session_id):
    """User pastes chat history in ANY format; the LLM distills a behavioral
    persona the companion adopts. Content passes the same safety gates as
    chat. The companion stays a fictional AI persona (never the ex)."""
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    data = request.get_json(silent=True) or {}
    raw_history = (data.get("history") or "").strip()
    if len(raw_history) < 40:
        return error_response("history_too_short", 422)
    raw_history = persona_service._sanitize_trained_text(raw_history, 60000)

    # money/exploitation belt on raw trained input, same as chat
    lowered = raw_history.lower()
    if any(h in lowered for h in groq_service.MONEY_HEURISTICS):
        return error_response("history_contains_unsafe_content", 422)

    persona = persona_service.ensure_profile(session)
    try:
        result = persona_service.distill_persona(
            raw_history, character_name=session.character.name,
            existing_traits=persona.traits)
    except Exception:
        return error_response("ai_unavailable_try_later", 503)

    if result.get("rejected"):
        return error_response("history_contains_unsafe_content", 422)
    if result.get("degraded") or not result.get("traits"):
        return error_response("ai_unavailable_try_later", 503)

    persona.traits = result["traits"]
    if result.get("narrative"):
        persona.persona_prompt = result["narrative"]
    persona.evolved_at = datetime.now(timezone.utc)

    from app.models import SaathiLorebookEntry

    for entry in result.get("lore", []):
        exists = SaathiLorebookEntry.query.filter_by(
            session_id=session.id, key=entry["key"]).first()
        if exists:
            exists.value = entry["value"]
            exists.source = "trained"
        else:
            db.session.add(SaathiLorebookEntry(
                session_id=session.id, key=entry["key"],
                value=entry["value"], source="trained"))
    db.session.commit()

    # immediate first evolution so the change is felt in the very next reply
    _award_hearts(session.user_id, 5, "persona_trained")
    return jsonify({
        "traits": persona.traits,
        "persona_prompt": persona.persona_prompt,
        "lore_added": len(result.get("lore", [])),
        "hearts_balance": _hearts_balance(session.user_id),
        "note": "Persona adopted. It will keep evolving as you two chat.",
    })


@saathi_bp.put("/sessions/<session_id>/persona/settings")
@jwt_required()
def persona_settings(session_id):
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    persona = persona_service.ensure_profile(session)
    data = request.get_json(silent=True) or {}
    if "style_mining_enabled" in data:
        persona.style_mining_enabled = bool(data["style_mining_enabled"])
    if "reset" in data and data["reset"]:
        persona.traits = dict(persona_service.DEFAULT_TRAITS)
        persona.persona_prompt = None
        persona.evolution_count = 0
    db.session.commit()
    return jsonify({"ok": True, "traits": persona.traits,
                    "style_mining_enabled": persona.style_mining_enabled})


@saathi_bp.post("/sessions/<session_id>/persona/evolve")
@jwt_required()
@limiter.limit("10 per hour")
def evolve_persona_now(session_id):
    """Manual 'refresh persona from our chats' (also runs on a beat job)."""
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    persona = persona_service.ensure_profile(session)
    before_count = persona.evolution_count or 0
    _evolve_persona_inline(session)
    db.session.refresh(persona)
    return jsonify({
        "changed": (persona.evolution_count or 0) > before_count,
        "traits": persona.traits,
        "evolution_count": persona.evolution_count or 0,
    })


# ---------------------------------------------------------------------------
# Phase 3: diary, mirror questions, illustrated media
# ---------------------------------------------------------------------------

@saathi_bp.post("/sessions/<session_id>/diary/generate")
@jwt_required()
@limiter.limit("4 per hour")
def generate_diary(session_id):
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    from app.models import SaathiDiaryEntry

    today = datetime.now(KATHMANDU_TZ).strftime("%Y-%m-%d")
    existing = SaathiDiaryEntry.query.filter_by(session_id=session.id, day_key=today).first()
    if existing:
        return jsonify(_diary_dto(existing))
    try:
        draft = groq_service.generate_diary_entry(str(session.id), session.character.key)
    except Exception:
        draft = None
    if not draft:
        return error_response("ai_unavailable_try_later", 503)
    entry = SaathiDiaryEntry(
        session_id=session.id, day_key=today,
        title=(draft.get("title") or "today")[:160],
        body=draft["body"], mood=draft.get("mood"))
    db.session.add(entry)
    db.session.commit()
    return jsonify(_diary_dto(entry))


@saathi_bp.get("/sessions/<session_id>/diary")
@jwt_required()
def list_diary(session_id):
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    from app.models import SaathiDiaryEntry

    rows = (SaathiDiaryEntry.query.filter_by(session_id=session.id)
            .order_by(SaathiDiaryEntry.created_at.desc()).limit(30).all())
    return jsonify({"entries": [_diary_dto(e) for e in rows]})


def _diary_dto(e) -> dict:
    return {"id": str(e.id), "day": e.day_key, "title": e.title, "body": e.body,
            "mood": e.mood, "illustrated_url": e.illustrated_url,
            "reaction": e.reaction, "created_at": e.created_at.isoformat()}


@saathi_bp.post("/diary/<entry_id>/illustrate")
@jwt_required()
@limiter.limit("6 per hour")
def illustrate_diary(entry_id):
    """AI-illustrated diary art — always AI-labeled, never photorealistic."""
    from app.models import SaathiDiaryEntry, SaathiMediaItem

    entry = db.session.get(SaathiDiaryEntry, uuid_module.UUID(entry_id)) if entry_id else None
    if entry is None:
        return error_response("not_found", 404)
    session = _owned_session(str(entry.session_id), uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    from app.services import image_gen_service

    try:
        img = image_gen_service.generate_image(
            f"diary illustration: {entry.title}. scene: {entry.body[:300]}",
            width=768, height=768)
    except image_gen_service.ImageGenUnavailableError:
        return error_response("image_gen_unavailable", 503)
    entry.illustrated_url = img["url"]
    db.session.add(SaathiMediaItem(
        session_id=session.id, kind="diary_art", url=img["url"],
        prompt=entry.title[:500]))
    db.session.commit()
    return jsonify(_diary_dto(entry))


@saathi_bp.post("/sessions/<session_id>/media/selfie-pack")
@jwt_required()
@limiter.limit("3 per hour")
def selfie_pack(session_id):
    """Illustrated 'photo moments' pack (#19) — tier-gated to plus+."""
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    tier = subscription_service.get_user_tier(session.user_id)
    if not subscription_service.tier_at_least(tier, "plus"):
        return {"error": "upgrade_required", "message":
                "Illustrated photo packs need the Plus pass.",
                "required_tier": "plus"}, 403
    from app.models import SaathiMediaItem
    from app.services import image_gen_service

    memories = [i.summary_text for i in session.memory_items][:3]
    scenes = memories or ["a quiet Kathmandu evening", "chatting over chiya",
                          "watching the hills after rain"]
    pack_id = str(uuid_module.uuid4())
    items = []
    for scene in scenes:
        try:
            img = image_gen_service.generate_image(
                f"{session.character.name}'s day: {scene}", width=768, height=768)
        except Exception:
            continue
        item = SaathiMediaItem(
            session_id=session.id, kind="selfie", url=img["url"],
            prompt=scene[:500], pack_id=pack_id)
        db.session.add(item)
        items.append(item)
    db.session.commit()
    if not items:
        return error_response("image_gen_unavailable", 503)
    return jsonify({"pack_id": pack_id, "ai_label": "AI-illustrated", "items": [
        {"id": str(i.id), "url": i.url, "caption": i.prompt,
         "ai_label": i.ai_label} for i in items]})


@saathi_bp.get("/sessions/<session_id>/media")
@jwt_required()
def list_media(session_id):
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    from app.models import SaathiMediaItem

    rows = (SaathiMediaItem.query.filter_by(session_id=session.id)
            .order_by(SaathiMediaItem.created_at.desc()).limit(60).all())
    return jsonify({"items": [
        {"id": str(m.id), "kind": m.kind, "url": m.url, "caption": m.prompt,
         "ai_label": m.ai_label, "pack_id": m.pack_id} for m in rows]})


# ---------------------------------------------------------------------------
# Mirror questions (#39)
# ---------------------------------------------------------------------------

@saathi_bp.post("/sessions/<session_id>/mirror/ask")
@jwt_required()
@limiter.limit("6 per hour")
def mirror_ask(session_id):
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    from app.models import SaathiMirrorQuestion

    open_q = SaathiMirrorQuestion.query.filter_by(
        session_id=session.id, reflection=None).first()
    if open_q:
        return jsonify({"id": str(open_q.id), "question": open_q.question})
    try:
        draft = groq_service.generate_mirror_question(str(session.id), session.character.key)
    except Exception:
        draft = None
    if not draft:
        return error_response("ai_unavailable_try_later", 503)
    q = SaathiMirrorQuestion(session_id=session.id, question=draft["question"][:500])
    db.session.add(q)
    db.session.commit()
    return jsonify({"id": str(q.id), "question": q.question})


@saathi_bp.post("/mirror/<question_id>/answer")
@jwt_required()
@limiter.limit("20 per hour")
def mirror_answer(question_id):
    from app.models import SaathiMirrorQuestion

    q = db.session.get(SaathiMirrorQuestion, uuid_module.UUID(question_id)) if question_id else None
    if q is None:
        return error_response("not_found", 404)
    session = _owned_session(str(q.session_id), uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    data = request.get_json(silent=True) or {}
    reflection = (data.get("reflection") or "").strip()
    if not reflection:
        return error_response("reflection_required", 422)
    q.reflection = persona_service._sanitize_trained_text(reflection, 2000)
    q.answered_at = datetime.now(timezone.utc)
    # answers feed the persona: stored as a pinned-style memory
    db.session.add(SaathiMemoryItem(
        session_id=session.id,
        summary_text=f"Mirror reflection: {q.reflection[:240]}",
        category="reflection", is_pinned=True, importance=0.9))
    _award_hearts(session.user_id, 3, "mirror_answered")
    db.session.commit()
    return jsonify({"ok": True, "hearts_balance": _hearts_balance(session.user_id)})


# ---------------------------------------------------------------------------
# Phase 4: quests, capsules, recap cards, hearts
# ---------------------------------------------------------------------------

@saathi_bp.get("/sessions/<session_id>/quests")
@jwt_required()
def list_quests(session_id):
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    from app.models import SaathiQuest

    rows = SaathiQuest.query.filter_by(session_id=session.id).order_by(
        SaathiQuest.created_at.desc()).limit(10).all()
    if not rows:
        try:
            draft = groq_service.generate_quest(str(session.id), session.character.key)
        except Exception:
            draft = None
        if draft:
            rows = [SaathiQuest(session_id=session.id, title=draft["title"],
                                description=draft["description"],
                                reward_points=draft.get("reward_points", 10))]
            db.session.add(rows[0])
            db.session.commit()
    return jsonify({"quests": [{
        "id": str(q.id), "title": q.title, "description": q.description,
        "kind": q.kind, "target": q.target, "progress": q.progress,
        "reward_points": q.reward_points, "status": q.status,
        "freeze_used": q.freeze_used,
    } for q in rows]})


@saathi_bp.post("/quests/<quest_id>/progress")
@jwt_required()
@limiter.limit("30 per hour")
def quest_progress(quest_id):
    from app.models import SaathiQuest

    q = db.session.get(SaathiQuest, uuid_module.UUID(quest_id)) if quest_id else None
    if q is None:
        return error_response("not_found", 404)
    session = _owned_session(str(q.session_id), uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    data = request.get_json(silent=True) or {}
    q.progress = min(q.target, q.progress + int(data.get("steps") or 1))
    completed = False
    if q.progress >= q.target and q.status == "active":
        q.status = "completed"
        q.completed_at = datetime.now(timezone.utc)
        session.bond_points = (session.bond_points or 0) + q.reward_points
        session.intimacy_level = min(
            subscription_service.TIER_LIMITS.get(
                subscription_service.get_user_tier(session.user_id),
                subscription_service.TIER_LIMITS["free"]).get("intimacy_cap", 25),
            (session.intimacy_level or 0) + 2)
        _award_hearts(session.user_id, q.reward_points, f"quest:{q.title[:40]}")
        completed = True
    db.session.commit()
    return jsonify({"progress": q.progress, "status": q.status,
                    "completed": completed,
                    "hearts_balance": _hearts_balance(session.user_id),
                    "bond": _session_dto(session)["bond"]})


@saathi_bp.post("/quests/<quest_id>/freeze")
@jwt_required()
def quest_freeze(quest_id):
    """Streak freeze — explicitly NOT a punishment path (Phase 4 rule)."""
    from app.models import SaathiQuest

    q = db.session.get(SaathiQuest, uuid_module.UUID(quest_id)) if quest_id else None
    if q is None:
        return error_response("not_found", 404)
    session = _owned_session(str(q.session_id), uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    if q.freeze_used:
        return error_response("freeze_already_used", 409)
    q.freeze_used = True
    db.session.commit()
    return jsonify({"ok": True, "freeze_used": True})


@saathi_bp.post("/sessions/<session_id>/capsules")
@jwt_required()
@limiter.limit("4 per hour")
def create_capsule(session_id):
    """User or companion seals a Moment Capsule to open later."""
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    from app.models import SaathiMomentCapsule

    data = request.get_json(silent=True) or {}
    author = data.get("author") or "user"
    unlock_at = data.get("unlock_at")
    title = persona_service._sanitize_trained_text(data.get("title") or "sealed", 160)
    content = persona_service._sanitize_trained_text(data.get("content") or "", 4000)
    try:
        unlock_dt = datetime.fromisoformat(unlock_at.replace("Z", "+00:00")) if unlock_at \
            else datetime.now(timezone.utc) + timedelta(days=7)
    except ValueError:
        return error_response("invalid_unlock_at", 422)
    if author == "companion":
        try:
            draft = groq_service.generate_capsule_content(
                str(session.id), session.character.key,
                persona_service._sanitize_trained_text(data.get("occasion") or "next week", 120))
        except Exception:
            draft = None
        if not draft:
            return error_response("ai_unavailable_try_later", 503)
        title, content = draft["title"], draft["content"]
    if not content:
        return error_response("content_required", 422)
    capsule = SaathiMomentCapsule(session_id=session.id, title=title,
                                  content=content, author=author,
                                  unlock_at=unlock_dt)
    db.session.add(capsule)
    db.session.commit()
    return jsonify({"id": str(capsule.id), "title": capsule.title,
                    "unlock_at": capsule.unlock_at.isoformat(),
                    "author": capsule.author,
                    "sealed": _as_aware(capsule.unlock_at) > datetime.now(timezone.utc)})


@saathi_bp.get("/sessions/<session_id>/capsules")
@jwt_required()
def list_capsules(session_id):
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    from app.models import SaathiMomentCapsule

    rows = (SaathiMomentCapsule.query.filter_by(session_id=session.id)
            .order_by(SaathiMomentCapsule.created_at.desc()).limit(30).all())
    now = datetime.now(timezone.utc)
    return jsonify({"capsules": [{
        "id": str(c.id), "title": c.title, "author": c.author,
        "unlock_at": c.unlock_at.isoformat(),
        "content": c.content if _as_aware(c.unlock_at) <= now else None,
        "sealed": _as_aware(c.unlock_at) > now,
        "opened_at": c.opened_at.isoformat() if c.opened_at else None,
    } for c in rows]})


@saathi_bp.post("/capsules/<capsule_id>/open")
@jwt_required()
def open_capsule(capsule_id):
    from app.models import SaathiMomentCapsule

    c = db.session.get(SaathiMomentCapsule, uuid_module.UUID(capsule_id)) if capsule_id else None
    if c is None:
        return error_response("not_found", 404)
    session = _owned_session(str(c.session_id), uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    if _as_aware(c.unlock_at) > datetime.now(timezone.utc):
        return error_response("still_sealed", 409)
    if c.opened_at is None:
        c.opened_at = datetime.now(timezone.utc)
        _award_hearts(session.user_id, 2, "capsule_opened")
        db.session.commit()
    return jsonify({"id": str(c.id), "title": c.title, "content": c.content,
                    "hearts_balance": _hearts_balance(session.user_id)})


@saathi_bp.post("/sessions/<session_id>/recap")
@jwt_required()
@limiter.limit("4 per hour")
def build_recap(session_id):
    """Milan Recap share card (#17): deterministic stats from real data +
    one grounded narrative. Share token renders a watermarked public card."""
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    from app.models import SaathiMessage, SaathiRecapCard

    period = (request.get_json(silent=True) or {}).get("period") or "week"
    since = datetime.now(timezone.utc) - timedelta(
        days={"week": 7, "month": 30}.get(period, 7))
    msgs = (SaathiMessage.query.filter_by(session_id=session.id)
            .filter(SaathiMessage.created_at >= since).all())
    user_msgs = [m for m in msgs if m.role == "user"]
    payload = {
        "period": period,
        "messages_exchanged": len(msgs),
        "your_messages": len(user_msgs),
        "days_active": len({m.created_at.astimezone(KATHMANDU_TZ).strftime("%Y-%m-%d") for m in msgs}),
        "streak_days": session.streak_days or 0,
        "intimacy_stage": groq_service.intimacy_stage(session.intimacy_level or 0),
        "memories_kept": len(session.memory_items),
        "top_context": (session.user_mood or "cheerful"),
    }
    try:
        narrative = groq_service.generate_recap_narrative(payload)
    except Exception:
        narrative = None
    card = SaathiRecapCard(
        session_id=session.id, period=period, payload={**payload, "narrative": narrative},
        share_token=uuid_module.uuid4().hex)
    db.session.add(card)
    _award_hearts(session.user_id, 4, "recap_created")
    db.session.commit()
    return jsonify({"id": str(card.id), "payload": card.payload,
                    "share_token": card.share_token,
                    "share_url": f"/recap/{card.share_token}",
                    "watermark": card.watermark,
                    "hearts_balance": _hearts_balance(session.user_id)})


@saathi_bp.get("/hearts")
@jwt_required()
def hearts_balance():
    user_id = uuid_module.UUID(get_jwt_identity())
    from app.models import SaathiHeartLedger

    rows = (SaathiHeartLedger.query.filter_by(user_id=user_id)
            .order_by(SaathiHeartLedger.created_at.desc()).limit(25).all())
    return jsonify({"balance": rows[0].balance_after if rows else 0,
                    "ledger": [{"delta": r.delta, "reason": r.reason,
                                "balance": r.balance_after,
                                "at": r.created_at.isoformat()} for r in rows]})


# ---------------------------------------------------------------------------
# §16 "send me a pic": the companion shares an illustrated moment of her/his
# day. Identity-locked face prompt (same face every time), behaves like a
# human: typing indicator → delay → photo with a casual caption, never a raw
# image dump. Content is illustrated-only + AI-labeled (master plan §12.1).
# ---------------------------------------------------------------------------

@saathi_bp.post("/sessions/<session_id>/selfie")
@jwt_required()
@limiter.limit("8 per day")
def send_selfie(session_id):
    session = _owned_session(session_id, uuid_module.UUID(get_jwt_identity()))
    if session is None:
        return error_response("session_not_found", 404)
    if session.is_paused:
        return error_response("session_paused", 409)

    tier = subscription_service.get_user_tier(session.user_id)
    if not subscription_service.tier_at_least(tier, "basic"):
        return {"error": "upgrade_required",
                "message": "Photo moments need a Milan pass.",
                "required_tier": "basic"}, 403

    character = session.character

    # 1) a short in-character caption from recent chat context (cheap model)
    from app.models import SaathiMessage

    recent = (SaathiMessage.query.filter_by(session_id=session.id)
              .order_by(SaathiMessage.created_at.desc()).limit(10).all())
    recent.reverse()
    context_note = "\n".join(f"{m.role}: {m.content}" for m in recent)[-900:]
    caption = None
    scene_hint = "sharing how my day looked"
    if not groq_service._mock_mode():
        try:
            raw = groq_service._chat(
                groq_service.MODELS["icebreaker"],
                [
                    {"role": "system", "content": (
                        "You are an AI companion sharing one illustrated 'moment from "
                        "my day' photo with the user. Write ONE casual caption (max 15 "
                        "words, lowercase, natural texting style) and ONE short visual "
                        "scene description for the illustration (what you're doing, where). "
                        "Return JSON: {\"caption\": \"...\", \"scene\": \"...\"}")},
                    {"role": "user", "content": f"Recent chat:\n{context_note or '(new bond)'}"},
                ],
                temperature=0.9, max_tokens=200, json_mode=True,
            )
            parsed = groq_service._parse_json(raw)
            caption = (parsed.get("caption") or "").strip()[:160] or None
            scene_hint = (parsed.get("scene") or scene_hint)[:220]
        except groq_service.GroqUnavailableError:
            pass  # falls back to the default scene; image still identity-locked

    # 2) generate the identity-locked illustration
    from app.services import image_gen_service

    try:
        img = groq_service.generate_companion_image(character.key, scene_hint)
    except image_gen_service.ImageGenUnavailableError:
        return error_response("ai_unavailable_try_later", 503)

    from app.models import SaathiMediaItem

    item = SaathiMediaItem(
        session_id=session.id, kind="moment", url=img["url"],
        prompt=groq_service.companion_face_prompt(character.key, scene_hint)[:500],
        ai_label="AI-illustrated moment")
    db.session.add(item)

    if caption:
        db.session.add(SaathiMessage(
            session_id=session.id, role="saathi", content=caption))
    db.session.commit()

    # 3) mirror into the unified chat thread so it lands in the normal inbox
    match_envelope = None
    if session.match_id:
        from app.models import Message
        from app.services import companion_account_service

        match = db.session.get(__import__("app.models", fromlist=["Match"]).Match,
                               session.match_id)
        if match is not None:
            companion_id = (match.user_b_id if match.user_a_id == session.user_id
                            else match.user_a_id)
            if caption:
                cap_msg = Message(match_id=match.id, sender_id=companion_id, body=caption)
                db.session.add(cap_msg)
                db.session.commit()
                from app.sockets.chat_events import broadcast_message

                broadcast_message(str(match.id), {
                    "id": str(cap_msg.id), "sender_id": str(companion_id),
                    "body": caption, "media_url": None,
                    "created_at": cap_msg.created_at.isoformat(),
                    "is_ai_suggested": False})
                match_envelope = {"caption_message_id": str(cap_msg.id)}

    human_delay = 2.5 + (len(caption or "") / 14.0)
    return jsonify({
        "url": img["url"],
        "ai_label": item.ai_label,
        "caption": caption,
        "scene": scene_hint,
        "typing_delay_seconds": round(human_delay, 1),
        "match": match_envelope,
    })
