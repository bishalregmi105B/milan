"""Offline text filter — Nepali (Devanagari + romanized) and English
profanity/rough-word screening with no network dependency (doc 8 §C2).

Two belts:
  hard   — slurs, explicit sexual abuse, threats of violence. Always blocks.
  rough  — crude words that may appear in casual banter. Blocks identity
           surfaces (display names, interests) and is reported for bios.

Transliteration-tolerant: leet/separator/character-substitution variants of
the same word normalize to one hit. Used by profile saving (display name,
bio, prompts, interests), the discovery search endpoint, and as the
deterministic lexical belt inside the AI moderator.
"""
import re

# ── hard belt: always blocks ────────────────────────────────────────────────
# Nepali/Hindi romanized + Devanagari, then English. Patterns are tolerant of
# separators and common substitutions (i→1/!, a→@, o→0, s→5/$).
_HARD_WORDS = [
    # Nepali / Hindi romanized
    "randi", "randwa", "chikne", "chikna", "bhosadi", "bhosda", "machod",
    "machuda", "bhosadike", "bhenchod", "behanchod", "bhadwa", "bhadwa",
    "haramzada", "harami", "chut", "chuchi", "gaand", "gandu", "lund",
    "lawda", "loda", "chodu", "choda", "jhat", "bhosdike", "tattoke",
    "kalomui", "kalo mui", "ghare auni",
    # English
    "nigger", "nigga", "faggot", "retard", "kike", "spic", "tranny",
    "motherfucker", "cocksucker", "cumshot", "blowjob", "handjob",
]

_HARD_REGEXES = [
    # threats / extortion phrasing that survives word-list normalisation
    r"\bi (will|wanna|going to) (find|kill|hurt) you\b",
    r"\bkys\b",
    r"\bf[u*@]ck (yo)?u*r? (mother|sister|family)\b",
    r"\bfuck off and die\b",
    # Devanagari explicit terms
    "रंडी", "भोसडी", "भेन्चोद", "मादरचोद", "गाण्ड", "लन्ड", "चुच्ची", "हरामी",
]

_ROUGH_WORDS = [
    "fuck", "fuk", "fck", "shit", "bitch", "bastard", "asshole", "dickhead",
    "arsehole", "cunt", "dick", "cock", "pussy", "prick", "slut", "whore",
    "wanker", "bollocks", "jerk off", "horny", "sex chat", "suk muji",
    "muji", "sutta", "kutti", "kukur", "sundi", "sudi",
]

_SUBS = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t",
    "@": "a", "$": "s", "!": "i", "*": "", "-": "", "_": "", ".": "",
    "×": "x",
})


def _normalize(text: str) -> str:
    lowered = (text or "").lower().translate(_SUBS)
    # collapse repeated letters (fuuuck → fuck) and squeezed spaces
    collapsed = re.sub(r"(.)\1{2,}", r"\1\1", lowered)
    return collapsed


def _word_pattern(word: str) -> re.Pattern:
    tokens = [re.escape(t) for t in word.split()]
    body = r"[\s_-]*".join(tokens)
    # allow intra-word separators for single tokens (f-u-c-k)
    if len(tokens) == 1 and len(word) > 3:
        body = r"[\s_-]*".join(re.escape(ch) for ch in word)
    return re.compile(rf"\b{body}\b", re.IGNORECASE)


_HARD_RE = [_word_pattern(w) for w in _HARD_WORDS if len(w) > 2] + [
    re.compile(p, re.IGNORECASE) if p.startswith("\\b") else re.compile(p)
    for p in _HARD_REGEXES
]
_ROUGH_RE = [_word_pattern(w) for w in _ROUGH_WORDS]


def hard_block(text: str) -> bool:
    """True when the text hits the hard belt (slurs, explicit abuse, threats)."""
    if not text:
        return False
    normalized = _normalize(text)
    return any(rx.search(normalized) for rx in _HARD_RE)


def rough_flags(text: str) -> list[str]:
    """Rough words present in the text; informative, not identity-blocking."""
    if not text:
        return []
    normalized = _normalize(text)
    return [w for w, rx in zip(_ROUGH_WORDS, _ROUGH_RE) if rx.search(normalized)]


def screen(text: str, *, allow_rough: bool = True) -> dict:
    """Single entry point. Returns {"ok", "severity", "violations"}.

    severity: "hard" (always reject), "rough" (reject on identity surfaces,
    else allowed), or "clean". `allow_rough=False` rejects rough words too —
    use for display names, interest labels and other identity surfaces."""
    if hard_block(text):
        return {"ok": False, "severity": "hard", "violations": ["hard_language"]}
    rough = rough_flags(text)
    if rough and not allow_rough:
        return {"ok": False, "severity": "rough", "violations": rough}
    if rough:
        return {"ok": True, "severity": "rough", "violations": rough}
    return {"ok": True, "severity": "clean", "violations": []}


def mask(text: str) -> str:
    """Replace hard/rough tokens with their first character plus asterisks.
    Used where rejecting the whole message would be worse than masking."""
    if not text:
        return text
    masked = text
    for rx in _HARD_RE:
        masked = rx.sub(lambda m: m.group(0)[0] + "*" * max(len(m.group(0)) - 1, 2), masked)
    for rx in _ROUGH_RE:
        masked = rx.sub(lambda m: m.group(0)[0] + "*" * max(len(m.group(0)) - 1, 2), masked)
    return masked
