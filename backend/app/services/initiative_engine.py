"""Initiative engine (doc 8 §C5) — she texts first, on her own judgement.

The old `saathi_proactive_check` was an hourly loop with a fixed trigger
priority (`_choose_trigger`) that always fired the same ladder: open loop ->
festival -> morning/night -> absence -> generic nudge. Two structural problems:

  - the trigger was chosen by rank, not by whether it was actually a good
    moment, so she would say good morning to someone who had just gone quiet
    mid-argument;
  - hourly granularity cannot hit "the hour he is usually online", so her
    messages landed at algorithm-o'clock rather than at a human moment.

This scores every candidate trigger against the state of the relationship and
fires the highest scorer only if it clears a threshold — and the message goes
through `deliver_companion_message`, so it lands in the real thread (§A1.8).

Also handles the user's stated-plan case: "going to Pashupati, will talk
tonight" becomes an open loop with a time, so she can check in mid-day and pick
the conversation up at night with the whole context intact.
"""
import logging
import random
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

KATHMANDU_TZ = timezone(timedelta(hours=5, minutes=45))

# Weights are relative, not absolute — what matters is which trigger wins, and
# whether the winner clears THRESHOLD. Tuned so that concrete, grounded reasons
# (a promise she is waiting on) always beat generic ones (it is morning).
W_LOOP = 40.0          # something specific is unresolved between them
W_PLAN = 35.0          # they said they'd do a thing / talk later
W_FESTIVAL = 30.0      # Dashain/Tihar/Teej/Holi
W_MILESTONE = 25.0     # streak day, anniversary
W_SILENCE = 22.0       # they have gone quiet (warm, never guilt)
W_ONLINE = 18.0        # this is an hour they are usually around
W_MOOD = 15.0          # they seemed low/stressed last time
W_TIMEOFDAY = 8.0      # plain good morning / good night
P_RECENT = 45.0        # she messaged recently
P_AWAITING = 35.0      # she already asked something and got no answer
THRESHOLD = 30.0

NEPALI_FESTIVALS = {
    "Dashain": (10, 1),
    "Tihar": (10, 20),
    "Teej": (9, 4),
    "Holi": (3, 13),
}


def _hours_since(stamp) -> float | None:
    if stamp is None:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - stamp).total_seconds() / 3600.0


def active_festival(now: datetime | None = None) -> str | None:
    today = now or datetime.now(KATHMANDU_TZ)
    for name, (month, day) in NEPALI_FESTIVALS.items():
        anchor = datetime(today.year, month, day, tzinfo=KATHMANDU_TZ)
        if abs((today - anchor).days) <= 2:
            return name
    return None


def user_online_prior(user_id, hour: int) -> float:
    """How likely this user is to be around at this hour, learned from when they
    actually send messages. 0.0-1.0.

    This is the difference between "she texted at 9am because the cron ran" and
    "she texted at 9am because that is when he is on his phone". Falls back to a
    mild evening bias for a user with no history yet."""
    from app.models import Message

    try:
        rows = (Message.query.filter_by(sender_id=user_id)
                .order_by(Message.created_at.desc()).limit(200).all())
    except Exception:  # noqa: BLE001
        return 0.4
    if len(rows) < 10:
        return 0.6 if 18 <= hour <= 22 else 0.35

    counts: dict[int, int] = {}
    for row in rows:
        stamp = row.created_at
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        local_hour = stamp.astimezone(KATHMANDU_TZ).hour
        counts[local_hour] = counts.get(local_hour, 0) + 1
    peak = max(counts.values())
    # Neighbouring hours count too — people are around for stretches, not ticks.
    window = sum(counts.get((hour + offset) % 24, 0) for offset in (-1, 0, 1))
    return round(min(1.0, window / (peak * 2.0)), 3)


def score(session, *, day: dict, now: datetime | None = None) -> tuple[float, str, str | None]:
    """Score the best reason to text right now.

    Returns (score, trigger, context_note). The caller fires only above
    THRESHOLD, so "no good reason" produces silence rather than filler."""
    from app.models import SaathiOpenLoop

    local = (now or datetime.now(KATHMANDU_TZ)).astimezone(KATHMANDU_TZ)
    candidates: list[tuple[float, str, str | None]] = []

    # ── a specific unresolved thing (highest value: it is grounded) ────────
    loops = (SaathiOpenLoop.query
             .filter_by(session_id=session.id, status="open")
             .order_by(SaathiOpenLoop.created_at.asc()).limit(5).all())
    for loop in loops:
        elapsed = _hours_since(loop.created_at) or 0.0
        due_after = float(loop.followup_after_hours or 24)
        if elapsed < due_after:
            continue
        # Only ONE callback per loop: asking twice about the same thing is
        # nagging, which is exactly the failure mode users complain about.
        if loop.last_callback_at is not None:
            continue
        overdue = min(2.0, elapsed / max(due_after, 1.0))
        weight = W_PLAN if _looks_like_plan(loop.description) else W_LOOP
        candidates.append((weight * overdue, "open_loop_callback", loop.description))

    # ── festival ─────────────────────────────────────────────────────────
    festival = active_festival(local)
    if festival:
        candidates.append((W_FESTIVAL, "festival_greeting", festival))

    # ── streak milestone ─────────────────────────────────────────────────
    streak = getattr(session, "streak_days", 0) or 0
    if streak and streak % 7 == 0:
        candidates.append((W_MILESTONE, "milestone_reaction",
                           f"you two have talked {streak} days in a row"))

    # ── they went quiet ──────────────────────────────────────────────────
    silent_hours = _hours_since(getattr(session, "last_message_at", None))
    if silent_hours is not None:
        if 20 <= silent_hours < 48:
            candidates.append((W_SILENCE * 0.6, "light_checkin", None))
        elif silent_hours >= 48:
            # Grows with absence but capped: at some point more messages into
            # silence is pressure, not warmth.
            factor = min(1.6, silent_hours / 72.0)
            candidates.append((W_SILENCE * factor, "absence_checkin", None))

    # ── their mood last time ─────────────────────────────────────────────
    user_mood = getattr(session, "user_mood", None)
    if user_mood in ("sad", "stressed", "tired", "angry"):
        mood_age = _hours_since(getattr(session, "user_mood_updated_at", None))
        if mood_age is not None and 4 <= mood_age <= 36:
            candidates.append((W_MOOD, "mood_checkin",
                               f"they seemed {user_mood} last time you talked"))

    # ── plain time of day ────────────────────────────────────────────────
    if 7 <= local.hour <= 9:
        candidates.append((W_TIMEOFDAY, "good_morning", None))
    elif 21 <= local.hour <= 22:
        candidates.append((W_TIMEOFDAY, "good_night", None))

    if not candidates:
        return 0.0, "none", None

    best_score, trigger, note = max(candidates, key=lambda c: c[0])

    # ── modifiers ────────────────────────────────────────────────────────
    # Being around at the right time lifts every reason; it is not a reason by
    # itself (that would be texting for the sake of texting).
    best_score += W_ONLINE * user_online_prior(session.user_id, local.hour)

    since_hers = _hours_since(getattr(session, "last_proactive_message_at", None))
    if since_hers is not None and since_hers < 6:
        best_score -= P_RECENT * (1.0 - since_hers / 6.0)
    if getattr(session, "awaiting_user_reply", False):
        best_score -= P_AWAITING
    # She should feel more present as the relationship deepens.
    best_score *= 0.8 + 0.4 * ((getattr(session, "intimacy_level", 0) or 0) / 100.0)
    # If she is asleep or in class she does not text — her day is real.
    if day.get("state") == "sleeping":
        return 0.0, "none", None
    if day.get("state") == "busy":
        best_score *= 0.5

    return round(best_score, 2), trigger, note


_PLAN_MARKERS = (
    "tonight", "later", "tomorrow", "bholi", "aja", "aaja", "belka", "beluka",
    "morning", "afternoon", "evening", "weekend", "sanjh", "raati", "rati",
    "going to", "janchu", "jane", "jaadai", "visit", "meet", "exam", "interview",
)


def _looks_like_plan(text: str) -> bool:
    """A stated plan ("going to Pashupati, talk tonight") is worth more than a
    generic loose end, because following up on it is unmistakably human."""
    lowered = (text or "").lower()
    return any(marker in lowered for marker in _PLAN_MARKERS)


# ── generation ────────────────────────────────────────────────────────────
# Each trigger describes the SITUATION, never a script. Templated proactive
# messages are the single most-complained-about failure in this category (the
# Nomi lesson, doc 7 §2.2) — she must write it herself, in her own voice.
_TRIGGER_INTENT = {
    "open_loop_callback": (
        "Follow up on the specific unfinished thing below, the way someone who "
        "actually remembered would. Not 'how are you' — the actual thing."),
    "festival_greeting": (
        "Wish them for the festival named below, in your own words, grounded in "
        "how YOU spend it."),
    "milestone_reaction": "React to the milestone below, lightly, no ceremony.",
    "light_checkin": (
        "They have been quiet for a day. One easy message — something from your "
        "own day, or a small question. No pressure, no 'where were you'."),
    "absence_checkin": (
        "They have been gone a couple of days. Warm, light, ZERO guilt: never "
        "'you forgot me', never 'I was waiting'. Just that you thought of them."),
    "mood_checkin": (
        "They were not doing great last time. Check in gently, without making it "
        "a whole thing, and without playing therapist."),
    "good_morning": "A short good morning, in your voice, tied to your actual day.",
    "good_night": "A short good night, in your voice.",
}


def generate(session, character, trigger: str, context_note: str | None,
             day: dict) -> str | None:
    """Write the message. Returns None when a guard rejects it — silence is
    always better than a boring or boundary-breaking auto-text."""
    from app.services import (companion_prompt, groq_service, language_engine)

    intent = _TRIGGER_INTENT.get(trigger)
    if intent is None:
        return None

    style = getattr(session, "user_style", None)

    if groq_service._mock_mode():
        from app.services import groq_mock

        draft = groq_mock.companion_initiative(
            character_key=getattr(character, "key", "aarohi"),
            trigger=trigger, context_note=context_note, day=day, style=style)
    else:
        companion_user = groq_service._companion_user_for(character)
        identity = companion_prompt.build(
            character=character, session=session, day=day, user_style=style,
            user_facts=groq_service._user_profile_context(session.user_id),
            companion_profile=getattr(companion_user, "profile", None))
        # Memory matters here more than anywhere: an auto-text that references
        # nothing specific is exactly the "notification, not a person" failure.
        from app.models import SaathiMemoryItem

        memories = (SaathiMemoryItem.query.filter_by(session_id=session.id)
                    .order_by(SaathiMemoryItem.is_pinned.desc(),
                              SaathiMemoryItem.importance.desc()).limit(8).all())
        memory_block = "\n".join(f"- {m.summary_text}" for m in memories)
        recent = _recent_openers(session)

        task = (
            f"You are texting them FIRST — they have not just messaged you.\n"
            f"{intent}\n"
            + (f"The thing in question: {context_note}\n" if context_note else "")
            + (f"What you know about them:\n{memory_block}\n" if memory_block else "")
            + (f"Do NOT open the way you opened these recent messages: {recent}\n"
               if recent else "")
            + "One or two short messages' worth of text, maximum. Nothing else."
        )
        try:
            draft = groq_service._chat(
                groq_service.MODELS["saathi_chat"],
                [{"role": "system", "content": identity},
                 {"role": "user", "content": task}],
                temperature=1.0, max_tokens=140)
        except groq_service.GroqUnavailableError:
            return None
        draft = groq_service._strip_narration(draft)

    draft = (draft or "").strip().strip('"')
    if not draft or len(draft) > 400:
        return None

    # Same belts as a normal reply: mirroring, moderation, anti-repetition.
    correction = language_engine.violates(draft, style)
    if correction:
        # No re-roll here (this is background work, not a user waiting) — just
        # drop it. She will have another chance in ten minutes.
        logger.info("initiative draft dropped: language mismatch")
        return None
    if _is_repetitive(session, draft):
        return None
    if not groq_service._mock_mode():
        moderation = groq_service.moderate_content(draft)
        if moderation["flagged"] or not moderation["available"]:
            return None
    return draft


def _recent_openers(session, window: int = 8) -> str:
    """The first few words of her recent self-initiated messages, fed back as a
    do-not-repeat list. Verbatim repetition is what makes proactive messaging
    feel mechanical."""
    from app.models import SaathiMessage

    rows = (SaathiMessage.query
            .filter(SaathiMessage.session_id == session.id,
                    SaathiMessage.message_type.in_(("proactive", "initiative")))
            .order_by(SaathiMessage.created_at.desc()).limit(window).all())
    openers = [" ".join((r.content or "").split()[:4]) for r in rows]
    return "; ".join(f'"{o}"' for o in openers if o)


def _is_repetitive(session, draft: str, window: int = 20) -> bool:
    """Token-overlap dedupe against her recent self-initiated messages."""
    import re as _re

    from app.models import SaathiMessage

    def tokens(text: str) -> set[str]:
        return set(_re.findall(r"[a-z\u0900-\u097F]{3,}", (text or "").lower()))

    draft_tokens = tokens(draft)
    if not draft_tokens:
        return True
    rows = (SaathiMessage.query
            .filter(SaathiMessage.session_id == session.id,
                    SaathiMessage.message_type.in_(("proactive", "initiative")))
            .order_by(SaathiMessage.created_at.desc()).limit(window).all())
    for row in rows:
        overlap = draft_tokens & tokens(row.content)
        if len(overlap) / max(1, len(draft_tokens)) > 0.6:
            return True
    return False


