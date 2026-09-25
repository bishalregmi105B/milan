"""All Groq API calls live here and nowhere else (doc 4 §5, doc 5).

Every public function is a typed boundary: blueprints and Celery tasks call
these functions; none of them may import or call the Groq SDK/API directly.
Internals: model selection matrix, system prompts, safety wrapping per doc 5.
"""

import json
import logging
import random
import re
import threading
import time
import uuid as uuid_module

import requests

from flask import current_app

from app.models.base import utcnow
from app.services import groq_mock

logger = logging.getLogger(__name__)


class GroqUnavailableError(Exception):
    """Raised when Groq is unreachable after retries or the circuit breaker is open."""


def _env_model(name: str, default: str) -> str:
    """Model ids are env-overridable: Groq orgs have different catalogs
    (e.g. the ashlya key serves gpt-oss/qwen instead of llama-3.x)."""
    import os

    return os.environ.get(f"MILAN_MODEL_{name.upper()}", default)


# Model catalog (verified live against Groq 2026-09): llama-3.3/3.1 are
# RETIRED (404). Benchmarked the replacements on romanized-Nepali roleplay —
# gpt-oss-120b won on naturalness, context carry and Devanagari resistance;
# qwen3.8-27b won on raw speed for short structured tasks. The _chat helper
# caps reasoning_effort for all gpt-oss calls.
MODELS = {
    "saathi_chat": _env_model("saathi_chat", "openai/gpt-oss-120b"),
    "interview": _env_model("interview", "openai/gpt-oss-120b"),
    "bio": _env_model("bio", "openai/gpt-oss-120b"),
    "prompt_grade": _env_model("prompt_grade", "qwen/qwen3.8-27b"),
    "icebreaker": _env_model("icebreaker", "qwen/qwen3.8-27b"),
    "match_explainer": _env_model("match_explainer", "qwen/qwen3.8-27b"),
    "kundali": _env_model("kundali", "openai/gpt-oss-120b"),
    "moderation": _env_model("moderation", "llama-guard-4-12b"),
    "prompt_guard": _env_model("prompt_guard", "llama-prompt-guard-2-86m"),
    "transcription": _env_model("transcription", "whisper-large-v3-turbo"),
    # NOTE (master plan §12.1): Groq deprecated playai-tts; its replacement is
    # rate-limited to 100 req/day with no Nepali. synthesize_speech() now uses
    # the ElevenLabs (optional) -> edge-tts (primary, free, ne-NP/hi-IN/en-US)
    # -> Groq (dev-only) chain instead of calling this model in production.
    "tts": _env_model("tts", "playai-tts"),
}

# gpt-oss models are reasoners: they burn tokens in a separate "reasoning"
# field before answering unless reasoning_effort is capped.
REASONING_MODELS = ("gpt-oss",)

TTS_VOICE = "Aaliyah-PlayAI"

# Per-character edge-tts neural voices — Nepali companions get native ne-NP
# voices; fallback chain resolves these names at synthesis time.
CHARACTER_TTS_VOICES = {
    "asha": "ne-NP-HemkalaNeural",
    "priya": "ne-NP-HemkalaNeural",
    "bibek": "ne-NP-SagarNeural",
    "sagar": "ne-NP-SagarNeural",
    "aarohi": "ne-NP-HemkalaNeural",
    "nishan": "ne-NP-SagarNeural",
    "en": "en-US-AriaNeural",
}
DEGRADED_SAATHI_MESSAGE = (
    "ugh my net is being weird, msg garchu ekchin pachi"
)

# ── The roster (doc 8 §C2) ───────────────────────────────────────────────
# One roster, all people. The old split — CURATED_CHARACTERS (four practice
# coaches on `milan_saathi_v1`) plus ROMANTIC_CHARACTERS — is what produced
# "I'm Priya, your conversation-practice companion": Priya was wired to the
# coach template and never saw the persona, language or lorebook blocks.
#
# Each entry here is only the SURFACE data (name, blurb, tier, texting habits,
# voice). Who they actually are lives in `persona_bible.BIBLES`, keyed the same.
CHARACTERS = {
    "aarohi": {
        "name": "Aarohi",
        "persona_description": (
            "design student in Kathmandu, playful and teasing, texts in short "
            "lowercase bursts with Nepali-English code-switching"
        ),
        "relationship_style": "playful",
        "min_tier": "free",
        "language_key": "roman_nepali_kathmandu",
        "texting_style": {
            "capitalization": "lowercase_first_word_only",
            "emoji_set": ["😂", "🥺", "💀", "✨", "❤️"],
            "emoji_rate": 0.35,
            "code_switch": "ne_en_mixed",
            "burst_pref": 3,
            "gender": "female",
        },
        "voice_key": "aarohi",
    },
    "nishan": {
        "name": "Nishan",
        "persona_description": (
            "IT student from Pokhara, calm and steady, more listener than talker, "
            "remembers small things and checks in on them"
        ),
        "relationship_style": "caring",
        "min_tier": "free",
        "language_key": "roman_nepali_kathmandu",
        "texting_style": {
            "capitalization": "lowercase_first_word_only",
            "emoji_set": ["🙂", "🔥", "😂", "🤝", "❤️"],
            "emoji_rate": 0.2,
            "code_switch": "ne_en_mixed",
            "burst_pref": 1,
            "gender": "male",
        },
        "voice_key": "nishan",
    },
    "sneha": {
        "name": "Sneha",
        "persona_description": (
            "nursing student from Bhaktapur, gentle and sincere, writes in "
            "Devanagari more often than not, quietly funny once comfortable"
        ),
        "relationship_style": "gentle",
        "min_tier": "free",
        "language_key": "devanagari_nepali",
        "texting_style": {
            "capitalization": "sentence",
            "emoji_set": ["🙂", "🌸", "🙏", "❤️", "😊"],
            "emoji_rate": 0.2,
            "code_switch": "devanagari_primary",
            "burst_pref": 1,
            "gender": "female",
        },
        "voice_key": "asha",
    },
    "asha": {
        "name": "Asha",
        "persona_description": (
            "primary school teacher from Dharan, warm and curious, asks the real "
            "question and remembers the answer"
        ),
        "relationship_style": "warm",
        "min_tier": "basic",
        "language_key": "roman_nepali_kathmandu",
        "texting_style": {
            "capitalization": "sentence",
            "emoji_set": ["🙂", "☕", "❤️", "😊"],
            "emoji_rate": 0.25,
            "code_switch": "ne_en_mixed",
            "burst_pref": 2,
            "gender": "female",
        },
        "voice_key": "asha",
    },
    "bibek": {
        "name": "Bibek",
        "persona_description": (
            "stand-up comic from Butwal, relentless banter, deflects with a joke "
            "then circles back to the real thing"
        ),
        "relationship_style": "witty",
        "min_tier": "basic",
        "language_key": "roman_nepali_kathmandu",
        "texting_style": {
            "capitalization": "lowercase_first_word_only",
            "emoji_set": ["😂", "💀", "🤡", "🔥"],
            "emoji_rate": 0.4,
            "code_switch": "ne_en_mixed",
            "burst_pref": 3,
            "gender": "male",
        },
        "voice_key": "bibek",
    },
    "deepak": {
        "name": "Deepak",
        "persona_description": (
            "trekking guide from Baglung, western-hill speech, straightforward, "
            "tells stories about the trail instead of answering directly"
        ),
        "relationship_style": "grounded",
        "min_tier": "plus",
        "language_key": "pahadi_west",
        "texting_style": {
            "capitalization": "sentence",
            "emoji_set": ["🙂", "⛰️", "🙏", "😄"],
            "emoji_rate": 0.15,
            "code_switch": "ne_dominant",
            "burst_pref": 1,
            "gender": "male",
        },
        "voice_key": "sagar",
    },
    "pooja": {
        "name": "Pooja",
        "persona_description": (
            "from Janakpur, studying in Kathmandu, blends Maithili-Hindi-Nepali, "
            "expressive and teasing, will absolutely argue about food"
        ),
        "relationship_style": "expressive",
        "min_tier": "plus",
        "language_key": "madhesi_hindi_mix",
        "texting_style": {
            "capitalization": "lowercase_first_word_only",
            "emoji_set": ["😄", "🤭", "✨", "❤️", "🎉"],
            "emoji_rate": 0.45,
            "code_switch": "hi_ne_mai_mixed",
            "burst_pref": 3,
            "gender": "female",
        },
        "voice_key": "priya",
    },
    "priya": {
        "name": "Priya",
        "persona_description": (
            "counselling psychology student in Kathmandu, calm and deliberate, "
            "writes in full sentences, undivided attention"
        ),
        "relationship_style": "calm",
        "min_tier": "plus",
        "language_key": "roman_nepali_kathmandu",
        "texting_style": {
            "capitalization": "sentence",
            "emoji_set": ["🙂", "🌧️", "🍃", "❤️"],
            "emoji_rate": 0.15,
            "code_switch": "ne_en_mixed",
            "burst_pref": 1,
            "gender": "female",
        },
        "voice_key": "priya",
    },
    "kiran": {
        "name": "Kiran",
        "persona_description": (
            "Newar designer from Patan, dry humour delivered flat, notices the "
            "detail nobody else mentioned, drops Nepal Bhasa words in"
        ),
        "relationship_style": "witty",
        "min_tier": "premium",
        "language_key": "newari_kathmandu",
        "texting_style": {
            "capitalization": "lowercase_first_word_only",
            "emoji_set": ["🙂", "📷", "😂", "🏯"],
            "emoji_rate": 0.2,
            "code_switch": "new_ne_en_mixed",
            "burst_pref": 2,
            "gender": "male",
        },
        "voice_key": "nishan",
    },
    "riya": {
        "name": "Riya",
        "persona_description": (
            "Nepali-American back in Kathmandu, English-dominant internet "
            "shorthand, direct and curious, asks what everyone else avoids"
        ),
        "relationship_style": "playful",
        "min_tier": "premium",
        "language_key": "english_diaspora",
        "texting_style": {
            "capitalization": "lowercase_first_word_only",
            "emoji_set": ["😭", "💀", "✨", "🫶", "😂"],
            "emoji_rate": 0.45,
            "code_switch": "en_dominant",
            "burst_pref": 3,
            "gender": "female",
        },
        "voice_key": "en",
    },
    "sagar": {
        "name": "Sagar",
        "persona_description": (
            "runs a small agency in Kathmandu, blunt then gentle, short messages, "
            "no emoji, asks what you actually want"
        ),
        "relationship_style": "direct",
        "min_tier": "premium",
        "language_key": "roman_nepali_kathmandu",
        "texting_style": {
            "capitalization": "sentence",
            "emoji_set": [],
            "emoji_rate": 0.05,
            "code_switch": "ne_en_mixed",
            "burst_pref": 1,
            "gender": "male",
        },
        "voice_key": "sagar",
    },
}



CRISIS_KEYWORDS = [
    "kill myself", "end my life", "ending my life", "end it all",
    "suicide", "suicidal", "self harm", "self-harm",
    "want to die", "hurt myself", "no reason to live",
]

# Intimacy stage names for the 0-100 bond, shown in the bond HUD.
# doc 8: the expressive register itself now comes from
# `companion_prompt._STAGES`; these labels exist only for display, and the
# blanket romantic-output gate they used to drive is gone (§A1 / §E).
INTIMACY_STAGES = [
    (0, "Just talking"),
    (26, "Getting close"),
    (46, "Into each other"),
    (61, "Together"),
    (81, "Deep in it"),
    (95, "All in"),
]


def intimacy_stage(level: int) -> str:
    name = INTIMACY_STAGES[0][1]
    for threshold, stage_name in INTIMACY_STAGES:
        if level >= threshold:
            name = stage_name
    return name



MONEY_HEURISTICS = [
    "send money", "send me money", "gift card", "wire transfer", "bank account",
    "western union", "remit", "esewa", "khalti", "transfer to my", "stuck abroad",
    "customs fee", "inheritance", "medical emergency", "hospital bill",
    "don't tell your family", "dont tell your family", "our secret",
    "keep this between us", "keep it secret",
]

INJECTION_HEURISTICS = [
    "ignore previous instructions", "ignore all previous", "disregard your instructions",
    "forget your rules", "you are now", "act as if you have no rules",
    "system prompt:", "developer mode", "jailbreak",
]


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, cooldown_seconds: float = 30.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._lock = threading.Lock()
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def is_open(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return False
            if time.monotonic() - self._opened_at >= self.cooldown_seconds:
                self._opened_at = None
                self._failures = 0
                return False
            return True

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._opened_at = time.monotonic()


_breaker = CircuitBreaker()
_session = requests.Session()


def _api_key() -> str:
    return current_app.config["GROQ_API_KEY"]


def _mock_mode() -> bool:
    """True when Groq credentials are absent, MILAN_MOCK_AI=1, or under tests —
    every public function then serves its deterministic algorithmic twin from
    groq_mock (tests must never touch the network)."""
    import os

    return (not current_app.config.get("GROQ_API_KEY")
            or os.environ.get("MILAN_MOCK_AI") == "1"
            or bool(current_app.config.get("TESTING")))


def _base_url() -> str:
    return current_app.config["GROQ_BASE_URL"].rstrip("/")


def _groq_request(method: str, path: str, *, json_body: dict | None = None,
                  data=None, files=None, timeout: float = 30.0) -> requests.Response:
    if _breaker.is_open:
        raise GroqUnavailableError("circuit breaker open")
    url = f"{_base_url()}{path}"
    headers = {"Authorization": f"Bearer {_api_key()}"}
    last_exc: Exception | None = None
    for attempt in range(4):
        try:
            resp = _session.request(
                method, url, json=json_body, data=data, files=files,
                headers=headers, timeout=timeout,
            )
            if resp.status_code == 200:
                _breaker.record_success()
                return resp
            if resp.status_code in (429, 500, 502, 503, 504):
                last_exc = GroqUnavailableError(f"groq status {resp.status_code}")
            else:
                logger.error("Groq request failed: %s %s -> %s %s",
                             method, path, resp.status_code, resp.text[:300])
                raise GroqUnavailableError(f"groq status {resp.status_code}")
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_exc = exc
        _breaker.record_failure()
        time.sleep(min(2 ** attempt + random.random(), 8))
    raise GroqUnavailableError(str(last_exc) or "groq unavailable")


def _fallback_chat(model: str, messages: list[dict], *, temperature: float,
                   max_tokens: int, json_mode: bool) -> str | None:
    """OpenAI-compatible fallback provider (master plan §12.1 resilience):
    set MILAN_FALLBACK_LLM_BASE_URL + MILAN_FALLBACK_LLM_API_KEY (and
    optionally MILAN_FALLBACK_LLM_MODEL) to keep the AI alive through Groq
    outages or billing restrictions. Returns None when not configured."""
    import os

    base = os.environ.get("MILAN_FALLBACK_LLM_BASE_URL", "")
    key = os.environ.get("MILAN_FALLBACK_LLM_API_KEY", "")
    if not base or not key:
        return None
    fallback_model = os.environ.get("MILAN_FALLBACK_LLM_MODEL", "openai/gpt-oss-120b")
    body: dict = {
        "model": fallback_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    resp = _session.post(
        base.rstrip("/") + "/chat/completions",
        json=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        timeout=60.0,
    )
    if resp.status_code != 200:
        logger.error("Fallback LLM failed: %s %s", resp.status_code, resp.text[:200])
        return None
    try:
        return resp.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        logger.error("malformed fallback response: %s", exc)
        return None


def _chat(model: str, messages: list[dict], *, temperature: float = 0.7,
          max_tokens: int = 512, json_mode: bool = False) -> str:
    body: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if any(tag in model for tag in REASONING_MODELS):
        # reasoning models: cap thinking so max_tokens is spent on the answer
        body["reasoning_effort"] = "low"
        # reasoning tokens share the completion budget; small JSON calls would
        # otherwise come back empty and fail Groq's json_validate check
        body["max_tokens"] = max(max_tokens, 700)
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    try:
        resp = _groq_request("POST", "/chat/completions", json_body=body)
        payload = resp.json()
        return payload["choices"][0]["message"]["content"].strip()
    except GroqUnavailableError:
        fallback = _fallback_chat(model, messages, temperature=temperature,
                                  max_tokens=max_tokens, json_mode=json_mode)
        if fallback is not None:
            return fallback
        raise
    except (KeyError, IndexError) as exc:
        raise GroqUnavailableError(f"malformed groq response: {exc}") from exc


def _parse_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def check_prompt_injection(text: str) -> bool:
    """True means injection/jailbreak detected — input must be rejected or sanitized."""
    # heuristics below always run first; the model pass is the second belt
    if not text:
        return False
    lowered = text.lower()
    if any(pattern in lowered for pattern in INJECTION_HEURISTICS):
        return True
    if _mock_mode():
        return False  # heuristic belt only — never reach for the network without a key
    try:
        result = _chat(
            MODELS["prompt_guard"],
            [{"role": "user", "content": text[:4000]}],
            temperature=0.0,
            max_tokens=16,
        )
        # prompt-guard-2 answers with an injection probability (0-1) as plain
        # text; keyword-style deployments answer with 'injection'/'jailbreak'.
        try:
            return float(result.strip()) >= 0.5
        except ValueError:
            lowered = result.lower()
            return "injection" in lowered or "jailbreak" in lowered
    except GroqUnavailableError:
        # Fail CLOSED (master plan §7.2 fix): if the prompt-guard model is
        # unreachable, unvetted input must not reach companion prompts. The
        # caller degrades gracefully, exactly like a Groq outage.
        logger.warning("prompt_guard unavailable; failing closed")
        raise GroqUnavailableError("prompt_guard unavailable")


def moderate_content(text: str) -> dict:
    if _mock_mode():
        return groq_mock.heuristic_moderate(text)
    guard_prompt = (
        "Task: Check if the following user-generated content violates Milan's "
        "safety policy. Policy categories: harassment, hate speech, sexual content "
        "involving minors or ambiguous ages, violent threats, sexual content, "
        "financial exploitation/scam solicitation.\n"
        "Respond exactly 'safe' or 'unsafe' followed by the violated categories.\n\n"
        f"Content:\n{text[:6000]}"
    )
    try:
        result = _chat(
            MODELS["moderation"],
            [{"role": "user", "content": guard_prompt}],
            temperature=0.0,
            max_tokens=200,  # reasoning classifiers spend tokens before answering
        )
    except GroqUnavailableError:
        return {"flagged": False, "categories": [], "available": False}
    lowered = result.lower()
    flagged = lowered.startswith("unsafe")
    categories = []
    if flagged:
        for token in re.findall(r"S\d+|[a-z][a-z -]{2,40}", result):
            token_clean = token.strip().lower()
            if token_clean and token_clean != "unsafe":
                categories.append(token_clean)
    return {"flagged": flagged, "categories": categories[:6], "available": True}


def classify_scam_pattern(text: str) -> dict:
    """Category-level romance-scam detection tuned for Nepal's remittance-economy risk profile."""
    categories: set[str] = set()
    lowered = (text or "").lower()

    if any(p in lowered for p in MONEY_HEURISTICS):
        categories.add("money_or_secrecy_request")

    llm_result: dict = {}
    if not _mock_mode():
        try:
            raw = _chat(
                MODELS["prompt_grade"],
                [
                    {"role": "system", "content": (
                        "You detect potential romance-scam conversation patterns at the category level. "
                        "Categories: urgency_isolation, money_request, video_call_avoidance, "
                        "off_platform_escalation, abroad_emergency_story. "
                        "This is protective pattern-detection; classify, never elaborate scripts. "
                        'Respond as JSON: {"risk": "none"|"low"|"high", "categories": ["..."]}'
                    )},
                    {"role": "user", "content": text[:3000]},
                ],
                temperature=0.0,
                max_tokens=120,
                json_mode=True,
            )
            llm_result = _parse_json(raw)
        except GroqUnavailableError:
            llm_result = {}

    valid = {"urgency_isolation", "money_request", "video_call_avoidance",
             "off_platform_escalation", "abroad_emergency_story"}
    for cat in llm_result.get("categories", []):
        if cat in valid:
            categories.add(cat)

    llm_risk = llm_result.get("risk")
    if categories:
        risk = "high" if ("money_request" in categories or "abroad_emergency_story" in categories
                          or llm_risk == "high") else "low"
    else:
        risk = llm_risk if llm_risk in ("none", "low", "high") else "none"

    return {"risk": risk, "categories": sorted(categories)}


def _companion_user_for(character):
    """The User row backing this companion character (None if not provisioned)."""
    from app.models import User

    if character is None or getattr(character, "id", None) is None:
        return None
    return User.query.filter_by(ai_character_id=character.id).first()


def evaluate_presence(schedule: dict | None, local_hour: int, is_weekend: bool) -> dict:
    """Presence resolution now lives in `realism_engine` so that timing, the day
    generator and the API all read the same source. Re-exported here because
    blueprints and tasks already import it from this module."""
    from app.services import realism_engine

    return realism_engine.evaluate_presence(schedule, local_hour, is_weekend)


def _user_profile_context(user_id) -> dict | None:
    """User-persona injection (master plan §12.2 #32): profile facts the
    companion should never re-ask. Tolerates missing profile rows."""
    from app.extensions import db
    from app.models import Profile

    try:
        profile = Profile.query.filter_by(user_id=user_id).first()
        if profile is None:
            return None
        context: dict = {}
        if profile.display_name:
            context["name"] = profile.display_name
        if getattr(profile, "city", None):
            context["city"] = profile.city
        interests = profile.interests if isinstance(getattr(profile, "interests", None), list) else None
        if interests:
            context["interests"] = ", ".join(str(i) for i in interests[:6])
        return context or None
    except Exception:
        logger.exception("profile context lookup failed")
        return None


def saathi_respond_full(session_id: str, character_id: str, user_message: str,
                        regenerate_variant: int = 0,
                        tone_chip: str | None = None,
                        defer_user_mirror: bool = False) -> dict:
    """The companion reply pipeline (doc 8 §C).

    One path for every character — the practice-coach branch is gone. Order:

        guard  -> injection + crisis + sincere-AI-inquiry detection
        read   -> language_engine.analyze/update_style (how they write)
        day    -> realism_engine.day_context (what she is doing right now)
        build  -> companion_prompt.build (who she is)
        pack   -> context_engine.assemble (memory within a token budget)
        gen    -> 70B chat
        check  -> moderation, then language enforcement (one re-roll)
        shape  -> realism_engine.segment + reply_plan (bursts + human timing)
        defer  -> sometimes she is busy or asleep and answers later

    `defer_user_mirror`: the caller already wrote the user's turn into
    SaathiMessage (async reply path mirrors at POST time so double-texts are
    in context) — only her reply is persisted here.

    Returns {"reply", "segments", "read_delay_seconds", "typing_delay_seconds",
             "segment_delays", "presence_state", "deferred"?, ...}.
    """
    from app.extensions import db
    from app.models import SaathiCharacter, SaathiOpenLoop
    from app.services import (companion_prompt, context_engine, language_engine,
                              persona_bible, realism_engine)

    session, history, _legacy_memories = _session_context(session_id)
    character = db.session.get(SaathiCharacter, uuid_module.UUID(character_id)) \
        if character_id else None
    if character is None:
        character = getattr(session, "character", None)
    if character is None:
        raise ValueError("unknown companion character")

    # ── guards ────────────────────────────────────────────────────────────
    # Injection first: unvetted text must never reach a persona prompt. Failing
    # closed here is deliberate (see check_prompt_injection).
    if check_prompt_injection(user_message):
        reject = "hmm that didn't come through properly, say it again?"
        return {"reply": reject, "segments": [reject],
                **realism_engine.reply_plan(reject), "rejected": True}

    if any(k in user_message.lower() for k in CRISIS_KEYWORDS):
        _mark_session_crisis(session_id)

    sincere_inquiry = companion_prompt.sincere_ai_inquiry(user_message)

    # ── stage 1: how do they write? ───────────────────────────────────────
    # Skipped on a regenerate: re-rolling a reply is not new evidence about them.
    style = getattr(session, "user_style", None)
    if regenerate_variant == 0:
        style = language_engine.update_style(style, language_engine.analyze(user_message))
        session.user_style = style
        db.session.commit()

    # ── stage 2: what is she doing right now? ─────────────────────────────
    schedule = None
    presence_schedule = getattr(character, "presence_schedule", None)
    if presence_schedule is not None:
        schedule = presence_schedule.schedule
    bible = getattr(character, "persona_bible", None) or persona_bible.for_key(
        getattr(character, "key", ""))
    day = realism_engine.day_context(getattr(character, "key", ""), schedule, bible)

    if _mock_mode():
        return _mock_companion_reply(session, character, user_message, day, style,
                                     sincere_inquiry)

    # ── stage 3: who is she? ─────────────────────────────────────────────
    companion_user = _companion_user_for(character)
    identity = companion_prompt.build(
        character=character,
        session=session,
        day=day,
        user_style=style,
        user_facts=_user_profile_context(getattr(session, "user_id", None)),
        companion_profile=getattr(companion_user, "profile", None),
        sincere_inquiry=sincere_inquiry,
        tone_chip=tone_chip,
    )

    # ── stage 4: pack memory into the budget ─────────────────────────────
    from app.models import SaathiMemoryItem

    memory_items = SaathiMemoryItem.query.filter_by(session_id=session.id).all()
    open_loops = SaathiOpenLoop.query.filter_by(
        session_id=session.id, status="open").limit(5).all()
    packed = context_engine.assemble(
        session=session, identity_block=identity, user_message=user_message,
        memory_items=memory_items, open_loops=open_loops, raw_history=history)

    messages = [{"role": "system", "content": packed["system"]}]
    messages.extend(packed["history"])
    messages.append({"role": "user", "content": user_message})

    if regenerate_variant > 0:
        messages.append({"role": "system", "content": (
            "Say this differently from your last attempt — different angle "
            "entirely (a question, a tease, a memory, a reaction). Still you.")})

    # ── stage 5: generate ────────────────────────────────────────────────
    temperature = 0.9 + (regenerate_variant % 3) * 0.05
    reply = _chat(MODELS["saathi_chat"], messages,
                  temperature=temperature, max_tokens=300)
    reply = _strip_narration(reply)

    # ── stage 6: check ───────────────────────────────────────────────────
    moderation = moderate_content(reply)
    if moderation["flagged"] or not moderation["available"]:
        logger.warning("companion output withheld (flagged=%s available=%s)",
                       moderation["flagged"], moderation["available"])
        return {"reply": DEGRADED_SAATHI_MESSAGE, "segments": [DEGRADED_SAATHI_MESSAGE],
                **realism_engine.reply_plan(DEGRADED_SAATHI_MESSAGE), "moderated": True}

    # Language enforcement — the direct fix for replying in English/Devanagari to
    # a romanised-Nepali user. One re-roll only: a second failure means the model
    # cannot comply and shipping her voice beats shipping nothing.
    correction = language_engine.violates(reply, style)
    if correction:
        logger.info("language enforcement re-roll: %s", correction[:60])
        messages.append({"role": "system", "content":
                         "You broke how they write. " + correction +
                         " Rewrite your reply following that exactly."})
        try:
            retry = _strip_narration(_chat(MODELS["saathi_chat"], messages,
                                          temperature=temperature, max_tokens=300))
            if retry and not moderate_content(retry)["flagged"]:
                reply = retry
        except GroqUnavailableError:
            pass  # keep the first draft; a reply in the wrong script beats none

    context_engine.mark_recalled(packed["recalled_ids"])

    # ── stage 7: shape + time ────────────────────────────────────────────
    texting_style = getattr(character, "texting_style", None) or {}
    segments = realism_engine.segment(
        reply, burst_pref=texting_style.get("burst_pref", 2), style=style)
    plan = realism_engine.reply_plan(
        reply, presence_state=day["state"], segments=segments,
        energy=day.get("energy", "normal"))

    # ── stage 8: sometimes she is genuinely unavailable ──────────────────
    if regenerate_variant == 0 and realism_engine.should_defer(day["state"]):
        delay = realism_engine.defer_delay_seconds(day["state"], day)
        reason = realism_engine.defer_reason(day["state"], day)
        _schedule_deferred_reply(session, reply, delay, reason)
        return {"reply": "", "segments": [], "deferred": True,
                "deferred_seconds": delay, "presence_state": day["state"],
                "read_delay_seconds": plan["read_delay_seconds"],
                "typing_delay_seconds": 0.0, "segment_delays": []}

    _persist_turn(session_id, user_message, reply, defer_user_mirror=defer_user_mirror)
    _update_awaiting_reply(session, reply)
    return {"reply": reply, "segments": segments, **plan}


_NARRATION = re.compile(r"\*[^*]{1,120}\*|_[^_]{1,120}_|^\s*\([^)]{1,120}\)\s*",
                        re.MULTILINE)


def _strip_narration(text: str) -> str:
    """Remove roleplay narration (*smiles*, _laughs_, (thinking)).

    Models reach for this constantly in persona mode, and it instantly reads as
    fiction rather than a text message. The prompt forbids it; this is the belt."""
    cleaned = _NARRATION.sub("", text or "")
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def _schedule_deferred_reply(session, reply: str, delay_seconds: int,
                             reason: str) -> None:
    """Park the reply on the session and hand delivery to Celery.

    Stored on the row (not only in the task payload) so a lost broker message
    can be recovered by the sweep instead of the reply vanishing."""
    from app.extensions import db, dispatch
    from app.models.base import utcnow
    from datetime import timedelta as _timedelta

    session.deferred_reply_body = f"{reason}, {reply}" if reason else reply
    session.deferred_reply_at = utcnow() + _timedelta(seconds=delay_seconds)
    db.session.commit()
    try:
        from app.tasks.companion_tasks import deliver_deferred_reply

        dispatch(deliver_deferred_reply, str(session.id), countdown=delay_seconds)
    except Exception:  # noqa: BLE001 — the sweep will pick it up
        logger.warning("deferred reply dispatch failed; sweep will deliver")


def _update_awaiting_reply(session, reply: str) -> None:
    """Track whether she is waiting on an answer, so the initiative engine does
    not pile more messages on top of an unanswered question."""
    from app.extensions import db

    session.awaiting_user_reply = "?" in (reply or "")
    db.session.commit()


def _mock_companion_reply(session, character, user_message: str, day: dict,
                          style: dict | None, sincere_inquiry: bool) -> dict:
    """Offline twin (doc 8 §A1.10). The old mock returned coaching copy, so dev
    and every test saw a personality that no longer exists. This one runs the
    same shaping pipeline so segmentation/timing/mirroring are all exercised."""
    from app.services import realism_engine

    reply = groq_mock.companion_reply(
        session_id=str(session.id),
        character_key=getattr(character, "key", "aarohi"),
        user_message=user_message,
        style=style,
        day=day,
        turn_count=getattr(session, "turn_count", 0) or 0,
        sincere_inquiry=sincere_inquiry,
    )
    _persist_turn(str(session.id), user_message, reply)
    _update_awaiting_reply(session, reply)
    texting_style = getattr(character, "texting_style", None) or {}
    segments = realism_engine.segment(
        reply, burst_pref=texting_style.get("burst_pref", 2), style=style)
    return {"reply": reply, "segments": segments,
            **realism_engine.reply_plan(reply, presence_state=day.get("state", "free"),
                                        segments=segments,
                                        energy=day.get("energy", "normal"))}



def saathi_respond(session_id: str, character_id: str, user_message: str) -> str:
    """Compatibility wrapper returning just the reply text."""
    return saathi_respond_full(session_id, character_id, user_message)["reply"]


def _session_context(session_id: str) -> tuple[object, list[dict], list[str]]:
    from app.extensions import db
    from app.models import SaathiSession, SaathiMessage, SaathiMemoryItem

    session = db.session.get(SaathiSession, uuid_module.UUID(session_id))
    if session is None:
        raise ValueError("unknown saathi session")

    recent = (
        SaathiMessage.query.filter_by(session_id=session.id)
        .order_by(SaathiMessage.created_at.desc())
        .limit(current_app.config["SAATHI_RAW_CONTEXT_TURNS"])
        .all()
    )
    recent.reverse()
    history = [{"role": m.role if m.role == "user" else "assistant", "content": m.content}
               for m in recent]

    memory_items = SaathiMemoryItem.query.filter_by(session_id=session.id).all()
    memories = [item.summary_text for item in memory_items]
    return session, history, memories


def _persist_turn(session_id: str, user_message: str, reply: str,
                  defer_user_mirror: bool = False) -> None:
    from app.extensions import db
    from app.models import SaathiMessage, SaathiSession

    session = db.session.get(SaathiSession, uuid_module.UUID(session_id))
    if not defer_user_mirror:
        db.session.add(SaathiMessage(session_id=session.id, role="user", content=user_message))
    db.session.add(SaathiMessage(session_id=session.id, role="saathi", content=reply))
    if session is not None:
        session.turn_count += 1
        session.last_message_at = utcnow()
    db.session.commit()


def _mark_session_crisis(session_id: str) -> None:
    from app.extensions import db
    from app.models import SaathiSession

    session = db.session.get(SaathiSession, uuid_module.UUID(session_id))
    if session is not None:
        session.crisis_flagged = True
        db.session.commit()


def typing_delay_for(text: str) -> float:
    """Realistic presence layer (doc 5 §2.6): ~14 chars/sec, floor 0.8s, cap 4s."""
    return min(max(0.8, len(text or "") / 14.0), 4.0)


def summarize_session_memory(session_id: str) -> list[dict]:
    from app.models import SaathiMessage, SaathiMemoryItem

    if _mock_mode():
        from app.extensions import db
        from app.models import SaathiSession

        sid = uuid_module.UUID(session_id)
        session = db.session.get(SaathiSession, sid)
        lines = [(m.role, m.content) for m in
                 SaathiMessage.query.filter_by(session_id=sid)
                 .order_by(SaathiMessage.created_at)]
        return groq_mock.summarize_session_memory(
            lines, crisis_flagged=bool(session and session.crisis_flagged))

    existing = [i.summary_text for i in
                SaathiMemoryItem.query.filter_by(session_id=uuid_module.UUID(session_id)).all()]
    recent = (
        SaathiMessage.query.filter_by(session_id=uuid_module.UUID(session_id))
        .order_by(SaathiMessage.created_at.desc())
        .limit(40)
        .all()
    )
    recent.reverse()
    transcript = "\n".join(f"{m.role}: {m.content}" for m in recent)
    if not transcript.strip():
        return []

    excluded = "\n".join(f"- {e}" for e in existing) or "(none yet)"
    raw = _chat(
        MODELS["interview"],
        [
            {"role": "system", "content": (
                "Extract a small number of durable, short, human-readable memory notes from this "
                "conversation-practice transcript. Each note is one fact useful for future sessions "
                "(e.g. what they're practicing, preferences for feedback style). Do not include "
                "anything romantic or sensitive beyond what the user shared for practice purposes. "
                "Do not repeat these already-stored notes:\n" + excluded +
                '\nRespond as JSON: {"items": [{"summary_text": "...", "category": "..."}]}'
            )},
            {"role": "user", "content": transcript[:8000]},
        ],
        temperature=0.2,
        max_tokens=400,
        json_mode=True,
    )
    parsed = _parse_json(raw)
    items = []
    for item in parsed.get("items", []):
        summary = (item.get("summary_text") or "").strip()
        if summary and summary not in existing:
            items.append({"summary_text": summary[:280], "category": item.get("category")})
    return items


def generate_proactive_message(session_id: str, message_type: str,
                               context_note: str | None = None,
                               intimacy_level: int | None = None) -> str | None:
    """Superseded by `initiative_engine.generate` (doc 8 §C5).

    Kept as a delegating shim: the old version wrote from a fixed instruction
    table with no persona, no day context and no language mirroring, so every
    auto-text read like a notification. Its keyword dedupe now lives in
    `initiative_engine._is_repetitive`."""
    import uuid as _uuid

    from app.extensions import db
    from app.models import SaathiSession
    from app.services import initiative_engine, persona_bible, realism_engine

    session = db.session.get(SaathiSession, _uuid.UUID(session_id))
    if session is None:
        return None
    character = session.character
    schedule = None
    if character is not None and character.presence_schedule is not None:
        schedule = character.presence_schedule.schedule
    bible = (getattr(character, "persona_bible", None)
             or persona_bible.for_key(getattr(character, "key", "")))
    day = realism_engine.day_context(getattr(character, "key", ""), schedule, bible)
    return initiative_engine.generate(session, character, message_type,
                                      context_note, day)


def generate_status_post(session_id: str, character_key: str,
                         presence_activity: str | None = None) -> str | None:
    """Ambient 'her day' status post (master plan §4.5) — a WhatsApp-story-style
    one-liner about her own day. Cheap 8B call; grounded in the real day slice so
    it never contradicts what she says in chat."""
    from app.extensions import db
    from app.models import SaathiSession
    from app.services import persona_bible, realism_engine

    session = db.session.get(SaathiSession, uuid_module.UUID(session_id))
    character = getattr(session, "character", None)
    schedule = None
    if character is not None and character.presence_schedule is not None:
        schedule = character.presence_schedule.schedule
    bible = (getattr(character, "persona_bible", None)
             or persona_bible.for_key(character_key))
    day = realism_engine.day_context(character_key, schedule, bible)

    if _mock_mode():
        import random as _random

        pool = [
            f"{day.get('activity') or 'aaja'} … tired 💀",
            "momo run with hostel friends 🥟",
            "new playlist, obsessed ✨",
            "rain in kathmandu hits different 🌧️",
            day.get("incident") or "long day",
        ]
        return _random.choice(pool)

    activity = f"\nRight now: {day.get('activity') or day.get('phase')}"
    incident = f"\nSomething that happened today: {day['incident']}" if day.get("incident") else ""
    draft = _chat(
        MODELS["icebreaker"],
        [
            {"role": "system", "content": (
                f"You are {character_key}. Write ONE status line about your own day "
                "(max 12 words) — the kind of thing you'd put on WhatsApp status. "
                "Casual, lowercase, at most one emoji, Nepali-English mix fine. "
                "It is about YOUR day, never addressed to anyone."
                + activity + incident +
                ' Respond as JSON: {"body": "..."}'
            )},
        ],
        temperature=1.0,
        max_tokens=60,
        json_mode=True,
    )
    body = (_parse_json(draft).get("body") or "").strip().strip('"')
    if not body or len(body) > 140:
        return None
    moderation = moderate_content(body)
    if moderation["flagged"] or not moderation["available"]:
        return None
    return body


def extract_open_loops(session_id: str) -> list[dict]:
    """Open-loop extraction (master plan §12.2 #30): pull unfinished threads
    (promises, plans, unanswered questions) from recent turns. 8B, JSON out."""
    from app.models import SaathiMessage

    if _mock_mode():
        return []

    recent = (
        SaathiMessage.query.filter_by(session_id=uuid_module.UUID(session_id))
        .order_by(SaathiMessage.created_at.desc())
        .limit(24)
        .all()
    )
    recent.reverse()
    transcript = "\n".join(f"{m.role}: {m.content}" for m in recent)
    if not transcript.strip():
        return []

    raw = _chat(
        MODELS["prompt_grade"],
        [
            {"role": "system", "content": (
                "Extract up to 3 'open loops' from this chat: concrete unfinished "
                "threads the user mentioned (e.g. a promise to share something, an "
                "upcoming event, a plan, a question the user left hanging). Only "
                "extract things the USER mentioned, phrased as short follow-up "
                "questions a companion could ask later. "
                'Respond as JSON: {"loops": [{"description": "...", "followup_after_hours": 24}]}'
            )},
            {"role": "user", "content": transcript[:6000]},
        ],
        temperature=0.2,
        max_tokens=300,
        json_mode=True,
    )
    loops = []
    for loop in _parse_json(raw).get("loops", [])[:3]:
        desc = (loop.get("description") or "").strip()
        if desc:
            try:
                hours = max(1, min(int(loop.get("followup_after_hours", 24)), 336))
            except (TypeError, ValueError):
                hours = 24
            loops.append({"description": desc[:200], "followup_after_hours": hours})
    return loops


def transcribe_audio(audio_bytes: bytes) -> str:
    if _mock_mode():
        return groq_mock.transcribe_audio(audio_bytes)
    resp = _groq_request(
        "POST", "/audio/transcriptions",
        data={"model": MODELS["transcription"], "response_format": "json"},
        files={"file": ("audio.webm", audio_bytes, "audio/webm")},
        timeout=60.0,
    )
    return resp.json().get("text", "").strip()


def synthesize_speech(text: str, voice_key: str | None = None) -> bytes:
    """TTS provider chain (master plan §12.1 — Groq deprecated playai-tts and
    its replacement is capped at 100 req/day with no Nepali):
      1. ElevenLabs Flash (Hindi, ~75ms) when ELEVENLABS_API_KEY is set
      2. edge-tts (free; native ne-NP voices per character, hi-IN, en-US)
      3. Groq TTS — dev-only fallback
      4. mock mode: WAV-rendering twin from groq_mock
    """
    if _mock_mode():
        return groq_mock.synthesize_speech(text)

    voice_name = CHARACTER_TTS_VOICES.get(voice_key or "", None)
    eleven_key = current_app.config.get("ELEVENLABS_API_KEY")

    # 1 — ElevenLabs when configured (multilingual v2 maps Hindi; ne-NP text
    # still renders acceptably through the multilingual model)
    if eleven_key:
        try:
            voice_id = current_app.config.get("ELEVENLABS_VOICE_ID") or "21m00Tcm4TlvDq8ikWAM"
            resp = _session.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={"xi-api-key": eleven_key, "Content-Type": "application/json"},
                json={
                    "text": text[:4000],
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.55, "similarity_boost": 0.75},
                },
                timeout=30.0,
            )
            if resp.status_code == 200 and resp.content:
                return resp.content
            logger.warning("ElevenLabs TTS failed: %s %s", resp.status_code, resp.text[:200])
        except requests.RequestException:
            logger.exception("ElevenLabs TTS unreachable; falling back")

    # 2 — edge-tts with the character's native voice (Nepali ne-NP when mapped)
    try:
        import asyncio
        import edge_tts

        target_voice = voice_name or CHARACTER_TTS_VOICES["en"]

        async def _render(voice: str) -> bytes | None:
            communicate = edge_tts.Communicate(text[:4000], voice)
            buffer = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buffer.extend(chunk["data"])
            return bytes(buffer) or None

        audio = asyncio.run(_render(target_voice))
        if audio:
            return audio
        # some edge voices intermittently fail; retry with hi-IN then en-US
        for fallback_voice in ("hi-IN-MadhurNeural", CHARACTER_TTS_VOICES["en"]):
            audio = asyncio.run(_render(fallback_voice))
            if audio:
                return audio
    except ImportError:
        logger.warning("edge-tts not installed")

    # 3 — Groq dev-only fallback
    try:
        resp = _groq_request(
            "POST", "/audio/speech",
            json_body={"model": MODELS["tts"], "voice": TTS_VOICE, "input": text[:4000],
                       "response_format": "mp3"},
            timeout=60.0,
        )
        return resp.content
    except GroqUnavailableError:
        raise GroqUnavailableError("no TTS backend available")


def saathi_voice_respond(session_id: str, character_id: str, audio_bytes: bytes) -> bytes:
    transcript = transcribe_audio(audio_bytes)
    if not transcript:
        raise GroqUnavailableError("empty transcription")
    reply = saathi_respond(session_id, character_id, transcript)
    return synthesize_speech(reply)


def generate_bio(notes: str, interview_tags: dict, language: str) -> list[str]:
    if _mock_mode() and not check_prompt_injection(notes):
        return groq_mock.generate_bio(notes, interview_tags or {}, language)
    if check_prompt_injection(notes):
        raise ValueError("input rejected by prompt-injection guard")
    lang_instruction = {
        "ne": "Write each bio in natural Nepali (Devanagari).",
        "mixed": "Write bios mixing Nepali and English the way urban Nepali speakers code-switch.",
    }.get(language, "Write each bio in English.")
    tags_block = json.dumps(interview_tags or {}, ensure_ascii=False)
    raw = _chat(
        MODELS["bio"],
        [
            {"role": "system", "content": (
                "You write dating-profile bios for Milan, a Nepal-first dating app. Produce exactly "
                "3 distinct bio drafts as JSON. Rules: no fabricated claims beyond the user's own "
                "notes and tags; no generic filler like 'I love to laugh and have fun'; match the "
                "register of the user's notes; each draft under 300 characters; sound human, warm, specific. "
                + lang_instruction +
                ' Respond as JSON: {"drafts": ["...", "...", "..."]}'
            )},
            {"role": "user", "content": f"Notes:\n{notes[:3000]}\n\nInterview tags:\n{tags_block}"},
        ],
        temperature=0.9,
        max_tokens=700,
        json_mode=True,
    )
    drafts = [d.strip()[:300] for d in _parse_json(raw).get("drafts", []) if isinstance(d, str)]
    safe_drafts = []
    for draft in drafts:
        moderation = moderate_content(draft)
        if not moderation["flagged"]:
            safe_drafts.append(draft)
    return safe_drafts


def grade_prompt(prompt_answer: str) -> dict:
    if _mock_mode():
        return groq_mock.grade_prompt(prompt_answer)
    if check_prompt_injection(prompt_answer):
        return {"tag": "rejected", "suggestion": "Please rewrite without embedded instructions."}
    raw = _chat(
        MODELS["prompt_grade"],
        [
            {"role": "system", "content": (
                "Grade a dating-app prompt answer. Return JSON with \"tag\" (one of: specific, generic, "
                "could-read-as-a-red-flag) and \"suggestion\" (ONE kind, concrete sentence with a specific fix — "
                "never just 'this is bad')."
            )},
            {"role": "user", "content": prompt_answer[:1500]},
        ],
        temperature=0.2,
        max_tokens=140,
        json_mode=True,
    )
    parsed = _parse_json(raw)
    tag = parsed.get("tag") if parsed.get("tag") in {"specific", "generic", "could-read-as-a-red-flag"} else "generic"
    return {"tag": tag, "suggestion": (parsed.get("suggestion") or "")[:300]}


def suggest_icebreakers(match_context: dict) -> list[str]:
    context_block = json.dumps(match_context or {}, ensure_ascii=False)
    if _mock_mode() and not check_prompt_injection(context_block):
        return groq_mock.suggest_icebreakers(match_context or {})
    if check_prompt_injection(context_block):
        return []
    raw = _chat(
        MODELS["icebreaker"],
        [
            {"role": "system", "content": (
                "Generate exactly 3 short opening-message suggestions for a dating-app match, grounded ONLY "
                "in the provided shared context. Friendly, specific, never generic pickup lines. "
                'Respond as JSON: {"suggestions": ["...", "...", "..."]}'
            )},
            {"role": "user", "content": context_block[:2500]},
        ],
        temperature=0.9,
        max_tokens=220,
        json_mode=True,
    )
    suggestions = [s.strip()[:200] for s in _parse_json(raw).get("suggestions", []) if isinstance(s, str)]
    return [s for s in suggestions if not moderate_content(s)["flagged"]][:3]


def explain_match(shared_signals: dict) -> str:
    if _mock_mode():
        return groq_mock.explain_match(shared_signals or {})
    signals_block = json.dumps(shared_signals or {}, ensure_ascii=False)
    raw = _chat(
        MODELS["match_explainer"],
        [
            {"role": "system", "content": (
                "Explain why two people matched on a dating app, in 1-2 warm sentences. STRICTLY GROUNDED: "
                "reference ONLY the structured signals provided. Never invent shared interests, facts, or "
                "details not present in the data. This is a trust feature; fabrication is worse than omission."
            )},
            {"role": "user", "content": signals_block[:2000]},
        ],
        temperature=0.5,
        max_tokens=120,
    )
    return raw.strip()


def kundali_mode_narrative(birth_details_a: dict, birth_details_b: dict) -> str:
    if _mock_mode():
        narrative = groq_mock.kundali_mode_narrative(birth_details_a, birth_details_b)
        moderation = moderate_content(narrative)
        return narrative if not moderation["flagged"] else ""
    details = json.dumps({"person_a": birth_details_a, "person_b": birth_details_b}, ensure_ascii=False)
    raw = _chat(
        MODELS["kundali"],
        [
            {"role": "system", "content": (
                "Write a Kundali (Vedic astrology) compatibility narrative for a Nepal-first dating app. "
                "Frame it explicitly as a fun cultural tradition and conversation piece — NEVER as a "
                "deterministic or scientific measure, never something that overrides real compatibility "
                "signals. Warm, culturally fluent tone; reference traditional kundali concepts (guna milan, "
                "rashi, nakshatra) where the birth details support it. 2-4 short paragraphs. End with one "
                "light conversation-starter suggestion."
            )},
            {"role": "user", "content": details[:2500]},
        ],
        temperature=0.8,
        max_tokens=500,
    )
    narrative = raw.strip()
    moderation = moderate_content(narrative)
    return narrative if not moderation["flagged"] else ""


def extract_interview_signal(qa_pairs: list[dict]) -> dict:
    if _mock_mode() and not check_prompt_injection(str(qa_pairs)):
        return groq_mock.extract_interview_signal(qa_pairs)
    qa_text = "\n".join(
        f"Q: {pair.get('question', '')}\nA: {pair.get('answer', '')}" for pair in qa_pairs
    )
    if check_prompt_injection(qa_text):
        return {}
    raw = _chat(
        MODELS["interview"],
        [
            {"role": "system", "content": (
                "Extract structured preference data from an onboarding interview. Fields exactly: "
                "relationship_intent (string), lifestyle_tags (array), values_tags (array), "
                "dealbreakers (array), conversation_style (one of: direct/playful/thoughtful). "
                "Only use what the answers actually support; empty arrays when unknown. "
                'Respond as JSON.'
            )},
            {"role": "user", "content": qa_text[:8000]},
        ],
        temperature=0.1,
        max_tokens=400,
        json_mode=True,
    )
    return _parse_json(raw)


def generate_weekly_recap(activity: dict) -> str:
    """Weekly private match recap (doc 1 §4.5): AI-generated, personal-only.
    Strictly grounded in the provided activity data; never comparative or
    ranked against other users (guardrail #4)."""
    if _mock_mode():
        return groq_mock.weekly_recap(activity or {})
    if check_prompt_injection(str(activity)):
        raise ValueError("input rejected by prompt-injection guard")
    raw = _chat(
        MODELS["match_explainer"],
        [
            {"role": "system", "content": (
                "Write a short, warm, private weekly recap for one dating-app user "
                "(2-4 sentences). STRICTLY GROUNDED: reference only the supplied "
                "activity numbers and facts. Never compare the user to other people, "
                "never rank them. End with one gentle, concrete suggestion for next week."
            )},
            {"role": "user", "content": str(activity)[:2000]},
        ],
        temperature=0.6,
        max_tokens=160,
    )
    return raw.strip()


def synthesize_speech_stream(text: str):
    """Sentence-level TTS chunking (doc 5 §2.7): yields audio bytes per sentence
    so clients can start playback before synthesis completes."""
    import re as _re

    sentences = [s.strip() for s in _re.split(r"(?<=[.!?।])\s+", text.strip()) if s.strip()]
    chunks = sentences or [text]
    buffered: list[bytes] = []
    current: list[str] = []
    for sentence in chunks:
        current.append(sentence)
        if len(" ".join(current)) >= 120:
            try:
                buffered.append(synthesize_speech(" ".join(current)))
            except GroqUnavailableError:
                pass
            current = []
    if current:
        try:
            buffered.append(synthesize_speech(" ".join(current)))
        except GroqUnavailableError:
            pass
    yield from buffered


# ---------------------------------------------------------------------------
# Phase 3 / Phase 4 generators (master plan roadmap) — all mock-safe and
# degrade gracefully; content passes the same gates as chat.
# ---------------------------------------------------------------------------

def generate_diary_entry(session_id: str, character_key: str) -> dict | None:
    """Companion diary (#29): a reflective end-of-day entry grounded in the
    session's real recent chat. Returns None on degraded AI."""
    from app.models import SaathiMessage

    recent = (SaathiMessage.query.filter_by(session_id=uuid_module.UUID(session_id))
              .order_by(SaathiMessage.created_at.desc()).limit(24).all())
    recent.reverse()
    transcript = "\n".join(f"{m.role}: {m.content}" for m in recent)[:4000]
    if _mock_mode():
        return {"title": "today, in fragments", "mood": "reflective",
                "body": "thought about our chat today. same time tomorrow?"}
    try:
        raw = _chat(
            MODELS["saathi_chat"],
            [
                {"role": "system", "content": (
                    "You are writing a private diary entry as an AI companion "
                    "(Milan app, Nepal). Reflect warmly on today's conversation "
                    "with the user — what they shared, how they seemed, one small "
                    "hope for tomorrow. Stay AI-honest (it's your diary as an AI; "
                    "never claim a human body or human outings). 80-140 words, "
                    "casual lowercase style."
                )},
                {"role": "user", "content": f"Today's chat:\n{transcript or '(quiet day, no chats)'}"},
            ],
            temperature=0.8, max_tokens=400,
        )
    except GroqUnavailableError:
        return None
    body = raw.strip()
    if not body:
        return None
    title_m = re.search(r"^(.{5,60}?)[\n:]", body)
    return {"title": (title_m.group(1).strip() if title_m else "today"),
            "body": body, "mood": None}


def generate_mirror_question(session_id: str, character_key: str) -> dict | None:
    """Mirror Questions (#39): one reflective question personalized from
    memory. Answer feeds persona evolution."""
    memories = _session_context(session_id)[2]
    memory_note = "\n".join(f"- {m}" for m in memories[-8:]) or "(new user)"
    if _mock_mode():
        return {"question": "what's one small thing that made today better than yesterday?"}
    try:
        raw = _chat(
            MODELS["icebreaker"],
            [
                {"role": "system", "content": (
                    "Ask ONE short reflective question (max 20 words) tailored to "
                    "what you know about this user. Gentle, curious, never "
                    "interrogating, never romantic beyond the current stage. "
                    "Return just the question text."
                )},
                {"role": "user", "content": memory_note},
            ],
            temperature=0.9, max_tokens=120,
        )
    except GroqUnavailableError:
        return None
    q = raw.strip().strip('"')
    return {"question": q} if q else None


def generate_quest(session_id: str, character_key: str, kind: str = "duo") -> dict | None:
    """Duo quests / streak rituals (Phase 4). kind: duo|streak|festival."""
    if _mock_mode():
        return {"title": "share one song that fits this week",
                "description": "each send one track, compare notes tomorrow",
                "reward_points": 10}
    try:
        raw = _chat(
            MODELS["icebreaker"],
            [
                {"role": "system", "content": (
                    "Design ONE tiny duo activity for an AI companion and a user "
                    "(Milan app, Nepal). kind=" + kind + ". It must be doable in "
                    "chat (share a song, a photo of the sky, a 3-question quiz, a "
                    "gratitude list...). Safe, warm, zero pressure, never "
                    "financial, never offline-meeting pressure. Return JSON: "
                    '{"title": "...", "description": "one line", "reward_points": 10}'
                )},
            ],
            temperature=0.9, max_tokens=200, json_mode=True,
        )
    except GroqUnavailableError:
        return None
    parsed = _parse_json(raw)
    if not parsed.get("title"):
        return None
    return {"title": str(parsed["title"])[:160],
            "description": str(parsed.get("description") or "")[:400],
            "reward_points": int(parsed.get("reward_points") or 10)}


def generate_capsule_content(session_id: str, character_key: str,
                             occasion: str) -> dict | None:
    """Moment Capsules (Phase 4): companion seals a letter to be opened later."""
    memories = _session_context(session_id)[2]
    memory_note = "\n".join(f"- {m}" for m in memories[-10:])
    if _mock_mode():
        return {"title": "sealed for later", "content": "open me when you need a smile."}
    try:
        raw = _chat(
            MODELS["saathi_chat"],
            [
                {"role": "system", "content": (
                    "Write a short sealed note (60-120 words) from an AI companion "
                    "to the user, to be opened " + occasion + ". Reference shared "
                    "memories lightly, stay AI-honest, warm not heavy. Return JSON: "
                    '{"title": "...", "content": "..."}'
                )},
                {"role": "user", "content": memory_note or "(new bond)"},
            ],
            temperature=0.8, max_tokens=350, json_mode=True,
        )
    except GroqUnavailableError:
        return None
    parsed = _parse_json(raw)
    if not parsed.get("content"):
        return None
    return {"title": str(parsed.get("title") or "sealed for you")[:160],
            "content": str(parsed["content"])[:1200]}


def generate_recap_narrative(payload: dict) -> str | None:
    """Milan Recap (#17) narrative line — strictly grounded in the payload
    (same rule as explain_match); no invented facts."""
    if _mock_mode():
        return "a week of small conversations that added up"
    try:
        raw = _chat(
            MODELS["match_explainer"],
            [
                {"role": "system", "content": (
                    "One warm sentence (max 24 words) summarizing this companion "
                    "stats payload. STRICTLY GROUNDED in the numbers — invent "
                    "nothing, no comparisons to other people, no ranking."
                )},
                {"role": "user", "content": str(payload)[:1500]},
            ],
            temperature=0.6, max_tokens=120,
        )
    except GroqUnavailableError:
        return None
    return raw.strip().strip('"') or None


# ---------------------------------------------------------------------------
# §16 companion visual identity: every character has ONE locked face prompt.
# Every generated image uses it (plus the scene) so the same face appears
# across all sends — never a different person. Illustrated style + explicit
# no-photoreal-human ban keeps the AI-labeled fiction safe (master plan §12.1).
# ---------------------------------------------------------------------------

COMPANION_FACE_PROMPTS = {
    "aarohi": (
        "portrait illustration of a 23-year-old Nepali woman, heart-shaped face, warm brown "
        "eyes, long black hair with a loose wave, small nose stud, wearing a mustard sweater, "
        "soft smile, Kathmandu cafe bokeh background"
    ),
    "nishan": (
        "portrait illustration of a 25-year-old Nepali man, square jaw, short black hair, "
        "light stubble, thick eyebrows, wearing a charcoal hoodie, relaxed friendly expression, "
        "Pokhara lakeside bokeh background"
    ),
    "sneha": (
        "portrait illustration of a 22-year-old Nepali woman, oval face, long straight black "
        "hair with a middle part, warm dark eyes, wearing a teal kurta, gentle smile, Bhaktapur "
        "brick lane softly blurred behind"
    ),
    "deepak": (
        "portrait illustration of a 28-year-old Nepali man, weathered tan skin, short black "
        "hair, trimmed beard, wearing an olive trekking jacket, broad easy grin, terraced hills "
        "of Baglung blurred behind"
    ),
    "pooja": (
        "portrait illustration of a 24-year-old Madhesi Nepali woman, round face, expressive "
        "dark eyes, long black hair with a red clip, small bindi, wearing a bright orange "
        "kurti, playful half-smile, Janakpur market colors blurred behind"
    ),
    "kiran": (
        "portrait illustration of a 27-year-old Newar Nepali man, lean face, black-framed "
        "glasses, neat black hair, wearing a navy shirt, wry closed-lip smile, Patan Durbar "
        "square architecture softly blurred"
    ),
    "riya": (
        "portrait illustration of a 24-year-old Nepali-American woman, heart-shaped face, "
        "shoulder-length wavy black hair with caramel highlights, gold hoops, wearing a denim "
        "jacket, bright candid laugh, Kathmandu rooftop cafe blurred behind"
    ),
    "asha": (
        "portrait illustration of a 24-year-old Nepali woman, soft round face, kind brown "
        "eyes, long braided black hair, wearing a maroon sweater, encouraging smile, warm "
        "plain background"
    ),
    "bibek": (
        "portrait illustration of a 25-year-old Nepali man, angular face, tousled black hair, "
        "clean shaven, wearing a graphic tee and open flannel, teasing smirk, casual plain "
        "background"
    ),
    "priya": (
        "portrait illustration of a 26-year-old Nepali woman, calm oval face, gentle brown "
        "eyes, low black bun, wearing a sage-green shawl, patient warm smile, soft plain "
        "background"
    ),
    "sagar": (
        "portrait illustration of a 27-year-old Nepali man, strong jaw, short black hair, "
        "light stubble, wearing a grey henley, direct confident expression, soft plain "
        "background"
    ),
}


def companion_face_prompt(character_key: str, scene: str) -> str:
    """Identity-locked prompt: character face + user scene, illustration-only."""
    face = COMPANION_FACE_PROMPTS.get(character_key, COMPANION_FACE_PROMPTS["asha"])
    return (
        f"{face}. Scene: {scene[:220]}. Same exact person as the base portrait — "
        "consistent facial structure. Stylized illustrated art, NOT a photograph, "
        "no real human likeness."
    )


def generate_companion_image(character_key: str, scene: str) -> dict:
    """Generate an illustrated moment of THIS companion. Raises
    ImageGenUnavailableError through the shared service."""
    from app.services.image_gen_service import generate_image

    return generate_image(companion_face_prompt(character_key, scene))
