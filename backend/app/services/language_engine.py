"""Language mirroring (doc 8 §C4) — she talks the way YOU talk.

The screenshot bug: user wrote `hlw timro name k ho` (romanised Nepali,
informal `timro`), got English back, then formal Devanagari `तपाईंलाई`. Nothing
in the codebase looked at the user's script or register, so the model defaulted
to whatever the prompt was written in.

Three stages, all deterministic and offline — no model call, so this runs on
every message with no latency or cost:

1. `analyze(text)`   — one message -> observable signals
2. `update_style()`  — fold into an EWMA on `SaathiSession.user_style` so a
                       single odd message cannot flip her voice, but a genuine
                       switch converges in ~3 turns
3. `directives()`    — render the accumulated style as hard prompt rules
   `violates()`      — post-check the draft; the caller re-rolls once

Register matters as much as script in Nepali: `timro` (informal) vs `tapaiko`
(formal) is the difference between a girlfriend and a call-centre agent.
"""
import re

# ── character-class probes ────────────────────────────────────────────────
_DEVANAGARI = re.compile(r"[\u0900-\u097F]")
_LATIN = re.compile(r"[A-Za-z]")
_EMOJI = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF" "\U0001F1E6-\U0001F1FF" "]"
)

# ── register: the pronoun/verb-ending system, both scripts ────────────────
# Nepali has three levels. Mixing them is the single most unnatural thing an
# AI does in Nepali, so this is detected explicitly rather than left to vibes.
_REGISTER_MARKERS = {
    "intimate": [  # ta / timi — friends, partners, siblings
        r"\btimro\b", r"\btimi\b", r"\btimilai\b", r"\btimro\b", r"\bta\b",
        r"\btero\b", r"\btalai\b", r"\bhau\b", r"\bxau\b", r"\bchau\b",
        r"तिम्रो", r"तिमी", r"तिमीलाई", r"तँ", r"तेरो", r"छौ", r"हौ",
    ],
    "polite": [  # tapai — strangers, elders, service
        r"\btapai\b", r"\btapaiko\b", r"\btapailai\b", r"\bhajur\b",
        r"\bhuncha\b", r"\bhunuhuncha\b", r"\bgarnuhos\b",
        r"तपाई", r"तपाईं", r"तपाईको", r"तपाईंको", r"हजुर", r"हुनुहुन्छ", r"गर्नुहोस",
    ],
}

# ── romanisation dialect: 'xa' vs 'cha', 'k' vs 'ke' ─────────────────────
# Nepali youth romanise inconsistently but *individually* consistently. Copying
# the user's spelling system is a large part of sounding like a peer.
_ROMANISATION_MARKERS = {
    "x_style": [r"\bxa\b", r"\bxau\b", r"\bxu\b", r"\bxaina\b", r"\bgarxu\b", r"\bxan\b"],
    "ch_style": [r"\bcha\b", r"\bchau\b", r"\bchu\b", r"\bchaina\b", r"\bgarchu\b", r"\bchan\b"],
}
_SHORTFORM_MARKERS = [r"\bk\b", r"\bkn\b", r"\bhlw\b", r"\byr\b", r"\bkina\b", r"\bcx\b"]

# ── language identification by function words, not by dictionary ──────────
_NEPALI_WORDS = {
    "cha", "chha", "xa", "xu", "xau", "xan", "xaina", "chu", "chau", "chan", "chaina",
    "hola", "timro", "timi", "timilai", "mero", "malai", "kasto", "kaha", "kina",
    "gardai", "grdai", "garne", "garxu", "garchu", "gareko", "khana", "khayeu",
    "aile", "bhayo", "vayo", "thiyo", "hunchha", "huncha", "ramro", "hoina", "haina",
    "ni", "po", "ta", "la", "khai", "hami", "tapai", "sanga", "matra", "pani", "nai",
    "bhane", "jasto", "dherai", "ekdam", "vaye", "lagyo", "lagcha", "bho", "hera",
    "sathi", "maya", "ghar", "bhat", "chiya", "momo", "hajur", "kti", "keti",
    "keta", "bhai", "didi", "dai", "bahini", "nasta", "suta", "sutne", "auta",
}
_HINDI_WORDS = {
    "kya", "hai", "hain", "nahi", "accha", "arre", "bahut", "kaise", "tum", "mera",
    "tera", "yaar", "matlab", "thik", "bhai", "abhi", "kuch", "bilkul",
}
_ENGLISH_STOPWORDS = {
    "the", "and", "you", "your", "what", "how", "are", "was", "with", "have",
    "just", "like", "about", "would", "really", "think", "want", "know",
}

# ── internet slang worth echoing back ────────────────────────────────────
_SLANG = [
    "ngl", "fr", "lowkey", "highkey", "tbh", "idk", "imo", "istg", "bro", "bruh",
    "lmao", "lol", "hehe", "haha", "yr", "yaar", "arre", "accha", "khai", "la",
]


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z]+", text.lower())


def _match_any(text: str, patterns: list[str]) -> int:
    return sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))


def analyze(text: str) -> dict:
    """Observable signals from ONE message. Everything here is a fact about the
    text, never a guess about the person — `None` where there is no evidence,
    so the EWMA is not polluted by defaults."""
    raw = (text or "").strip()
    signals: dict = {
        "script": None, "language": None, "register": None, "romanization": None,
        "length": len(raw), "emoji_count": 0, "has_question": False,
        "ends_with_punct": False, "all_lower": None, "slang": [], "shortform": False,
    }
    if not raw:
        return signals

    deva = len(_DEVANAGARI.findall(raw))
    latin = len(_LATIN.findall(raw))
    letters = deva + latin
    if letters == 0:
        # emoji-only / numbers-only: carries tone, not script — leave script None
        signals["emoji_count"] = len(_EMOJI.findall(raw))
        return signals

    deva_ratio = deva / letters
    if deva_ratio >= 0.85:
        signals["script"] = "devanagari"
    elif deva_ratio <= 0.15:
        signals["script"] = "roman"
    else:
        signals["script"] = "mixed"

    words = set(_words(raw))
    ne_hits = len(words & _NEPALI_WORDS)
    hi_hits = len(words & _HINDI_WORDS)
    en_hits = len(words & _ENGLISH_STOPWORDS)
    if signals["script"] == "devanagari":
        signals["language"] = "ne"
    elif ne_hits and en_hits:
        signals["language"] = "ne_en"
    elif hi_hits and ne_hits:
        signals["language"] = "hi_ne"
    elif ne_hits:
        signals["language"] = "ne"
    elif hi_hits:
        signals["language"] = "hi"
    elif en_hits or latin:
        signals["language"] = "en"

    intimate = _match_any(raw, _REGISTER_MARKERS["intimate"])
    polite = _match_any(raw, _REGISTER_MARKERS["polite"])
    if intimate or polite:
        signals["register"] = "intimate" if intimate >= polite else "polite"

    x_hits = _match_any(raw, _ROMANISATION_MARKERS["x_style"])
    ch_hits = _match_any(raw, _ROMANISATION_MARKERS["ch_style"])
    if x_hits or ch_hits:
        signals["romanization"] = "x_style" if x_hits > ch_hits else "ch_style"

    signals["emoji_count"] = len(_EMOJI.findall(raw))
    signals["has_question"] = "?" in raw
    signals["ends_with_punct"] = raw[-1] in ".!?।" if raw else False
    alpha = [c for c in raw if c.isalpha() and not _DEVANAGARI.match(c)]
    if alpha:
        signals["all_lower"] = all(c.islower() for c in alpha)
    signals["slang"] = [s for s in _SLANG if re.search(rf"\b{s}\b", raw, re.IGNORECASE)]
    signals["shortform"] = _match_any(raw, _SHORTFORM_MARKERS) > 0
    return signals


# ── stage 2: accumulate ───────────────────────────────────────────────────
# Categorical signals (script/language/register) can't be averaged, so each
# keeps a small decayed vote tally: the winner is the mode, and `confidence` is
# its share. ALPHA=0.3 means ~3 consistent messages to flip a category and ~7
# to reach high confidence — fast enough to feel responsive, slow enough that
# one copy-pasted English link doesn't turn her into an English speaker.
ALPHA = 0.3
DECAY = 1.0 - ALPHA
_CATEGORICAL = ("script", "language", "register", "romanization")
EMPTY_STYLE: dict = {
    "script": None, "language": None, "register": None, "romanization": None,
    "votes": {}, "avg_len": None, "emoji_rate": 0.0, "question_rate": 0.0,
    "lowercase_rate": 0.0, "shortform_rate": 0.0, "slang": [], "samples": 0,
}


def _vote(votes: dict, field: str, value: str) -> None:
    bucket = votes.setdefault(field, {})
    for key in list(bucket):
        bucket[key] = round(bucket[key] * DECAY, 4)
        if bucket[key] < 0.01:
            del bucket[key]
    bucket[value] = round(bucket.get(value, 0.0) * DECAY + ALPHA, 4)


def _winner(votes: dict, field: str) -> tuple[str | None, float]:
    bucket = votes.get(field) or {}
    if not bucket:
        return None, 0.0
    total = sum(bucket.values()) or 1.0
    best = max(bucket, key=bucket.get)
    return best, round(bucket[best] / total, 3)


def _ewma(previous: float | None, value: float) -> float:
    if previous is None:
        return round(value, 3)
    return round(previous * DECAY + value * ALPHA, 3)


def update_style(style: dict | None, signals: dict) -> dict:
    """Fold one message's signals into the session's running style.

    Returns a NEW dict (never mutates the stored JSON in place — SQLAlchemy
    does not reliably detect in-place JSON mutation)."""
    current = dict(style or EMPTY_STYLE)
    current.setdefault("votes", {})
    votes = {k: dict(v) for k, v in (current.get("votes") or {}).items()}

    for field in _CATEGORICAL:
        value = signals.get(field)
        if value:
            _vote(votes, field, value)
    current["votes"] = votes
    for field in _CATEGORICAL:
        winner, confidence = _winner(votes, field)
        current[field] = winner
        current[f"{field}_confidence"] = confidence

    length = signals.get("length") or 0
    if length:
        current["avg_len"] = _ewma(current.get("avg_len"), float(length))
        emoji_per_msg = float(signals.get("emoji_count") or 0)
        current["emoji_rate"] = _ewma(current.get("emoji_rate"), emoji_per_msg)
        current["question_rate"] = _ewma(
            current.get("question_rate"), 1.0 if signals.get("has_question") else 0.0)
        if signals.get("all_lower") is not None:
            current["lowercase_rate"] = _ewma(
                current.get("lowercase_rate"), 1.0 if signals["all_lower"] else 0.0)
        current["shortform_rate"] = _ewma(
            current.get("shortform_rate"), 1.0 if signals.get("shortform") else 0.0)

    if signals.get("slang"):
        # keep a small most-recent-first set; the user's own words fed back is
        # what makes replies feel like they came from someone who knows them
        merged = list(dict.fromkeys(list(signals["slang"]) + list(current.get("slang") or [])))
        current["slang"] = merged[:10]

    current["samples"] = int(current.get("samples") or 0) + 1
    return current


# ── stage 3: render + enforce ─────────────────────────────────────────────
_SCRIPT_RULES = {
    "roman": ("Write Nepali in ROMAN letters (Nepali typed with English "
              "letters). Do NOT use Devanagari script at all."),
    "devanagari": ("Write in DEVANAGARI script (देवनागरी). Use English words only "
                   "where a Nepali speaker naturally would."),
    "mixed": ("Move between Devanagari and Roman/English freely, the way "
              "someone comfortable in both does."),
}
_LANGUAGE_RULES = {
    "ne": "Speak Nepali. English only for words Nepali speakers use in English.",
    "ne_en": "Code-switch Nepali and English mid-sentence, the way Kathmandu youth text.",
    "hi": "Speak Hindi, the way it is spoken in the Terai.",
    "hi_ne": "Blend Hindi and Nepali, the way Madhesi speakers do.",
    "en": "Speak English, with Nepali words dropped in for warmth.",
}
_REGISTER_RULES = {
    "intimate": ("Use the INFORMAL register — timi/timro/ta, verb endings in "
                 "-au/-xau. Never tapai/tapaiko/hajur: formal address to someone "
                 "close reads cold and wrong."),
    "polite": ("Use the POLITE register — tapai/tapaiko, -nuhuncha endings — "
               "until they switch to timi first."),
}
_ROMANIZATION_RULES = {
    "x_style": "Spell Nepali the way they do — 'xa', 'xau', 'garxu' (x, not ch).",
    "ch_style": "Spell Nepali the way they do — 'cha', 'chau', 'garchu' (ch, not x).",
}

# Below this, there is not enough evidence to constrain her — better to let the
# character's own default voice speak than to guess wrong and sound erratic.
MIN_CONFIDENCE = 0.45
# Post-draft enforcement is stricter: only re-roll when the user has been very
# consistent, so a genuinely code-switching user is never fought.
ENFORCE_CONFIDENCE = 0.8


def directives(style: dict | None) -> str:
    """Render accumulated style as prompt rules. Empty string on a new session:
    her own voice leads until the user has actually shown one."""
    if not style or not style.get("samples"):
        return ""
    rules: list[str] = []

    for field, table in (("script", _SCRIPT_RULES), ("language", _LANGUAGE_RULES),
                         ("register", _REGISTER_RULES),
                         ("romanization", _ROMANIZATION_RULES)):
        value = style.get(field)
        confidence = float(style.get(f"{field}_confidence") or 0.0)
        if value and confidence >= MIN_CONFIDENCE and value in table:
            rules.append(table[value])

    avg_len = style.get("avg_len")
    if avg_len:
        if avg_len < 25:
            rules.append("They text in very short bursts — match that. One line, sometimes "
                         "a single word. Long paragraphs feel like a different species.")
        elif avg_len < 80:
            rules.append("They text in short-to-medium messages — keep yours similar.")
        else:
            rules.append("They write longer messages — you can too, but stay conversational.")

    emoji_rate = float(style.get("emoji_rate") or 0.0)
    if emoji_rate < 0.15:
        rules.append("They barely use emoji — so don't sprinkle them.")
    elif emoji_rate > 1.2:
        rules.append("They use emoji heavily — match their energy.")

    if float(style.get("lowercase_rate") or 0.0) > 0.7:
        rules.append("They type in lowercase — do the same, skip the capitals.")
    if float(style.get("shortform_rate") or 0.0) > 0.4:
        rules.append("They use shortforms ('k', 'hlw', 'yr') — use them naturally too.")

    slang = style.get("slang") or []
    if slang:
        rules.append("Words they actually use: " + ", ".join(f'"{s}"' for s in slang[:6])
                     + " — echoing a couple back is what makes you sound like a peer.")

    if not rules:
        return ""
    return ("HOW THEY TEXT — MIRROR IT (this is the single most important thing "
            "for sounding real; getting the script or register wrong instantly "
            "breaks it):\n- " + "\n- ".join(rules) + "\n")


def violates(draft: str, style: dict | None) -> str | None:
    """Post-draft check. Returns a short corrective instruction when the draft
    contradicts a HIGH-confidence observed style, else None.

    Only script and register are enforced: they are objectively checkable and
    they are exactly what broke in the screenshot. Tone/length are left to the
    prompt — re-rolling on those would fight legitimate variation."""
    text = (draft or "").strip()
    if not text or not style:
        return None
    signals = analyze(text)

    script = style.get("script")
    if (script and float(style.get("script_confidence") or 0) >= ENFORCE_CONFIDENCE
            and signals["script"] and signals["script"] != script
            and script in _SCRIPT_RULES):
        return _SCRIPT_RULES[script]

    register = style.get("register")
    if (register and float(style.get("register_confidence") or 0) >= ENFORCE_CONFIDENCE
            and signals["register"] and signals["register"] != register
            and register in _REGISTER_RULES):
        return _REGISTER_RULES[register]
    return None


