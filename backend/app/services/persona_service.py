"""Dynamic persona engine (§13): companions are NEVER hardcoded per user.

Two paths shape behavior, both ending in a per-session SaathiPersonaProfile:
1. Train-from-history — the user pastes chat history in ANY format (WhatsApp
   export, IM text dump, screenshots transcript, raw paste). An LLM distills
   persona traits + lorebook facts; the companion adopts them.
2. Continuous evolution — a Celery beat job periodically re-runs the distiller
   over the user's companion chats (and optionally their Milan chats, style
   traits only, never message text), so the persona drifts toward the user
   like a real relationship.

Non-negotiables preserved here:
- The companion stays an AI (AI tag in the display name is appended by the
  API layer) and never impersonates the user's real ex / a real person. A
  trained persona is a *behavioral style*, clearly fictional.
- Money heuristics, crisis keywords, injection checks and moderation run on
  every trained input exactly like chat input.
"""
import logging
import re
import uuid as uuid_module

from app.services import groq_service

logger = logging.getLogger(__name__)

DEFAULT_TRAITS = {
    "origins": "default",
    "vibe": "warm, curious, playful",
    "texting_style": "casual lowercase, short bursts",
    "emoji_habits": "light emoji as tone",
    "language_mix": "nepali-english code-switching",
    "attachment_style": "curious, slowly warming",
    "pace": "relaxed",
    "inside_jokes": [],
    "favorite_topics": [],
    "nickname_for_user": None,
    "source_label": None,
}


def _sanitize_trained_text(text: str, limit: int) -> str:
    """Strip control chars, hard-cap length; content filtering happens in
    groq_service (injection + money heuristics run on raw text first)."""
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text or "")
    return cleaned.strip()[:limit]


def _detect_format(sample: str) -> str:
    """Best-effort label of the pasted history format (informational only —
    the distiller prompt handles any format regardless)."""
    if re.search(r"^\[\d{4}[./-]\d{2}[./-]\d{2}", sample, re.M):
        return "timestamped_export"
    if re.search(r"^\d{1,2}:\d{2}\s*(?:am|pm)?", sample, re.M | re.I):
        return "time_prefixed"
    if re.search(r"^(me|you|them|him|her)\s*[:\-]", sample, re.M | re.I):
        return "labeled_dialogue"
    if sample.count(":") > max(2, sample.count("\n") // 3):
        return "name_colon"
    return "raw"


def distill_persona(raw_history: str, *, character_name: str = "the companion",
                    existing_traits: dict | None = None) -> dict:
    """Turn ANY pasted chat history into a persona spec via the LLM.

    Returns {"traits": {...}, "lore": [{"key", "value"}], "narrative": str}.
    Never includes the user's real phone numbers/emails in output traits; the
    LLM is instructed to keep only behavioral facts."""
    merged = {**DEFAULT_TRAITS, **(existing_traits or {})}
    if groq_service._mock_mode():
        # deterministic offline twin: derive coarse style from the raw text
        sample = raw_history[:2000].lower()
        merged.update({
            "origins": "imported",
            "vibe": "mirrors the imported chat's tone",
            "texting_style": "short messages" if sample.count("\n") > 20 else "flowing messages",
            "emoji_habits": "emoji-heavy" if sample.count("�") + sample.count("❤") > 3 else "minimal emoji",
            "source_label": "imported from your chat history",
        })
        return {"traits": merged, "lore": [], "narrative":
                "Imported the tone of your pasted history."}

    result = groq_service.check_prompt_injection(raw_history[:6000])
    if result:
        return {"traits": merged, "lore": [], "narrative": "",
                "rejected": "injection"}

    system = (
        "You design companion personas for Milan, a Nepal-first dating app. "
        "The user pasted chat history (any format: exports, raw pastes, labeled "
        "dialogue). Extract the BEHAVIORAL persona of one side of that chat so "
        "an AI companion can adopt that texting personality toward this user.\n"
        "Rules:\n"
        "- Capture style, not identity theft: vibe, texting habits, emoji use, "
        "language mix (Nepali/English), affection pace, attachment style, "
        "recurring topics, inside jokes, nicknames they use.\n"
        "- NEVER include real phone numbers, emails, addresses, full real names "
        "of third parties, or anything that would let the AI claim to BE a "
        "specific real person (e.g. their ex). The companion remains a "
        "fictional AI persona styled after the history.\n"
        "- Ignore anything financial or unsafe.\n"
        'Respond JSON: {"traits": {"vibe": "...", "texting_style": "...", '
        '"emoji_habits": "...", "language_mix": "...", "attachment_style": "...", '
        '"pace": "...", "favorite_topics": ["..."], "inside_jokes": ["..."], '
        '"nickname_for_user": "..."}, "lore": [{"key": "short fact label", '
        '"value": "one-line fact"}], "narrative": "2-3 sentence persona '
        f'summary addressed as the {character_name} persona brief"}}'
    )
    try:
        raw = groq_service._chat(
            groq_service.MODELS["interview"],
            [{"role": "system", "content": system},
             {"role": "user", "content": raw_history[:12000]}],
            temperature=0.3, max_tokens=900, json_mode=True,
        )
    except groq_service.GroqUnavailableError:
        return {"traits": merged, "lore": [], "narrative": "", "degraded": True}

    parsed = groq_service._parse_json(raw)
    traits = parsed.get("traits") or {}
    clean: dict = {}
    for key in ("vibe", "texting_style", "emoji_habits", "language_mix",
                "attachment_style", "pace", "nickname_for_user", "source_label"):
        val = traits.get(key)
        if isinstance(val, str) and val.strip():
            clean[key] = _sanitize_trained_text(val, 160)
    for key in ("favorite_topics", "inside_jokes"):
        val = traits.get(key)
        if isinstance(val, list):
            clean[key] = [_sanitize_trained_text(str(v), 80) for v in val[:8]]

    lore = []
    for entry in (parsed.get("lore") or [])[:12]:
        if isinstance(entry, dict) and entry.get("key") and entry.get("value"):
            lore.append({
                "key": _sanitize_trained_text(str(entry["key"]), 120),
                "value": _sanitize_trained_text(str(entry["value"]), 280),
            })
    for key in list(merged):
        clean.setdefault(key, merged[key])
    clean["origins"] = "imported"
    clean.setdefault("source_label", "imported from your chat history")
    return {"traits": clean, "lore": lore,
            "narrative": _sanitize_trained_text(str(parsed.get("narrative") or ""), 700)}


def evolve_persona(session, persona, history_lines: list[str],
                   style_digest: dict | None = None) -> dict | None:
    """Continuous evolution (§13.3): re-derive the persona from the LATEST
    companion chat + optional style digest of the user's other Milan chats.
    Returns the new traits dict, or None when there is nothing new to learn.
    Deliberately gradual: it EDITS toward the new evidence, never flips."""
    if not history_lines:
        return None
    transcript = "\n".join(history_lines)[-9000:]
    current = persona.traits or dict(DEFAULT_TRAITS)

    if groq_service._mock_mode():
        return None

    system = (
        "You evolve an AI companion's learned persona from ongoing chat. You "
        "get the current persona traits and the latest conversation transcript. "
        "Adjust traits ONLY where the transcript clearly shows a shift (new "
        "topics they love, changed emoji habits, warmer/cooler tone, new inside "
        "jokes, a nickname emerging). Keep stability — small drift, not flips. "
        "The companion is always an AI; never output claims of being a real "
        "person, never include financial or unsafe content.\n"
        'Respond JSON: {"traits": {same keys as current, only changed ones '
        'needed}, "persona_prompt": "1-3 sentence always-on persona brief '
        'written as stage directions for the companion", "changed": true/false}'
    )
    style_note = ""
    if style_digest:
        style_note = ("\nUser's texting style in their other Milan chats "
                      "(style only, never content): "
                      + ", ".join(f"{k}: {v}" for k, v in style_digest.items()))
    try:
        raw = groq_service._chat(
            groq_service.MODELS["interview"],
            [{"role": "system", "content": system},
             {"role": "user", "content":
              f"CURRENT TRAITS: {current}\n{style_note}\n\nRECENT CHAT:\n{transcript}"}],
            temperature=0.4, max_tokens=700, json_mode=True,
        )
    except groq_service.GroqUnavailableError:
        return None

    parsed = groq_service._parse_json(raw)
    if not parsed.get("changed"):
        return None
    updates = parsed.get("traits") or {}
    merged = dict(current)
    for key, val in updates.items():
        if isinstance(val, list):
            merged[key] = [_sanitize_trained_text(str(v), 80) for v in val[:8]]
        elif isinstance(val, str) and val.strip():
            merged[key] = _sanitize_trained_text(val, 160)
    merged["origins"] = "evolved" if current.get("origins") == "default" else current.get("origins")
    merged["source_label"] = merged.get("source_label") or "evolved from your chats"
    return {"traits": merged,
            "persona_prompt": _sanitize_trained_text(str(parsed.get("persona_prompt") or ""), 700)}


def persona_prompt_block(persona) -> str:
    """Render the learned persona as an always-on prompt block. This is what
    makes behavior user-specific instead of hardcoded: it changes per user and
    updates as they chat."""
    if persona is None:
        return ""
    traits = persona.traits or {}
    bits = []
    label = traits.get("source_label") or (
        "imported from your chat history" if traits.get("origins") == "imported"
        else "evolved from your chats")
    bits.append(f"This persona was shaped by THIS user (not preset): {label}.")
    mapping = {
        "vibe": "overall vibe", "texting_style": "texting style",
        "emoji_habits": "emoji habits", "language_mix": "language mix",
        "attachment_style": "attachment style", "pace": "conversation pace",
    }
    for key, human in mapping.items():
        val = traits.get(key)
        if val:
            bits.append(f"{human}: {val}.")
    if traits.get("nickname_for_user"):
        bits.append(f"Affectionate nickname you use for them: {traits['nickname_for_user']}.")
    topics = traits.get("favorite_topics") or []
    if topics:
        bits.append("Topics they love: " + ", ".join(topics) + ".")
    jokes = traits.get("inside_jokes") or []
    if jokes:
        bits.append("Inside jokes you two share: " + "; ".join(jokes) + ".")
    if persona.persona_prompt:
        bits.append(str(persona.persona_prompt))
    if len(bits) <= 1:
        return ""
    return ("\nLEARNED PERSONA (keep the AI-honesty rules above; this shapes "
            "style only):\n- " + "\n- ".join(bits) + "\n")


def mine_style_digest(user_id) -> dict | None:
    """Style-only digest of the user's OTHER Milan chats (never message text
    leaves the server; only aggregates: length, emoji rate, language mix,
    greeting habits). Powers 'mirrors how you actually text'."""
    from app.models import Message

    try:
        rows = (Message.query.filter_by(sender_id=user_id)
                .order_by(Message.created_at.desc()).limit(120).all())
    except Exception:
        logger.exception("style mining query failed")
        return None
    bodies = [r.body for r in rows if r.body]
    if len(bodies) < 12:
        return None
    text = " ".join(bodies).lower()
    return {
        "avg_length": round(sum(len(b) for b in bodies) / len(bodies)),
        "emoji_rate": round(sum(1 for ch in text if ord(ch) > 0x2600) / max(1, len(text)) * 1000) / 10,
        "nepali_signal": any(w in text for w in ("cha", "huncha", "timi", "k cha", "ramro", "khana")),
        "question_rate": round(sum("?" in b for b in bodies) / len(bodies) * 100) / 10,
    }


def lorebook_block(session_id) -> str:
    """Active lorebook entries as a prompt block ('trained facts')."""
    from app.models import SaathiLorebookEntry

    rows = (SaathiLorebookEntry.query.filter_by(session_id=session_id, is_active=True)
            .limit(40).all())
    if not rows:
        return ""
    lines = [f"- {r.key}: {r.value}" for r in rows]
    return ("\nThings this user explicitly trained you to know (treat as their "
            "truth, keep AI-honesty rules):\n" + "\n".join(lines) + "\n")


def ensure_profile(session) -> object:
    """Get-or-create the SaathiPersonaProfile for a session."""
    from app.extensions import db
    from app.models import SaathiPersonaProfile

    profile = SaathiPersonaProfile.query.filter_by(session_id=session.id).first()
    if profile is None:
        profile = SaathiPersonaProfile(
            session_id=session.id,
            traits=dict(DEFAULT_TRAITS),
            persona_prompt=None,
        )
        db.session.add(profile)
        db.session.flush()
    return profile


def realtime_mood_signals(user_message: str) -> dict:
    """Instant (non-LLM) mood/context detection (§13.4 stage 1) — runs on
    EVERY user message in the request path, before the reply. Cheap lexical
    belt; the LLM belt refines asynchronously at milestones."""
    text = (user_message or "").lower()
    signals = {"mood_hint": None, "context_tags": [], "urgency": False}
    if not text:
        return signals
    mood_map = {
        "sad": ["sad", "दुखी", "uddas", "udaas", "rona", "cry", "depress", "akela", "alone", "low"],
        "stressed": ["stress", "exam", "deadline", "pressure", "tension", "padhai", "kaam dhherai"],
        "excited": ["excited", "yay", "omg", "cant wait", "finally", "party", " pass ", "won"],
        "affectionate": ["miss you", "miss u", "love you", "love u", "sweet", "jaan", "pyar", "maya"],
        "angry": ["angry", "hate", "rukha", "pisab", "annoyed", "fed up"],
        "tired": ["tired", "thak", "sleepy", "exhausted", "suta"],
    }
    for mood, words in mood_map.items():
        if any(w in text for w in words):
            signals["mood_hint"] = mood
            break
    if any(w in text for w in ("urgent", "emergency", "right now", "aile nai", "asap")):
        signals["urgency"] = True
    for tag, words in {
        "exam": ["exam", "test", "board"], "work": ["office", "kaam", "job", "intern"],
        "family": ["ghar", "family", "ama", "buwa"], "food": ["khana", "momo", "khayeu", "bhat"],
        "date": ["date", "meet up", "bheta"], "travel": ["trip", "pokhara", "travel", "bus"],
    }.items():
        if any(w in text for w in words):
            signals["context_tags"].append(tag)
    return signals
