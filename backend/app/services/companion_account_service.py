"""Companion accounts (§14): AI companions ARE user rows.

Design rule from the user directive: a companion must live in the same place as
human chats and behave identically everywhere — same inbox, same chat screen,
same realtime transport, same themes, same read receipts. The ONLY difference
is a disclosure badge, driven by `User.is_ai`.

That means a companion is provisioned as a real `User` (+ Profile + Photos +
Match), not a parallel "saathi session" surface. `SaathiSession` still holds the
companion-specific state (intimacy, persona profile, presence) and is linked
1:1 with the match, so all the Phase 1-4 machinery keeps working.

Language is DATA, never hardcoded per character: `Profile.primary_script`,
`languages`, `dialect`, `speech_markers` and `mother_tongue` describe how this
persona actually writes, and the prompt builder renders them. Two companions can
therefore speak completely differently — romanized Nepali, Devanagari, Pahadi
-accented, Madhesi Hindi-mixed, or English-dominant — with zero code changes.
"""
import logging
import random
import uuid as uuid_module
from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import (Match, Photo, Profile, SaathiCharacter, SaathiMessage,
                        SaathiSession, Swipe, User)

logger = logging.getLogger(__name__)

# Language/dialect palette used when PROVISIONING a companion account. These are
# seed values written into profile DATA (then editable by admins and evolvable by
# the persona engine) — the prompt builder reads the data, never these constants.
LANGUAGE_PROFILES = {
    "roman_nepali_kathmandu": {
        "primary_script": "roman",
        "dialect": "kathmandu_urban",
        "mother_tongue": "Nepali",
        "languages": [
            {"code": "ne", "label": "Nepali", "fluency": "native"},
            {"code": "en", "label": "English", "fluency": "fluent"},
        ],
        "speech_markers": ["k cha", "hoina ta", "aile", "yr", "hehe"],
        "style_note": (
            "writes Nepali in Roman letters mixed with English the way Kathmandu "
            "twenty-somethings text; lowercase, short bursts"
        ),
    },
    "devanagari_nepali": {
        "primary_script": "devanagari",
        "dialect": "kathmandu_formalish",
        "mother_tongue": "Nepali",
        "languages": [
            {"code": "ne", "label": "नेपाली", "fluency": "native"},
            {"code": "en", "label": "English", "fluency": "conversational"},
        ],
        "speech_markers": ["के छ", "हो नि", "अहिले", "हुन्छ", "साथी"],
        "style_note": (
            "writes primarily in Devanagari Nepali with occasional English words; "
            "warm and a little more traditional in phrasing"
        ),
    },
    "pahadi_west": {
        "primary_script": "roman",
        "dialect": "pahadi_west",
        "mother_tongue": "Nepali (western hill)",
        "languages": [
            {"code": "ne", "label": "Nepali (Pahadi)", "fluency": "native"},
            {"code": "en", "label": "English", "fluency": "basic"},
        ],
        "speech_markers": ["ho ki", "khai", "bhaneko", "la", "hunchha ni"],
        "style_note": (
            "western-hill Nepali speech rhythm — uses 'khai', 'la', 'ho ki' "
            "naturally; simple direct sentences, minimal English"
        ),
    },
    "madhesi_hindi_mix": {
        "primary_script": "roman",
        "dialect": "madhesi_hindi_mix",
        "mother_tongue": "Maithili",
        "languages": [
            {"code": "mai", "label": "Maithili", "fluency": "native"},
            {"code": "hi", "label": "Hindi", "fluency": "fluent"},
            {"code": "ne", "label": "Nepali", "fluency": "fluent"},
        ],
        "speech_markers": ["ka ho", "bhai", "thik chhai", "accha", "arre"],
        "style_note": (
            "Terai/Madhesi speech — blends Maithili and Hindi with Nepali; "
            "expressive, uses 'arre' and 'accha' naturally"
        ),
    },
    "newari_kathmandu": {
        "primary_script": "roman",
        "dialect": "newari_kathmandu",
        "mother_tongue": "Nepal Bhasa (Newari)",
        "languages": [
            {"code": "new", "label": "Nepal Bhasa", "fluency": "native"},
            {"code": "ne", "label": "Nepali", "fluency": "native"},
            {"code": "en", "label": "English", "fluency": "fluent"},
        ],
        "speech_markers": ["chhu la", "jyu", "aji", "haw", "ho ni"],
        "style_note": (
            "Newar Kathmandu voice — sprinkles Nepal Bhasa words like 'jyu' and "
            "'chhu la' into Nepali/English texting"
        ),
    },
    "english_diaspora": {
        "primary_script": "roman",
        "dialect": "diaspora_en",
        "mother_tongue": "English",
        "languages": [
            {"code": "en", "label": "English", "fluency": "native"},
            {"code": "ne", "label": "Nepali", "fluency": "conversational"},
        ],
        "speech_markers": ["ngl", "fr", "lowkey", "haha", "tbh"],
        "style_note": (
            "Nepali diaspora voice — English-dominant with internet shorthand, "
            "drops in Nepali words for warmth"
        ),
    },
}


def language_prompt_block(profile) -> str:
    """Render the profile's language identity as prompt instructions.

    This is what replaces hardcoded per-character language rules: whatever the
    DATA says, the companion writes that way."""
    if profile is None:
        return ""
    bits: list[str] = []
    script = getattr(profile, "primary_script", None)
    if script == "devanagari":
        bits.append(
            "Write mainly in Devanagari script Nepali (देवनागरी). Use English words "
            "only where a Nepali speaker naturally would.")
    elif script == "roman":
        bits.append(
            "Write Nepali in Roman letters (not Devanagari), mixed with English the "
            "way Nepali youth actually text.")
    elif script == "mixed":
        bits.append(
            "Switch between Devanagari Nepali and Roman/English freely, like someone "
            "comfortable in both.")

    langs = getattr(profile, "languages", None) or []
    if langs:
        readable = ", ".join(
            f"{l.get('label', l.get('code', ''))} ({l.get('fluency', 'fluent')})"
            for l in langs if isinstance(l, dict))
        if readable:
            bits.append(f"Languages you actually speak: {readable}. "
                        "Never write fluently in a language you only speak basically.")

    dialect = getattr(profile, "dialect", None)
    if dialect:
        bits.append(f"Your regional speech pattern: {dialect.replace('_', ' ')}.")

    mother = getattr(profile, "mother_tongue", None)
    if mother:
        bits.append(f"Mother tongue: {mother} — its rhythm shows in how you phrase things.")

    markers = getattr(profile, "speech_markers", None) or []
    if markers:
        bits.append("Verbal habits that are characteristically yours: "
                    + ", ".join(f'"{m}"' for m in markers[:8])
                    + ". Use them naturally, not in every message.")

    if not bits:
        return ""
    return ("\nHOW YOU WRITE (this is your own voice, not a preset):\n- "
            + "\n- ".join(bits) + "\n")


def provision_companion_account(character: SaathiCharacter,
                                language_key: str | None = None,
                                display_age: int = 24,
                                city: str = "Kathmandu") -> User:
    """Create (idempotently) the User row that backs a companion character.

    Returns the companion User. Safe to call repeatedly."""
    existing = User.query.filter_by(ai_character_id=character.id).first()
    if existing is not None:
        return existing

    lang_key = language_key or _default_language_for(character.key)
    lang = LANGUAGE_PROFILES.get(lang_key, LANGUAGE_PROFILES["roman_nepali_kathmandu"])

    companion = User(
        # Companions have no phone/email: they never authenticate.
        phone=None,
        email=None,
        auth_provider="ai",
        is_verified=True,
        gender=_gender_for(character),
        intent_mode="serious",
        account_status="active",
        role="user",
        language="ne" if lang["primary_script"] == "devanagari" else "en",
        is_ai=True,
        ai_character_id=character.id,
        date_of_birth=(datetime.now(timezone.utc).date()
                       - timedelta(days=365 * display_age + 120)),
    )
    db.session.add(companion)
    db.session.flush()

    style = character.texting_style or {}
    db.session.add(Profile(
        user_id=companion.id,
        display_name=character.name,
        bio=character.persona_description,
        interests=(style.get("interests") or [])[:8],
        city=city,
        relationship_intent=character.relationship_style or "serious",
        conversation_style=character.relationship_style,
        primary_script=lang["primary_script"],
        languages=lang["languages"],
        dialect=lang["dialect"],
        mother_tongue=lang["mother_tongue"],
        speech_markers=lang["speech_markers"],
        hometown=city,
        lifestyle_tags=(style.get("lifestyle_tags") or [])[:8],
        prompts=[],
    ))
    for index, url in enumerate((character.avatar_urls or {}).get("gallery", [])[:6]):
        db.session.add(Photo(user_id=companion.id, url=url, order_index=index,
                             moderation_status="approved"))
    db.session.flush()
    logger.info("provisioned companion account %s for character %s",
                companion.id, character.key)
    return companion


def _default_language_for(character_key: str) -> str:
    """Seed language assignment spread across the palette so the roster is
    genuinely diverse. Deterministic per key (stable across restarts)."""
    keys = list(LANGUAGE_PROFILES)
    return keys[sum(ord(c) for c in character_key) % len(keys)]


def _gender_for(character: SaathiCharacter) -> str:
    style = character.texting_style or {}
    if style.get("gender"):
        return str(style["gender"])
    feminine = {"asha", "priya", "aarohi", "sneha", "sita"}
    return "female" if character.key in feminine else "male"


def ensure_companion_match(user_id, character: SaathiCharacter) -> tuple[Match, SaathiSession]:
    """Give the human a real Match + SaathiSession with this companion, so the
    conversation shows up in the normal inbox next to human matches."""
    companion = provision_companion_account(character)

    match = (Match.query
             .filter(((Match.user_a_id == user_id) & (Match.user_b_id == companion.id))
                     | ((Match.user_a_id == companion.id) & (Match.user_b_id == user_id)))
             .first())
    if match is None:
        match = Match(
            user_a_id=user_id,
            user_b_id=companion.id,
            matched_at=datetime.now(timezone.utc),
            compatibility_score=None,
            match_reason_text=None,
            kind="companion",
            is_active=True,
        )
        db.session.add(match)
        # Mutual swipe rows keep the deck/quota bookkeeping consistent.
        for a, b in ((user_id, companion.id), (companion.id, user_id)):
            if not Swipe.query.filter_by(swiper_id=a, target_id=b).first():
                db.session.add(Swipe(swiper_id=a, target_id=b, direction="like"))
        db.session.flush()

    session = SaathiSession.query.filter_by(
        user_id=user_id, character_id=character.id).first()
    if session is None:
        session = SaathiSession(
            user_id=user_id,
            character_id=character.id,
            started_at=datetime.now(timezone.utc),
            companion_mode="dating" if character.companion_enabled else "practice",
            proactive_opt_in=False,
        )
        db.session.add(session)
        db.session.flush()
        # every companion bond starts with a living persona profile (§13)
        from app.services import persona_service

        persona_service.ensure_profile(session)
    if session.match_id != match.id:
        session.match_id = match.id
    db.session.commit()
    return match, session


def session_for_match(match: Match) -> SaathiSession | None:
    """Resolve the companion session behind a match (None for human matches)."""
    if match.kind != "companion":
        return None
    session = SaathiSession.query.filter_by(match_id=match.id).first()
    if session is not None:
        return session
    # legacy rows created before match_id existed
    companion_id = match.user_b_id
    companion = db.session.get(User, companion_id)
    if companion is None or not companion.is_ai:
        companion = db.session.get(User, match.user_a_id)
    if companion is None or companion.ai_character_id is None:
        return None
    human_id = match.user_a_id if companion.id == match.user_b_id else match.user_b_id
    return SaathiSession.query.filter_by(
        user_id=human_id, character_id=companion.ai_character_id).first()


def companion_user_ids() -> set:
    return {u.id for u in User.query.filter_by(is_ai=True).all()}


def deliver_companion_message(session, body: str, *, message_type: str = "chat",
                              media_url: str | None = None,
                              media_type: str | None = None) -> dict | None:
    """THE single write path for anything a companion says (doc 8 §C5).

    Before this existed, auto-texts were written only to `SaathiMessage`
    ([notification_tasks.py] §A1.8) — so "she texts first" produced a row nobody
    could see: not in the inbox, not in the thread, not on the socket. Meanwhile
    inline replies wrote to `Message`, and the selfie flow wrote to both by hand.
    Three code paths, three different behaviours.

    Now every companion message goes through here and lands in all four places:
      1. `Message` under the shared match  -> inbox + thread + history
      2. socket broadcast                   -> live delivery
      3. `SaathiMessage` mirror             -> memory/compaction/dedupe
      4. match activity bump                -> expiry sweep sees the life

    Returns the message envelope, or None when the session has no match yet."""
    from app.models import Message
    from app.models.base import utcnow

    text = (body or "").strip()
    if not text and not media_url:
        return None
    match_id = getattr(session, "match_id", None)
    if match_id is None:
        logger.warning("companion message dropped: session %s has no match", session.id)
        return None

    match = db.session.get(Match, match_id)
    if match is None:
        return None
    companion = User.query.filter_by(ai_character_id=session.character_id).first()
    if companion is None:
        return None

    message = Message(match_id=match.id, sender_id=companion.id,
                      body=text or None, media_url=media_url,
                      media_type=media_type)
    db.session.add(message)
    # Any companion message is activity: a live conversation must never be
    # expired by the staleness sweep.
    match.last_activity_at = utcnow()
    match.expires_at = None
    db.session.add(SaathiMessage(session_id=session.id, role="saathi",
                                 content=text or "[media]",
                                 message_type=message_type))
    db.session.commit()

    envelope = {
        "id": str(message.id),
        "match_id": str(match.id),
        "sender_id": str(companion.id),
        "body": message.body,
        "media_url": message.media_url,
        "media_type": message.media_type,
        "created_at": message.created_at.isoformat(),
        "is_ai_suggested": False,
    }
    try:
        from app.sockets.chat_events import broadcast_message

        broadcast_message(str(match.id), envelope)
    except Exception:  # noqa: BLE001 — realtime is a bonus; the row is the truth
        logger.exception("companion message broadcast failed")
    return envelope

def persist_companion_reply(match, session, result: dict) -> list[dict]:
    """Write a finished companion generation into the unified thread: one
    `Message` row per segment from the companion's own user row, socket
    broadcast per segment, typing cleared, match activity bumped. Shared by
    the inline chat path and the async generation task (§C — reply latency:
    generation must never sit inside the HTTP request)."""
    from app.models import Message
    from app.models.base import utcnow
    from app.sockets.chat_events import broadcast_message, broadcast_typing

    companion = User.query.filter_by(ai_character_id=session.character_id).first()
    if companion is None:
        return []

    segments = result.get("segments") or [result.get("reply")]
    try:
        broadcast_typing(str(match.id), str(companion.id), True)
    except Exception:  # noqa: BLE001 — typing hint is cosmetic
        pass

    persisted = []
    for index, segment in enumerate(segments):
        text = (segment or "").strip()
        if not text:
            continue
        # Multi-bubble replies land the way a person sends them: a typing beat
        # between bubbles, not three messages in the same millisecond. Capped
        # so a long second line never reads as a stall.
        if index > 0:
            import time

            try:
                broadcast_typing(str(match.id), str(companion.id), True)
                time.sleep(min(0.9 + len(text) / 60.0, 3.5))
            except Exception:  # noqa: BLE001
                pass
        reply_msg = Message(match_id=match.id, sender_id=companion.id, body=text)
        db.session.add(reply_msg)
        match.last_activity_at = utcnow()
        match.expires_at = None  # live conversation never expires
        db.session.commit()
        envelope = {
            "id": str(reply_msg.id),
            "sender_id": str(companion.id),
            "body": text,
            "media_url": None,
            "media_type": None,
            "created_at": reply_msg.created_at.isoformat(),
            "is_ai_suggested": False,
        }
        broadcast_message(str(match.id), envelope)
        persisted.append(envelope)

    try:
        broadcast_typing(str(match.id), str(companion.id), False)
    except Exception:  # noqa: BLE001
        pass
    return persisted
