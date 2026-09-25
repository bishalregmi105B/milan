import logging
import re

from app.extensions import db
from app.models import ModerationEvent, ScamFlag
from app.services import groq_service

logger = logging.getLogger(__name__)

# Deterministic lexical belt — always runs, even when the AI moderator is
# down (Nepali romanized + English + Hindi hard-blocks; transliteration-tolerant
# patterns, not exhaustive dictionaries — the AI pass remains the deep belt).
HARD_BLOCK_PATTERNS = [
    r"\bra[nw]di\b", r"\bchik[-_ ]?ne\b", r"\bbhosad", r"\bmaa ?chud",
    r"\bbhen ?chod", r"\bb[-_ ]?k[-_ ]?b?c\b", r"\bra[nw]a\b.{0,6}di\b",
    r"\btatto?ke?\b", r"\bm[u]?ji\b", r"\bsutta\b.{0,3}\bmar\b",
    r"\bf[u*]ck (yo)?u*r? (mother|sister)\b",
    r"\bfuck off and die\b", r"\bkys\b", r"\bi (will|wanna) (find|kill) you\b",
    r"\bghare ?auni\b", r"\bkalo\b.{0,4}\bmui\b",
]

_LEXICAL_RE = [re.compile(p, re.IGNORECASE) for p in HARD_BLOCK_PATTERNS]


def _lexical_hard_block(text: str) -> bool:
    if not text:
        return False
    from app.services import text_filter

    if any(rx.search(text) for rx in _LEXICAL_RE):
        return True
    # doc 8 §C2: the shared offline filter widens the belt (normalised
    # variants, Devanagari, English slurs) without duplicating the list here.
    return text_filter.hard_block(text)


def screen_inbound_message(text: str) -> dict:
    """Synchronous fast pass run before any chat message is broadcast (doc 4 §4).
    The lexical belt blocks hard-abuse terms deterministically; the AI pass
    covers everything subtler and defers gracefully when unavailable."""
    if _lexical_hard_block(text):
        return {"flagged": True, "categories": ["harassment"], "deferred": False}
    result = groq_service.moderate_content(text)
    if not result.get("available"):
        logger.warning("sync moderation unavailable; deferring to async scan")
        return {"flagged": False, "categories": [], "deferred": True}
    return {"flagged": result["flagged"], "categories": result["categories"], "deferred": False}


def scan_message_deep(text: str, *, message_id=None, match_id=None, sender_id=None) -> dict:
    """Slower async re-scan: deeper policy pass + scam-pattern classification."""
    moderation = groq_service.moderate_content(text)
    scam = groq_service.classify_scam_pattern(text)

    if scam.get("risk") in ("low", "high"):
        flag = ScamFlag(
            message_id=message_id,
            match_id=match_id,
            flagged_user_id=sender_id,
            pattern_matched=scam.get("categories", []),
            confidence=0.9 if scam.get("risk") == "high" else 0.6,
            risk_level=scam["risk"],
        )
        db.session.add(flag)
        db.session.add(ModerationEvent(
            subject_type="message",
            subject_id=message_id,
            source="scam_classifier",
            action="flagged",
            categories=scam.get("categories", []),
            details={"risk": scam.get("risk")},
        ))
    if moderation.get("flagged"):
        db.session.add(ModerationEvent(
            subject_type="message",
            subject_id=message_id,
            source="llama_guard_async",
            action="flagged",
            categories=moderation.get("categories", []),
        ))
    db.session.commit()
    return {"moderation": moderation, "scam": scam}


def moderate_media_asset(*, subject_type: str, subject_id, media_url: str, user_id=None) -> str:
    """Moderation gate for uploaded media (profile photos, reels, custom wallpapers).
    Returns the new moderation_status. Private wallpapers are still moderated (doc 4 §8)."""
    from app.models import Photo, Reel, WallpaperUpload

    result = groq_service.moderate_content(f"[media asset] {media_url}")
    status = "approved"
    if result.get("flagged"):
        status = "rejected"
    elif not result.get("available"):
        status = "pending"

    if subject_type == "photo":
        row = db.session.get(Photo, subject_id)
    elif subject_type == "reel":
        row = db.session.get(Reel, subject_id)
    elif subject_type == "wallpaper":
        row = db.session.get(WallpaperUpload, subject_id)
    else:
        row = None
    if row is not None:
        row.moderation_status = status
        db.session.add(ModerationEvent(
            subject_type=subject_type,
            subject_id=subject_id,
            source="media_moderation",
            action=status,
            categories=result.get("categories", []),
        ))
        db.session.commit()
    return status


def record_admin_action(subject_type: str, subject_id, action: str, actor_id, note: str | None = None):
    db.session.add(ModerationEvent(
        subject_type=subject_type,
        subject_id=subject_id,
        source="admin_dashboard",
        action=action,
        actor_id=actor_id,
        details={"note": note} if note else None,
    ))
    db.session.commit()
