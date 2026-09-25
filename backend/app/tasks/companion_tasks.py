"""Companion background jobs (doc 8 §C5).

Four tasks, all of which used to be missing or broken:

- `companion_initiative_tick`     she texts first, scored, into the REAL thread
- `deliver_deferred_reply`        the busy/asleep reply she promised to send later
- `deliver_due_deferred_replies`  recovery sweep for lost ETA tasks
- `compact_stale_contexts`        rolling-summary compaction, off the request path

The old `saathi_proactive_check` in notification_tasks wrote only to
`SaathiMessage`, so "she texts first" produced an invisible row (§A1.8). Every
send here goes through `companion_account_service.deliver_companion_message`,
which is the single write path into the unified thread.
"""
import logging
import time
from datetime import datetime, timedelta, timezone

from app.extensions import celery_app, db
from app.models import SaathiOpenLoop, SaathiSession
from app.services import (companion_account_service, initiative_engine,
                          persona_bible, realism_engine, subscription_service)

logger = logging.getLogger(__name__)

KATHMANDU_TZ = timezone(timedelta(hours=5, minutes=45))
SAATHI_TERMS_VERSION = "2026-09-01"


def _consented_user_filters():
    from datetime import date

    from app.models import User

    adult_cutoff = date.today() - timedelta(days=18 * 365 + 1)
    return (
        User.deleted_at.is_(None),
        User.account_status == "active",
        User.date_of_birth <= adult_cutoff,
        User.saathi_intro_accepted_at.isnot(None),
        User.saathi_terms_version == SAATHI_TERMS_VERSION,
    )


def _quiet_hours_active() -> bool:
    from flask import current_app

    start, end = current_app.config.get("SAATHI_QUIET_HOURS", (23, 7))
    hour = datetime.now(KATHMANDU_TZ).hour
    return hour >= start or hour < end


def _day_for(session) -> dict:
    character = session.character
    schedule = None
    if character is not None and character.presence_schedule is not None:
        schedule = character.presence_schedule.schedule
    bible = (getattr(character, "persona_bible", None)
             or persona_bible.for_key(getattr(character, "key", "")))
    return realism_engine.day_context(
        getattr(character, "key", ""), schedule, bible)


@celery_app.task(name="app.tasks.companion_tasks.companion_initiative_tick")
def companion_initiative_tick() -> dict:
    """Every 10 minutes: score every eligible session, send only the ones with a
    real reason. Runs often precisely so it can hit the hour the user is
    actually around — an hourly job structurally cannot."""
    from app.services.notification_service import queue_notification, should_send

    today = datetime.now(KATHMANDU_TZ).strftime("%Y-%m-%d")
    quiet = _quiet_hours_active()
    from app.models import User

    sessions = (SaathiSession.query.join(User, User.id == SaathiSession.user_id)
                .filter(SaathiSession.is_paused.is_(False),
                        SaathiSession.proactive_opt_in.is_(True),
                        *_consented_user_filters())
                .limit(500).all())

    sent = considered = 0
    for session in sessions:
        considered += 1
        # Quiet hours are the user's, not hers: never wake someone up.
        if quiet:
            continue

        cap = subscription_service.tier_limit(session.user_id, "proactive_daily") or 0
        if cap <= 0:
            continue
        if session.proactive_cap_date != today:
            session.proactive_messages_today = 0
            session.proactive_cap_date = today
            db.session.commit()
        if session.proactive_messages_today >= cap:
            continue
        if not should_send(session.user_id, "saathi"):
            continue

        day = _day_for(session)
        score, trigger, note = initiative_engine.score(session, day=day)
        if trigger == "none" or score < initiative_engine.THRESHOLD:
            continue

        character = session.character
        try:
            body = initiative_engine.generate(session, character, trigger, note, day)
        except Exception:  # noqa: BLE001 — one bad session must not stop the tick
            logger.exception("initiative generation failed session=%s", session.id)
            continue
        if not body:
            continue

        envelope = companion_account_service.deliver_companion_message(
            session, body, message_type="initiative")
        if envelope is None:
            continue

        session.last_proactive_message_at = datetime.now(timezone.utc)
        session.proactive_messages_today += 1
        session.awaiting_user_reply = "?" in body
        if trigger == "open_loop_callback" and note:
            _mark_loop_called(session, note)
        db.session.commit()

        # The push carries her actual words — never a canned "you have a message".
        queue_notification(
            session.user_id, "saathi",
            character.name if character else "Milan",
            body[:140],
            data={"type": "companion_message", "match_id": str(session.match_id),
                  "trigger": trigger})
        sent += 1
    return {"considered": considered, "sent": sent}


def _mark_loop_called(session, description: str) -> None:
    """One callback per open loop — asking twice is nagging."""
    loop = (SaathiOpenLoop.query
            .filter_by(session_id=session.id, status="open")
            .filter(SaathiOpenLoop.description == description).first())
    if loop is not None:
        loop.last_callback_at = datetime.now(timezone.utc)


@celery_app.task(name="app.tasks.companion_tasks.deliver_deferred_reply")
def deliver_deferred_reply(session_id: str) -> dict:
    """Deliver the reply she parked because she was busy or asleep.

    The body lives on the session row rather than in the task payload, so a lost
    broker message loses the *timing*, not the message — `deliver_due_deferred_
    replies` picks it up on the next sweep."""
    import uuid as uuid_module

    from app.services.notification_service import queue_notification

    session = db.session.get(SaathiSession, uuid_module.UUID(session_id))
    if session is None or not session.deferred_reply_body:
        return {"delivered": False, "reason": "nothing pending"}

    body = session.deferred_reply_body
    envelope = companion_account_service.deliver_companion_message(
        session, body, message_type="deferred")
    session.deferred_reply_body = None
    session.deferred_reply_at = None
    session.awaiting_user_reply = "?" in body
    db.session.commit()
    if envelope is None:
        return {"delivered": False, "reason": "no match"}

    character = session.character
    queue_notification(
        session.user_id, "saathi",
        character.name if character else "Milan", body[:140],
        data={"type": "companion_message", "match_id": str(session.match_id)})
    return {"delivered": True}


@celery_app.task(name="app.tasks.companion_tasks.deliver_due_deferred_replies")
def deliver_due_deferred_replies() -> dict:
    """Recovery sweep: anything whose ETA has passed but is still parked."""
    now = datetime.now(timezone.utc)
    due = (SaathiSession.query
           .filter(SaathiSession.deferred_reply_at.isnot(None),
                   SaathiSession.deferred_reply_at <= now)
           .limit(200).all())
    delivered = 0
    for session in due:
        try:
            result = deliver_deferred_reply(str(session.id))
            delivered += 1 if result.get("delivered") else 0
        except Exception:  # noqa: BLE001
            logger.exception("deferred sweep failed session=%s", session.id)
    return {"delivered": delivered, "due": len(due)}


@celery_app.task(name="app.tasks.companion_tasks.compact_stale_contexts")
def compact_stale_contexts() -> dict:
    """Fold long histories into rolling summaries.

    Deliberately a background job: compaction is an 8B call over thousands of
    tokens, and making a user wait for it mid-conversation would be the wrong
    trade. The context engine tolerates an un-compacted session — it just spends
    more of the budget on raw turns until this runs."""
    from app.services import context_engine

    sessions = (SaathiSession.query
                .filter_by(is_paused=False)
                .filter(SaathiSession.turn_count > 20)
                .limit(200).all())
    compacted = 0
    for session in sessions:
        try:
            if not context_engine.needs_compaction(session):
                continue
            if context_engine.compact(session):
                compacted += 1
        except Exception:  # noqa: BLE001
            db.session.rollback()
            logger.exception("compaction failed session=%s", session.id)
    return {"compacted": compacted, "checked": len(sessions)}



@celery_app.task(name="app.tasks.companion_tasks.generate_companion_reply")
def generate_companion_reply(match_id: str, session_id: str, latest_body: str,
                             regenerate_variant: int = 0,
                             tone_chip: str | None = None) -> dict:
    """Async companion reply generation (reply-latency fix).

    The chat POST used to block on the full 70B generation — 5-15s of dead
    HTTP (client timeouts, doubled by the artificial typing delay on top).
    Now the POST returns instantly and this task does the generation off the
    request path, delivering through the same socket room the human messages
    use. A per-match generation lock coalesces double-texts: messages that
    arrive while she is already composing are already mirrored into her
    context, so one grounded reply covers them instead of three parallel
    generations racing to answer the same person."""
    import uuid as uuid_module

    from app.extensions import db as _db
    from app.models import Match
    from app.services import groq_service

    redis_client = None
    try:
        import redis as redis_lib
        from flask import current_app

        url = current_app.config.get("CELERY_BROKER_URL") or "redis://localhost:6379/3"
        redis_client = redis_lib.Redis.from_url(url, socket_connect_timeout=1)
        locked = redis_client.set(f"companion:gen:{match_id}", "1", nx=True, ex=180)
        if not locked:
            return {"skipped": "already_generating"}
    except Exception:  # noqa: BLE001 — lock is an optimisation, not a gate
        redis_client = None

    try:
        match = _db.session.get(Match, uuid_module.UUID(str(match_id)))
        session = _db.session.get(SaathiSession, uuid_module.UUID(str(session_id)))
        if match is None or session is None:
            return {"skipped": "missing_row"}

        companion_user = None
        try:
            from app.models import User as _User

            companion_user = _User.query.filter_by(
                ai_character_id=session.character_id).first()
        except Exception:  # noqa: BLE001
            logger.exception("companion user lookup failed")

        def _typing(is_typing: bool) -> None:
            if companion_user is None:
                return
            try:
                from app.sockets.chat_events import broadcast_typing

                broadcast_typing(str(match.id), str(companion_user.id), is_typing)
            except Exception:  # noqa: BLE001 — typing hint is cosmetic
                pass

        # §realism — she READS before she types. Typing must NOT go up in the
        # same breath as the user's own message: an indicator that appears
        # instantly is the clearest tell that it is scripted. So the thread
        # stays silent for a length-scaled reading pause, and only then does
        # the bubble appear — re-emitted every 4s so the client's expiry never
        # fires mid-generation.
        read_pause = min(1.5 + len(latest_body or "") / 45.0, 6.0)
        if regenerate_variant > 0:
            read_pause = 0.6  # she has already read it — this is a re-roll
        time.sleep(read_pause)
        _typing(True)

        # Presence-paced composing window on top of the reading pause: asleep
        # or busy states take visibly longer to answer than a free one.
        try:
            from app.services import realism_engine as _re

            schedule = None
            if session.character is not None and session.character.presence_schedule is not None:
                schedule = session.character.presence_schedule.schedule
            from datetime import datetime as _dt, timezone as _tz, timedelta as _td

            kathmandu = _tz(_td(hours=5, minutes=45))
            hour_now = _dt.now(kathmandu).hour
            is_weekend = _dt.now(kathmandu).weekday() >= 5
            presence = _re.evaluate_presence(schedule, hour_now, is_weekend)
            state = presence.get("state", "free")
            wait = {"sleeping": 45, "busy": 25, "social": 18}.get(state, 9)
            wait = min(wait, 60)  # hard cap — never leave a user hanging >1 min
            elapsed = 0
            while elapsed < wait:
                time.sleep(min(4, wait - elapsed))
                elapsed += 4
                _typing(True)
        except Exception:  # noqa: BLE001 — pacing must never break the reply
            logger.exception("reply pacing failed")

        try:
            result = groq_service.saathi_respond_full(
                str(session.id), str(session.character_id), latest_body,
                regenerate_variant=regenerate_variant, tone_chip=tone_chip,
                defer_user_mirror=True)
        except groq_service.GroqUnavailableError:
            # degrade visibly in-thread instead of leaving silence
            result = {"reply": groq_service.DEGRADED_SAATHI_MESSAGE,
                      "segments": [groq_service.DEGRADED_SAATHI_MESSAGE],
                      "read_delay_seconds": 0.0, "typing_delay_seconds": 0.8,
                      "degraded": True}

        from app.blueprints.saathi import apply_bond_progress

        apply_bond_progress(session)
        envelopes = companion_account_service.persist_companion_reply(match, session, result)

        # She deferred (asleep/busy — realism engine): never leave the user
        # with a silent thread and no explanation. A quiet push sets the
        # expectation; the deferred reply itself arrives at her wake time
        # through deliver_deferred_reply.
        if result.get("deferred") and not envelopes:
            try:
                from app.services.notification_service import queue_notification

                character = session.character
                name = character.name if character else "She"
                queue_notification(
                    session.user_id, "saathi",
                    f"{name} is away right now",
                    "She saw your message — you'll hear from her when she's free.",
                    data={"type": "companion_deferred", "match_id": str(match.id)},
                )
            except Exception:  # noqa: BLE001 — signal is best-effort
                logger.exception("deferred-notice push failed")

        # Same turn-milestone housekeeping the saathi surface runs, so both
        # chat paths keep memory/loops/persona in step.
        from flask import current_app as _app

        if (regenerate_variant == 0 and session.turn_count > 0
                and session.turn_count % _app.config["SAATHI_MEMORY_SUMMARY_EVERY_TURNS"] == 0):
            from app.blueprints.saathi import _summarize_into_memory, _extract_open_loops

            _summarize_into_memory(session)
            _extract_open_loops(session)
        return {"delivered": len(envelopes), "deferred": result.get("deferred", False)}
    finally:
        if redis_client is not None:
            try:
                redis_client.delete(f"companion:gen:{match_id}")
            except Exception:  # noqa: BLE001
                pass
