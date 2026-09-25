import logging
from datetime import datetime, timedelta, timezone

from flask import current_app

from app.extensions import celery_app, db
from app.models import (SaathiCharacter, SaathiMessage, SaathiOpenLoop,
                        SaathiSession, SaathiStatusPost, DeviceToken, Notification, User)
from app.services import groq_service, initiative_engine, subscription_service
from app.services.notification_service import predicted_send_time, queue_notification

logger = logging.getLogger(__name__)

KATHMANDU_TZ = timezone(timedelta(hours=5, minutes=45))

NEPALI_FESTIVALS = {
    # (month, day) Gregorian anchors — updated per year; close-enough windows
    # are fine because the generator grounds the greeting in the name alone.
    "Dashain": (10, 1),
    "Tihar": (10, 20),
    "Teej": (9, 4),
    "Holi": (3, 13),
}


@celery_app.task(name="app.tasks.notification_tasks.send_scheduled_notifications")
def send_scheduled_notifications() -> dict:
    """Deliver queued notifications at each user's predicted send time, respecting caps."""
    now = datetime.now(timezone.utc)
    queued = Notification.query.filter(Notification.sent_at.is_(None)).limit(200).all()
    sent = 0
    for notification in queued:
        window = predicted_send_time(notification.user_id)
        if window > now:
            continue
        user = db.session.get(User, notification.user_id)
        if user is None:
            continue
        _deliver_push(user, notification)
        notification.sent_at = now
        sent += 1
    db.session.commit()
    return {"sent": sent}


def _quiet_hours_active() -> bool:
    start, end = current_app.config.get("SAATHI_QUIET_HOURS", (23, 7))
    hour = datetime.now(KATHMANDU_TZ).hour
    return hour >= start or hour < end


def _active_festival() -> str | None:
    today = datetime.now(KATHMANDU_TZ)
    for name, (month, day) in NEPALI_FESTIVALS.items():
        anchor = datetime(today.year, month, day, tzinfo=KATHMANDU_TZ)
        if abs((today - anchor).days) <= 2:
            return name
    return None


def _choose_trigger(session: SaathiSession) -> tuple[str, str | None]:
    """Superseded by `initiative_engine.score` (doc 8 §C5). Retained only as a
    fallback for callers that still ask for a single trigger name."""
    day = {"state": "free"}
    _score, trigger, note = initiative_engine.score(session, day=day)
    return trigger, note


@celery_app.task(name="app.tasks.notification_tasks.saathi_proactive_check")
def saathi_proactive_check() -> dict:
    """Superseded by the initiative engine (doc 8 §C5).

    Kept as a thin delegation because the beat schedule, deploy scripts and
    tests all reference this task name. The rank-ordered trigger ladder it used
    to implement (`_choose_trigger`) picked a reason by priority rather than by
    whether it was a good moment, and wrote only to `SaathiMessage` so nothing
    reached the inbox. `companion_initiative_tick` scores instead, and delivers
    through the unified thread."""
    from app.tasks.companion_tasks import companion_initiative_tick

    return companion_initiative_tick()



@celery_app.task(name="app.tasks.notification_tasks.saathi_status_posts")
def saathi_status_posts() -> dict:
    """Ambient 'her day' status posts (master plan §4.5), 2-3x daily for
    opted-in romantic sessions within their tier's per-day cap."""
    now = datetime.now(timezone.utc)
    today = datetime.now(KATHMANDU_TZ).strftime("%Y-%m-%d")
    from app.models import User
    from datetime import date

    adult_cutoff = date.today() - timedelta(days=18 * 365 + 1)
    candidates = (SaathiSession.query
                  .join(User, User.id == SaathiSession.user_id)
                  .filter(SaathiSession.is_paused.is_(False),
                          SaathiSession.companion_mode == "dating",
                          SaathiSession.proactive_opt_in.is_(True),
                          User.deleted_at.is_(None),
                          User.account_status == "active",
                          User.date_of_birth <= adult_cutoff,
                          User.saathi_intro_accepted_at.isnot(None),
                          User.saathi_terms_version == "2026-09-01")
                  .limit(300).all())

    created = 0
    for session in candidates:
        cap = subscription_service.tier_limit(session.user_id, "status_posts_daily") or 0
        if cap <= 0:
            continue
        if session.status_cap_date != today:
            session.status_posts_today = 0
            session.status_cap_date = today
        if session.status_posts_today >= cap:
            continue

        character = session.character
        schedule = character.presence_schedule.schedule if character and character.presence_schedule else None
        local_hour = datetime.now(KATHMANDU_TZ).hour
        presence = groq_service.evaluate_presence(schedule, local_hour, local_now_weekend())
        if presence["state"] == "sleeping":
            continue

        try:
            body = groq_service.generate_status_post(
                str(session.id), character.key, presence.get("activity"))
        except groq_service.GroqUnavailableError:
            logger.warning("status post skipped (AI unavailable) session=%s", session.id)
            continue
        if body is None:
            continue
        db.session.add(SaathiStatusPost(
            session_id=session.id, body=body, kind="ambient",
            expires_at=now + timedelta(hours=24),
        ))
        session.status_posts_today += 1
        created += 1
    db.session.commit()
    return {"created": created}


@celery_app.task(name="app.tasks.notification_tasks.saathi_mood_decay")
def saathi_mood_decay() -> dict:
    """Nightly mood reset toward baseline (master plan §4.6): moods decay to
    'cheerful'; silence beyond a week softens the mood to 'low-key'. Never
    guilt-trips — decay only changes tone, it never punishes."""
    updated = 0
    from app.models import User

    sessions = (SaathiSession.query
                .join(User, User.id == SaathiSession.user_id)
                .filter(SaathiSession.companion_mode == "dating",
                        SaathiSession.is_paused.is_(False),
                        *_consented_session_filters())
                .limit(1000).all())
    now = datetime.now(timezone.utc)
    for session in sessions:
        mood = session.current_mood or "cheerful"
        if session.last_message_at and (now - session.last_message_at).days >= 7:
            new_mood = "mellow"
        else:
            new_mood = "cheerful"
        if new_mood != mood:
            session.current_mood = new_mood
            updated += 1
    db.session.commit()
    return {"updated": updated}


@celery_app.task(name="app.tasks.notification_tasks.saathi_open_loop_followup")
def saathi_open_loop_followup() -> dict:
    """Daily sweep for sessions the initiative tick missed (e.g. every candidate
    window fell inside the user's quiet hours). Same caps apply."""
    from app.tasks.companion_tasks import companion_initiative_tick

    return {"open_loop_sweep": companion_initiative_tick()}


def _consented_session_filters():
    from app.models import User
    from datetime import date

    adult_cutoff = date.today() - timedelta(days=18 * 365 + 1)
    return (
        User.deleted_at.is_(None),
        User.account_status == "active",
        User.date_of_birth <= adult_cutoff,
        User.saathi_intro_accepted_at.isnot(None),
        User.saathi_terms_version == "2026-09-01",
    )


def _consented_sessions(minimum_turns: int):
    from app.models import User

    return (SaathiSession.query
            .join(User, User.id == SaathiSession.user_id)
            .filter(SaathiSession.companion_mode == "dating",
                    SaathiSession.is_paused.is_(False),
                    SaathiSession.turn_count > minimum_turns,
                    *_consented_session_filters())
            .all())


def _saathi_owner_allowed(user) -> bool:
    """Shared consent gate for background jobs that load sessions directly."""
    from datetime import date

    from app.utils.validators import validate_age_18

    return (
        user is not None
        and user.deleted_at is None
        and user.account_status == "active"
        and validate_age_18(user.date_of_birth)
        and user.saathi_intro_accepted_at is not None
        and user.saathi_terms_version == "2026-09-01"
    )


def local_now_weekend() -> bool:
    return datetime.now(KATHMANDU_TZ).weekday() >= 5


def queue_notification_gate(user_id) -> bool:
    from app.services.notification_service import should_send

    return should_send(user_id, "saathi")


def _deliver_push(user: User, notification: Notification) -> None:
    """Deliver rich push (doc 1 §4.8) via OneSignal REST when configured;
    MockPushBackend (structured log delivery) otherwise, so the full
    queue->cap->send pipeline stays observable in dev."""
    from flask import current_app

    app_id = current_app.config.get("ONESIGNAL_APP_ID")
    api_key = current_app.config.get("ONESIGNAL_API_KEY")
    tokens = [
        dt.token for dt in DeviceToken.query.filter_by(user_id=user.id).all()
    ]
    if app_id and api_key and tokens:
        import requests

        # OneSignal v5 SDK subscription ids go in include_subscription_ids;
        # include_player_ids is the legacy alias and is rejected for
        # v5-registered devices, which is why dashboard sends worked but
        # API sends silently addressed nobody.
        try:
            resp = requests.post(
                "https://api.onesignal.com/notifications",
                headers={
                    "Authorization": f"Key {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "app_id": app_id,
                    "include_subscription_ids": tokens,
                    "target_channel": "push",
                    "headings": {"en": notification.title},
                    "contents": {"en": notification.body},
                    "data": notification.data or {},
                    # quick-reply affordances where platform supports them
                    "buttons": _quick_actions(notification.category),
                },
                timeout=10,
            )
            ok = resp.status_code in (200, 201)
            if not ok:
                logger.warning("push rejected user=%s status=%s body=%s",
                               user.id, resp.status_code, resp.text[:200])
            else:
                logger.info("push sent user=%s recipients=%s",
                            user.id, resp.json().get("recipients"))
        except requests.RequestException:
            ok = False
            logger.exception("push delivery failed user=%s", user.id)
    else:
        ok = _log_push(user, notification)


def _log_push(user, notification) -> bool:
    logger.info("[MockPushBackend] user=%s category=%s title=%s",
                user.id, notification.category, notification.title)
    return True


def _quick_actions(category: str) -> list[dict]:
    return {
        "messages": [{"id": "open-chat", "text": "Open chat"},
                     {"id": "mute-1h", "text": "Mute 1h"}],
        "matches": [{"id": "view-match", "text": "Say hi"}],
    }.get(category, [])


# ---------------------------------------------------------------------------
# §13 continuous persona evolution + Phase 3/4 ambient jobs
# ---------------------------------------------------------------------------

@celery_app.task(name="app.tasks.notification_tasks.saathi_persona_evolution")
def saathi_persona_evolution() -> dict:
    """Nightly continuous evolution: re-distill each active romantic persona
    from the latest chats (gradual drift, never flips). Also refreshes the
    style digest mined from the user's other Milan chats when enabled."""
    from app.extensions import db
    from app.models import SaathiMessage, SaathiPersonaProfile, SaathiSession, User
    from app.services import persona_service

    updated = 0
    profiles = SaathiPersonaProfile.query.all()
    for persona in profiles:
        session = db.session.get(SaathiSession, persona.session_id)
        if session is None or session.companion_mode != "dating" or session.is_paused:
            continue
        owner = db.session.get(User, session.user_id)
        if not _saathi_owner_allowed(owner):
            continue
        recent = (SaathiMessage.query.filter_by(session_id=session.id)
                  .order_by(SaathiMessage.created_at.desc()).limit(30).all())
        if len(recent) < 6:
            continue  # nothing meaningful to evolve from
        recent.reverse()
        lines = [f"{m.role}: {m.content}" for m in recent]
        digest = None
        if persona.style_mining_enabled:
            digest = persona_service.mine_style_digest(session.user_id)
            if digest:
                persona.style_digest = digest
        try:
            result = persona_service.evolve_persona(session, persona, lines,
                                                    style_digest=digest)
        except Exception:
            continue
        if result:
            persona.traits = result["traits"]
            if result.get("persona_prompt"):
                persona.persona_prompt = result["persona_prompt"]
            persona.evolution_count = (persona.evolution_count or 0) + 1
            persona.evolved_at = datetime.now(timezone.utc)
            updated += 1
    db.session.commit()
    return {"personas_updated": updated, "checked": len(profiles)}


@celery_app.task(name="app.tasks.notification_tasks.saathi_nightly_diary")
def saathi_nightly_diary() -> dict:
    """Companion diary (#29): generates tonight's entry for active sessions
    (idempotent per day). Illustration is on-demand via the API endpoint."""
    from app.extensions import db
    from app.models import SaathiDiaryEntry, SaathiSession
    from app.services import groq_service

    local_now = datetime.now(timezone(timedelta(hours=5, minutes=45)))
    if local_now.hour < 21:
        return {"skipped": "not night yet"}
    today = local_now.strftime("%Y-%m-%d")
    created = 0
    sessions = _consented_sessions(3)
    for session in sessions:
        if SaathiDiaryEntry.query.filter_by(session_id=session.id, day_key=today).first():
            continue
        try:
            draft = groq_service.generate_diary_entry(str(session.id), session.character.key)
        except Exception:
            continue
        if not draft:
            continue
        db.session.add(SaathiDiaryEntry(
            session_id=session.id, day_key=today,
            title=(draft.get("title") or "today")[:160],
            body=draft["body"], mood=draft.get("mood")))
        created += 1
    db.session.commit()
    return {"diary_entries_created": created}


@celery_app.task(name="app.tasks.notification_tasks.saathi_quests_refresh")
def saathi_quests_refresh() -> dict:
    """Phase 4 duo quests: seed a new quest when a session has none active;
    anniversaries trigger a sealed capsule + hearts bonus."""
    from app.extensions import db
    from app.models import SaathiMomentCapsule, SaathiQuest, SaathiSession
    from app.services import groq_service

    seeded = capsules = 0
    sessions = _consented_sessions(5)
    for session in sessions:
        has_active = SaathiQuest.query.filter_by(session_id=session.id, status="active").first()
        if not has_active:
            try:
                draft = groq_service.generate_quest(str(session.id), session.character.key)
            except Exception:
                draft = None
            if draft:
                db.session.add(SaathiQuest(
                    session_id=session.id, title=draft["title"],
                    description=draft["description"],
                    reward_points=draft.get("reward_points", 10)))
                seeded += 1
        # anniversary: started_at month-day == today
        started = session.started_at.astimezone(timezone(timedelta(hours=5, minutes=45)))
        today = datetime.now(timezone(timedelta(hours=5, minutes=45)))
        anniversary = (started.month == today.month and started.day == today.day
                       and started.date() != today.date())
        if anniversary and not SaathiMomentCapsule.query.filter_by(
                session_id=session.id, author="companion").filter(
                SaathiMomentCapsule.created_at >= today - timedelta(days=1)).first():
            try:
                draft = groq_service.generate_capsule_content(
                    str(session.id), session.character.key, "your anniversary")
            except Exception:
                draft = None
            if draft:
                db.session.add(SaathiMomentCapsule(
                    session_id=session.id, title=draft["title"],
                    content=draft["content"], author="companion",
                    unlock_at=datetime.now(timezone.utc) + timedelta(hours=1)))
                capsules += 1
    db.session.commit()
    return {"quests_seeded": seeded, "anniversary_capsules": capsules}
