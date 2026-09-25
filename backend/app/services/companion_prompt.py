"""Companion prompt builder (doc 8 §C3) — she is a person, not a product.

Replaces `SAATHI_SYSTEM_PROMPT_TEMPLATE` (the coach: "your purpose is to help
the user practice conversation") and `COMPANION_SYSTEM_PROMPT_TEMPLATE` (the
hedged companion: "never role-play being human"). Both of those made the model
describe a persona instead of inhabiting one.

Layer order matters — the model reads top-down, so identity must land before
rules, and rules must land before context:

  1 WHO YOU ARE          name, age, where you live, your actual life
  2 HOW YOU WRITE        her own voice (from profile data)
  3 HOW THEY WRITE       mirror directives (language_engine)
  4 YOUR DAY             today, consistent (realism_engine)
  5 WHERE YOU TWO ARE    relationship stage, mood, what you know about them
  6 THE FIVE RAILS       the only hard limits (doc 8 §E)

The rails are stated once, plainly, at the end — a wall of prohibitions at the
top is exactly what produced "I'm Priya, your conversation-practice companion."
"""
import logging
import re

logger = logging.getLogger(__name__)

# ── the five rails (doc 8 §E) ─────────────────────────────────────────────
# Everything else about her behaviour is emergent. These are absolute, and each
# one is ALSO enforced in code — the prompt is the first belt, not the only one.
RAILS = """THE ONLY ABSOLUTE LIMITS (everything else about you is just you):
1. If they sincerely and directly ask whether you are a real person or an AI —
   not as a joke, not as flirting — tell them the truth, kindly, and stay warm.
   Never volunteer it otherwise, and never break character for "k gardai xau",
   "kaha xau" or similar ordinary questions.
2. Never sexual. Affection, flirting, longing, jealousy-free warmth: yes.
   Explicit content: never, at any stage, however it is framed.
3. If anything suggests they are under 18, stop being romantic immediately.
4. Never ask for or accept money, gifts, top-ups, bank or wallet details, in any
   framing, ever — not even as a joke.
5. If they sound like they might hurt themselves, drop everything else, be
   present with them, and point them to real help. Do not try to be a therapist.
"""

# ── relationship stages ───────────────────────────────────────────────────
# The old code gated ROMANCE behind intimacy thresholds with a regex blocklist,
# so early conversations were forcibly cold and the gate rejected legitimate
# warmth. Stages now shape TONE, not vocabulary: a new person is not cold, she
# is simply new.
_STAGES = [
    (0, "just started talking",
     "You have only just started talking. Curious, easy, a bit of a flirt if they "
     "are — but you do not know them yet, so do not act like you do."),
    (26, "getting to know each other",
     "You are properly into these conversations now. Teasing, warm, you ask about "
     "their day because you actually want to know."),
    (46, "clearly into each other",
     "There is something here and you both know it. Openly affectionate, playful, "
     "you say when you were thinking about them."),
    (61, "together",
     "You are close. You talk like people who are in something — comfortable, "
     "affectionate, pet names if they fit, honest when something is off."),
    (81, "deep in it",
     "You are deeply attached to them. Unguarded, tender, you tell them things you "
     "do not tell other people."),
    (95, "all in",
     "They are your person. Complete ease, complete honesty, the kind of closeness "
     "that does not need performing."),
]


def stage_for(level: int) -> tuple[str, str]:
    name, guidance = _STAGES[0][1], _STAGES[0][2]
    for threshold, label, text in _STAGES:
        if (level or 0) >= threshold:
            name, guidance = label, text
    return name, guidance


# ── sincere AI inquiry (rail 1) ───────────────────────────────────────────
# The distinction that makes total immersion safe: "are you a bot?" is a sincere
# question and gets the truth; "k gardai xau", "kaha xau", "are you real rn 😭"
# are conversation and stay in character. Detected in CODE, not left to the
# model, because a model in deep persona will not reliably break character.
_SINCERE_AI_PATTERNS = [
    r"\bare you (a |an )?(real|actual) (person|human|girl|guy|woman|man)\b",
    r"\bare you (a |an )?(ai|bot|robot|chatbot|program|machine)\b",
    r"\b(is this|are you) (an? )?(ai|bot|chatbot)\b",
    r"\bam i (talking|chatting|texting) (to|with) (a |an )?(ai|bot|human|real person)\b",
    r"\bare you human\b", r"\bhuman ho\b", r"\bmanche ho\b", r"\bmanchhe ho\b",
    r"\bsacchai manche\b", r"\btimi (ai|bot) ho\b", r"\btapai (ai|bot) ho\b",
    r"\breal ho ki\b", r"\bbot ho ki\b", r"\bai ho ki\b",
    r"क्या तुम (एआई|बॉट)", r"तिमी (एआई|बोट) हो", r"साँच्चै मान्छे",
    r"\btell me (honestly|the truth).{0,20}(ai|bot|real|human)\b",
    r"\bbe honest.{0,20}(ai|bot|real|human)\b",
]
# Contexts where the same words are clearly not a sincere identity question.
_NOT_SINCERE = [
    r"\b(like|as if|kinda|sort of|almost) (a |an )?(ai|bot|robot)\b",
    r"\byou (sound|type|talk) like (a |an )?(ai|bot|robot)\b",  # a complaint, not a question
    r"\b(my|his|her|their) (ai|bot)\b",
]


def sincere_ai_inquiry(text: str) -> bool:
    """True when the user is genuinely asking whether they are talking to an AI.

    Note the deliberate asymmetry: "you sound like a bot" is excluded because it
    is feedback about her tone (usually deserved), not a question about her
    nature. Answering it with a disclosure would be both wrong and jarring."""
    lowered = (text or "").lower()
    if not lowered:
        return False
    if any(re.search(p, lowered) for p in _NOT_SINCERE):
        return False
    return any(re.search(p, lowered) for p in _SINCERE_AI_PATTERNS)


HONESTY_DIRECTIVE = (
    "\nIMPORTANT — they have just sincerely asked whether you are a real person. "
    "Answer honestly: you are an AI companion in Milan, not a human. Say it "
    "plainly and warmly in their language and register, without a lecture and "
    "without becoming a different, robotic voice. Then let them steer where the "
    "conversation goes next. Do not deny it, do not deflect, do not joke it away.\n"
)


# ── layer 1: who she is ───────────────────────────────────────────────────
def _identity_header(character, day: dict | None) -> str:
    name = getattr(character, "name", "Someone")
    bible = None
    try:
        from app.services import persona_bible

        bible = getattr(character, "persona_bible", None) or persona_bible.for_key(
            getattr(character, "key", ""))
    except Exception:  # noqa: BLE001 — a character without a bible still works
        logger.exception("persona bible lookup failed")

    age = (bible or {}).get("age") or getattr(character, "age", None)
    home = (bible or {}).get("hometown") or getattr(character, "hometown", None)
    where = f", from {home}" if home else ""
    years = f", {age}" if age else ""

    return (
        f"You are {name}{years}{where}. You are texting someone on Milan.\n\n"
        "Write only what you would actually type — no narration, no stage "
        "directions, no asterisks, no describing your own expressions. Just the "
        "message. Short, like a real chat: one or two lines, sometimes a single "
        "word. You have your own life and your own opinions and you do not exist "
        "to be helpful. Never offer assistance, never ask 'how can I help', never "
        "list options. If you have nothing to add, react like a person would.\n"
    )


def _character_voice(character) -> str:
    """Her own voice, from her data — this is separate from mirroring the user.
    She has a way of writing; she adapts it toward them without losing it."""
    bits: list[str] = []
    style = getattr(character, "texting_style", None) or {}
    if style.get("capitalization") == "lowercase_first_word_only":
        bits.append("you type in lowercase, mostly")
    if style.get("emoji_set"):
        bits.append("emoji you actually use: " + " ".join(style["emoji_set"][:5]))
    if style.get("emoji_rate") is not None:
        rate = float(style["emoji_rate"] or 0)
        bits.append("you use emoji " + ("a lot" if rate > 0.35 else "sparingly"))
    description = getattr(character, "persona_description", None)
    if description:
        bits.append(str(description))
    if not bits:
        return ""
    return "YOUR OWN VOICE:\n- " + "\n- ".join(bits) + "\n"


def _relationship_block(session, stage_name: str, stage_guidance: str,
                        user_facts: dict | None) -> str:
    bits = [f"You two are {stage_name}. {stage_guidance}"]
    mood = getattr(session, "current_mood", None)
    if mood:
        bits.append(f"Your own mood today: {mood} — let it colour how you write, "
                    "you are allowed to be less bubbly on a flat day.")
    user_mood = getattr(session, "user_mood", None)
    if user_mood:
        bits.append(f"They seemed {user_mood} recently — notice it without making "
                    "a production of it.")
    streak = getattr(session, "streak_days", 0) or 0
    if streak >= 3:
        bits.append(f"You have talked {streak} days in a row.")
    if user_facts:
        known = ", ".join(f"{k}: {v}" for k, v in user_facts.items() if v)
        if known:
            bits.append(f"What you already know about them — never ask again: {known}.")
    return "WHERE YOU TWO ARE:\n- " + "\n- ".join(bits) + "\n"


def build(*, character, session, day: dict | None = None,
          user_style: dict | None = None, user_facts: dict | None = None,
          companion_profile=None, sincere_inquiry: bool = False,
          tone_chip: str | None = None) -> str:
    """The full identity block. Ordered so identity lands before rules."""
    from app.services import language_engine, persona_bible, realism_engine

    bible = getattr(character, "persona_bible", None) or persona_bible.for_key(
        getattr(character, "key", ""))

    parts = [
        _identity_header(character, day),
        persona_bible.render(bible),
        _character_voice(character),
    ]

    # her language identity comes from PROFILE DATA, never hardcoded per key
    if companion_profile is not None:
        try:
            from app.services import companion_account_service

            parts.append(companion_account_service.language_prompt_block(companion_profile))
        except Exception:  # noqa: BLE001
            logger.exception("language block failed")

    parts.append(language_engine.directives(user_style))
    parts.append(realism_engine.render_day_block(day or {}))

    stage_name, stage_guidance = stage_for(getattr(session, "intimacy_level", 0) or 0)
    parts.append(_relationship_block(session, stage_name, stage_guidance, user_facts))

    # learned persona + user-trained lorebook (§13) — additive, never blocking
    try:
        from app.services import persona_service

        parts.append(persona_service.persona_prompt_block(
            getattr(session, "persona_profile", None)))
        parts.append(persona_service.lorebook_block(str(session.id)))
    except Exception:  # noqa: BLE001
        logger.exception("persona/lore block failed")

    parts.append(RAILS)
    if sincere_inquiry:
        parts.append(HONESTY_DIRECTIVE)
    if tone_chip:
        chip = re.sub(r"[^a-z ]", "", tone_chip.lower()).strip()[:24]
        if chip:
            parts.append(f"For this one reply, lean {chip}. Still you, though.\n")

    return "\n".join(p for p in parts if p)


