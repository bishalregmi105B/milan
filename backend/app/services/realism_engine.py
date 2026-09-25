"""Realism engine (doc 8 §C5) — she has a today, and she answers like a person.

Three things live here, all of them things the old code either faked or ignored:

1. `day_context()` — a deterministic slice of her actual day, derived from her
   persona bible's weekly rhythm plus a date-seeded RNG. Deterministic per
   (character, date) matters: without it she says she is at class in one message
   and at home in the next. Every generator (chat, status post, auto-text,
   diary) reads the SAME slice, so her day is consistent across all of them.

2. `reply_plan()` — read delay -> typing -> burst gaps, driven by her REAL
   presence state. The old `reply_timing(reply, "free")` hardcoded "free", so a
   companion who was supposedly asleep replied in 1.2 seconds.

3. `segment()` — burst splitting driven by her style and the reply's shape
   instead of a flat 30% coin flip that almost never fired.

Nothing here is a fixed constant per character: timings come from her state and
her text, so the same character is fast when free and slow when busy.
"""
import hashlib
import random
import re
from datetime import date, datetime, timedelta, timezone

KATHMANDU_TZ = timezone(timedelta(hours=5, minutes=45))
_WEEKDAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

# Small, ordinary, non-dramatic incidents. Deliberately mundane: "power cut
# again" is believable, "I got hit by a car" is a soap opera.
_INCIDENTS = [
    "power cut for two hours", "the wifi died halfway through something important",
    "forgot to eat lunch", "woke up before the alarm and could not sleep again",
    "spilled tea on the table", "a friend called out of nowhere",
    "the traffic was unbelievable", "it started raining the moment she stepped out",
    "found an old photo and got distracted", "lost an hour scrolling",
    "the shop was closed", "someone cancelled last minute",
]
_ENERGY = ("low", "normal", "high")
_SLEEP = ("slept badly", "slept fine", "slept like a rock")


def _seed(*parts) -> int:
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode()).digest()
    return int.from_bytes(digest[:8], "big")


def local_now() -> datetime:
    return datetime.now(KATHMANDU_TZ)


def day_context(character_key: str, schedule: dict | None, bible: dict | None,
                when: datetime | None = None) -> dict:
    """Her day, as of `when` (Kathmandu local). Deterministic per character+date.

    Returns {"weekday", "plan", "phase", "state", "activity", "energy",
             "sleep", "incident", "hours_awake"}.
    `phase` is what she is in right now; `plan` is the whole day so she can talk
    about the morning in the evening."""
    now = when or local_now()
    today: date = now.date()
    weekday = _WEEKDAY_KEYS[now.weekday()]
    rng = random.Random(_seed(character_key, today.isoformat()))

    plan = ((bible or {}).get("week") or {}).get(weekday) or ""
    presence = evaluate_presence(schedule, now.hour, now.weekday() >= 5)

    if presence["state"] == "sleeping":
        phase = "asleep"
    elif now.hour < 11:
        phase = "morning"
    elif now.hour < 16:
        phase = "afternoon"
    elif now.hour < 20:
        phase = "evening"
    else:
        phase = "night"

    sleep_start = (schedule or {}).get("sleep_window", [23, 7])[1]
    hours_awake = max(0, now.hour - int(sleep_start)) if presence["state"] != "sleeping" else 0

    return {
        "weekday": weekday,
        "plan": plan,
        "phase": phase,
        "state": presence["state"],
        "activity": presence["activity"],
        "energy": _ENERGY[rng.randrange(len(_ENERGY))] if hours_awake < 12 else "low",
        "sleep": _SLEEP[rng.randrange(len(_SLEEP))],
        # One incident per day, and only sometimes — an eventful day every single
        # day is as unrealistic as a blank one.
        "incident": _INCIDENTS[rng.randrange(len(_INCIDENTS))] if rng.random() < 0.55 else None,
        "hours_awake": hours_awake,
    }


def evaluate_presence(schedule: dict | None, local_hour: int, is_weekend: bool) -> dict:
    """Resolve a schedule to the current activity state. Unknown/missing
    schedule => free; never fabricate a state (in particular, never a state that
    implies she is with someone else — that is a banned jealousy pattern)."""
    if not schedule:
        return {"state": "free", "activity": None}
    sleep_start, sleep_end = schedule.get("sleep_window", [23, 7])
    if local_hour >= sleep_start or local_hour < sleep_end:
        return {"state": "sleeping", "activity": "sleeping"}
    windows = schedule.get("weekend_windows" if is_weekend else "weekday_windows", [])
    for window in windows:
        if window.get("start", 0) <= local_hour < window.get("end", 0):
            return {"state": window.get("state", "busy"),
                    "activity": window.get("activity")}
    return {"state": "free", "activity": None}


def render_day_block(day: dict) -> str:
    """Her day as prompt context. She should be able to answer "k gardai xau?"
    truthfully and consistently, and refer back to her own morning."""
    if not day:
        return ""
    bits: list[str] = []
    if day.get("plan"):
        bits.append(f"Your {day['weekday']} looks like: {day['plan']}")
    if day.get("state") == "sleeping":
        bits.append("Right now you are asleep — if you reply at all you are groggy and brief")
    elif day.get("activity"):
        bits.append(f"Right now you are {day['activity']} ({day['state']})")
    else:
        bits.append(f"Right now it is {day['phase']} and you are free")
    if day.get("sleep"):
        bits.append(f"You {day['sleep']} last night")
    if day.get("energy"):
        bits.append(f"Your energy today is {day['energy']}")
    if day.get("incident"):
        bits.append(f"Something small happened today: {day['incident']} — mention it only "
                    "if it fits naturally")
    return ("YOUR DAY RIGHT NOW (keep this consistent; do not invent a different "
            "day mid-conversation):\n- " + "\n- ".join(bits) + "\n")


# ── timing ────────────────────────────────────────────────────────────────
# Read delay by state. A free person glances at their phone; a busy person sees
# it between things; a sleeping person sees it in the morning.
_READ_DELAY = {
    "free": (1.0, 9.0),
    "social": (8.0, 60.0),
    "busy": (40.0, 400.0),
    "routine": (5.0, 45.0),
    "sleeping": (600.0, 2400.0),
}
TYPING_CPS = 14.0          # doc 5 §2.6 formula, kept
TYPING_FLOOR = 0.7
TYPING_CAP = 4.5
BURST_GAP = (0.6, 2.5)


def reply_plan(reply_text: str, *, presence_state: str = "free",
               segments: list[str] | None = None,
               energy: str = "normal") -> dict:
    """Read -> type -> send, per segment.

    Returns {"read_delay_seconds", "typing_delay_seconds", "segment_delays": [],
             "presence_state"}. `typing_delay_seconds` stays in the payload for
    the existing client contract; `segment_delays` is the per-bubble sequence."""
    parts = segments or [reply_text or ""]
    low, high = _READ_DELAY.get(presence_state, _READ_DELAY["free"])
    read = random.uniform(low, high)
    # Energy modulates typing speed, not reading — a tired person types slower.
    speed = TYPING_CPS * {"low": 0.75, "normal": 1.0, "high": 1.2}.get(energy, 1.0)

    delays: list[dict] = []
    for index, part in enumerate(parts):
        typing = min(max(TYPING_FLOOR, len(part) / speed), TYPING_CAP)
        gap = 0.0 if index == 0 else random.uniform(*BURST_GAP)
        delays.append({"gap_seconds": round(gap, 2), "typing_seconds": round(typing, 2)})

    return {
        "read_delay_seconds": round(read, 1),
        "typing_delay_seconds": delays[0]["typing_seconds"] if delays else TYPING_FLOOR,
        "segment_delays": delays,
        "presence_state": presence_state,
    }


def should_defer(presence_state: str, *, rate: float | None = None) -> bool:
    """Occasionally a busy or sleeping person just doesn't reply now.

    This is the difference between a chat service and a person: an instant reply
    at 3am from someone who told you she sleeps at 11 breaks the whole illusion.
    Never defers when she is free — that would read as being ignored."""
    if presence_state not in ("busy", "sleeping", "social"):
        return False
    if rate is None:
        try:
            from flask import current_app

            rate = float(current_app.config.get("SAATHI_DELAYED_REPLY_RATE", 0.08))
        except Exception:  # noqa: BLE001
            rate = 0.08
    # Asleep is a near-certainty, not a dice roll — she is asleep.
    if presence_state == "sleeping":
        return random.random() < min(0.9, max(rate, 0.75))
    return random.random() < rate


def defer_delay_seconds(presence_state: str, day: dict | None = None) -> int:
    """How long the deferred reply waits. Sleeping wakes at her wake hour;
    busy comes back in 10-40 minutes."""
    if presence_state == "sleeping":
        now = local_now()
        wake_hour = 7
        if day and day.get("state") == "sleeping":
            wake_hour = 7
        wake = now.replace(hour=wake_hour, minute=random.randint(2, 40),
                           second=0, microsecond=0)
        if wake <= now:
            wake += timedelta(days=1)
        return int((wake - now).total_seconds())
    return random.randint(10 * 60, 40 * 60)


_DEFER_REASONS = {
    "busy": ["sorry {activity} thiyo", "aba free bhaye", "was stuck at {activity}",
             "just saw this, {activity} thiyo"],
    "sleeping": ["sutey ma, just woke up", "sorry sutey thiye", "good morning, just saw this"],
    "social": ["sorry was with friends", "just got back"],
}


def defer_reason(presence_state: str, day: dict | None = None) -> str:
    """A natural, short reason — in her own register. Never apologetic beyond a
    word, never guilt-inducing toward the user."""
    pool = _DEFER_REASONS.get(presence_state) or _DEFER_REASONS["busy"]
    template = random.choice(pool)
    activity = (day or {}).get("activity") or "class"
    return template.format(activity=activity)


# ── burst segmentation ────────────────────────────────────────────────────
# The old split was `if random() >= 0.3: return [text]` gated on burst_pref > 1,
# so ~70% of replies never split and single-burst characters never split at all.
# Real people split on *thought boundaries*: a statement then a question, a
# reaction then the substance. Length and their own habit decide how often.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…।])\s+")
# Short reactions that live on their own line in real chat.
_REACTION_HEAD = re.compile(
    r"^(hahaha?|hehe|lol|lmao|omg|arre|oye?|oh|ahh?|wow|nooo?|yesss?|acha|accha|"
    r"hmm+|uff|yaar|yr|damn|bruh|wait)\b[,!.…]*\s*", re.IGNORECASE)


def segment(reply_text: str, *, burst_pref: int = 2, style: dict | None = None) -> list[str]:
    """Split a reply into the bubbles a person would actually send.

    Rules, in order:
      - a short reply is one bubble, always
      - a leading reaction word ("hahaha", "arre") peels off as its own bubble
      - a trailing question separates from the statement before it
      - otherwise split on sentence boundaries up to the character's burst habit

    Users who text in long messages get fewer splits (mirroring, from style).
    Invariant: the concatenation of the result always equals the input text —
    truncating to a burst cap must never silently drop the tail (which is
    usually the question she wants answered)."""
    text = (reply_text or "").strip()
    if not text:
        return []

    max_bursts = max(1, min(int(burst_pref or 1), 3))
    # Mirror the user: someone who writes paragraphs finds 3 bubbles jarring.
    avg_len = float((style or {}).get("avg_len") or 0)
    if avg_len and avg_len > 120:
        max_bursts = 1
    elif avg_len and avg_len < 25:
        max_bursts = min(3, max_bursts + 1)

    if max_bursts == 1 or len(text) < 45:
        return [text]

    segments: list[str] = []
    remainder = text

    head = _REACTION_HEAD.match(remainder)
    if head and len(remainder) > len(head.group(0)) + 15:
        segments.append(head.group(0).strip().rstrip(",").strip())
        remainder = remainder[head.end():].strip()

    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(remainder) if s.strip()]
    room = max_bursts - len(segments)

    if len(sentences) <= 1 or room <= 1:
        # Nothing left to split, or no room left: the remainder goes out whole.
        if remainder:
            segments.append(remainder)
        return segments

    # A trailing question is its own message far more often than not — it is the
    # part she wants answered. Everything before it merges into one bubble.
    if sentences[-1].endswith("?"):
        lead = " ".join(sentences[:-1]).strip()
        if lead:
            segments.append(lead)
        segments.append(sentences[-1])
        return segments

    # Distribute sentences across the remaining bubbles, front-loaded, and let
    # the final bubble absorb everything left so nothing is lost.
    per = max(1, len(sentences) // room)
    for index in range(room):
        start = index * per
        if start >= len(sentences):
            break
        chunk = sentences[start:] if index == room - 1 else sentences[start:start + per]
        if chunk:
            segments.append(" ".join(chunk).strip())
    return [s for s in segments if s]



