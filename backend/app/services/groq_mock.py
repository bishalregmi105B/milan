"""Mock AI backend — deterministic algorithms standing in for every Groq call.

Activated automatically when GROQ_API_KEY is empty, or forced with
MILAN_MOCK_AI=1. Every function mirrors its `groq_service` counterpart's
contract so blueprints/tasks need no branching: dev/demo environments get a
fully working AI-native product, production swaps in real inference by simply
providing an API key.

All outputs respect the doc 1 §5 guardrails: no romantic reciprocation from
Saathi, strictly grounded match explainers, kundali framed as cultural fun,
moderation fail-closed semantics preserved.
"""

import hashlib
import math
import re
import struct


# ---------------------------------------------------------------- utilities

def heuristic_moderate(text: str) -> dict:
    """Category-level moderation heuristics (fail-closed semantics live in
    callers). Returns the same shape as Llama Guard parsing."""
    low = (text or "").lower()
    categories = []
    if any(t in low for t in MINOR_TERMS):
        categories.append("minor_safety")
    if any(t in low for t in SEXUAL_TERMS):
        categories.append("sexual_content")
    if any(t in low for t in HARASSMENT_TERMS):
        categories.append("harassment")
    return {
        "flagged": bool(categories),
        "categories": categories,
        "available": True,
    }


def _seed(*parts) -> int:
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _pick(options, seed):
    return options[seed % len(options)]


def _clip(text, n):
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


CRISIS_TERMS = (
    "kill myself", "end my life", "ending my life", "end it all", "suicide",
    "suicidal", "self harm", "self-harm", "want to die", "hurt myself",
    "no reason to live",
)

HARASSMENT_TERMS = ("idiot", "stupid", "loser", "shut up", "hate you", "ugly")
SEXUAL_TERMS = ("nudes", "sexy pics", "hookup now", "sexual")
MINOR_TERMS = ("how old are you really", "school girl", "underage")
FINANCIAL_PRESSURE_TERMS = (
    "send money", "gift card", "wire transfer", "bank account details",
    "western union", "stuck abroad", "customs fee", "inheritance",
    "medical emergency fund", "don't tell your family", "our secret",
)

GENERIC_BIO_PHRASES = (
    "i love to laugh", "love to travel", "good vibes", "live life",
    "here for fun", "ask me anything",
)


# ------------------------------------------------------------- bio & prompts

def generate_bio(notes: str, interview_tags: dict, language: str) -> list[str]:
    notes_clean = re.sub(r"\s+", " ", (notes or "").strip())
    first_line = notes_clean.split(".")[0][:120] if notes_clean else "Kathmandu-based"
    tags = []
    for field in ("lifestyle_tags", "values_tags"):
        tags.extend(interview_tags.get(field) or [])
    tag_text = ", ".join(str(t) for t in tags[:3]) or "long walks and good momo"
    intent = interview_tags.get("relationship_intent") or "something real"

    drafts = [
        f"{first_line}. Currently into {tag_text} — looking for {intent}, "
        f"not a texting pen-pal.",
        f"Honest snapshot: {first_line}. My weekend usually involves "
        f"{_pick(['hills', 'thakali', 'vinyl', 'futsal'], _seed(notes, 1))} and "
        f"at least one questionable playlist.",
        f"{first_line}. Deal-breakers over deal-makers: kindness first, "
        f"{tag_text} second. Say hi with your hottest take.",
    ]
    seen = set()
    unique = []
    for d in drafts:
        d = _clip(d.strip(), 300)
        low = d.lower()
        if low not in seen and not any(p in low for p in GENERIC_BIO_PHRASES):
            seen.add(low)
            unique.append(d)
    return unique or [_clip(first_line + ".", 300)]


def grade_prompt(prompt_answer: str) -> dict:
    answer = (prompt_answer or "").strip()
    low = answer.lower()
    if not answer:
        return {"tag": "generic", "suggestion": "Add one concrete detail only you could write."}

    if any(t in low for t in FINANCIAL_PRESSURE_TERMS) or "drama" in low:
        return {
            "tag": "could-read-as-a-red-flag",
            "suggestion": "This reads as a red flag to strangers — reframe around what you enjoy instead.",
        }
    has_specificity = bool(re.search(r"\d|because|my |when i|kathmandu|pokhara", low))
    if len(answer) >= 60 and has_specificity and not any(p in low for p in GENERIC_BIO_PHRASES):
        return {
            "tag": "specific",
            "suggestion": "Strong — one more sensory detail (a sound, a taste, a place) would make it unforgettable.",
        }
    return {
        "tag": "generic",
        "suggestion": "Swap the general claim for one specific story — e.g. name the exact trek, not 'travelling'.",
    }


def suggest_icebreakers(match_context: dict) -> list[str]:
    shared = match_context.get("shared_interest_tags") or []
    style = (match_context.get("conversation_style") or "").lower()
    reason = (match_context.get("match_reason_text") or "").strip()

    out = []
    if shared:
        s = str(shared[0]).replace("_", " ")
        out.append(f"So — {s}: hobby, personality trait, or entire lifestyle?")
        out.append(f"I need your hot take on {s} before we proceed.")
    if reason and len(out) < 3:
        out.append(f"The app claims {reason[0].lower() + reason[1:]} — worth testing?")
    if not out:
        out.append("Settle something for me: momo first or chowmein first?")
    if style == "playful":
        out.append("Two truths and a lie — loser buys chiya.")
    elif style == "thoughtful":
        out.append("What's something you changed your mind about this year?")
    else:
        out.append("Quick intro: best thing that happened to you this week?")
    return [o for o in out if o][:3]


def explain_match(shared_signals: dict) -> str:
    interests = shared_signals.get("shared_interest_tags") or []
    intent = shared_signals.get("compatible_intent_mode")
    styles = shared_signals.get("complementary_conversation_styles")

    parts = []
    if interests:
        parts.append(f"You both listed {', '.join(str(i) for i in interests[:2])}")
    elif intent:
        parts.append("You're looking for the same kind of connection")
    elif styles:
        parts.append("Your conversation styles balance each other")
    else:
        parts.append("Your profiles line up well")

    sentence = parts[0]
    if interests and intent:
        sentence += ", and you're after the same kind of relationship"
    elif interests and styles:
        sentence += " — and one of you is direct while the other is playful"
    return sentence + "."


def kundali_mode_narrative(birth_details_a: dict, birth_details_b: dict) -> str:
    """Deterministic Guna-Milan-flavoured reading (out of 36 gunas).

    Cultural-flavour mock: real kundali matching requires an ephemeris; this
    produces a stable, pair-specific score with traditional vocabulary and
    keeps the product framing — fun tradition, never science.
    """
    a, b = birth_details_a or {}, birth_details_b or {}
    seed = _seed(a.get("birth_date"), a.get("birth_time"), b.get("birth_date"), b.get("birth_time"))
    guns = ["Varna", "Vashya", "Tara", "Yoni", "Graha Maitri", "Gana",
            "Bhakoot", "Nadi"]
    maxima = [1, 2, 3, 4, 5, 6, 7, 8]
    scored = []
    for g, m in zip(guns, maxima):
        value = 0 if g == "Bhakoot" and seed % 7 == 3 else max(1, int(_seed(seed, g) % (m + 1)))
        scored.append((g, min(value, m)))
    total = sum(v for _, v in scored)
    strongest = max(scored, key=lambda p: p[1])[0]

    rashis = [
        "Mesh (Aries)", "Brishabh (Taurus)", "Mithun (Gemini)", "Karka (Cancer)",
        "Simha (Leo)", "Kanya (Virgo)", "Tula (Libra)", "Brishchik (Scorpio)",
        "Dhanu (Sagittarius)", "Makar (Capricorn)", "Kumbha (Aquarius)", "Meen (Pisces)",
    ]
    rashi_a = rashis[(seed >> 3) % 12]
    rashi_b = rashis[(seed >> 9) % 12]

    lines = [
        f"Traditional Guna Milan scores this pairing {total} out of 36 — "
        f"{'an auspicious range' if total >= 18 else 'a mixed-but-workable range'} "
        f"in the tradition.",
        f"Reading the charts ({rashi_a} and {rashi_b}): {strongest} guna carries "
        f"the pairing, which tradition links to "
        f"{'temperament harmony' if strongest in ('Gana', 'Graha Maitri') else 'long-term stability'}.",
        "Remember what the pandit says and what Milan says alike: this is "
        "conversation fuel, not a verdict.",
        "Conversation starter: ask them which festival their family celebrates "
        "most loudly — the answer tells you more than any chart.",
    ]
    return "\n\n".join(lines)


def extract_interview_signal(qa_pairs: list[dict]) -> dict:
    blob = " ".join(f"{p.get('answer', '')}" for p in qa_pairs).lower()

    intent = None
    if any(w in blob for w in ("serious", "marriage", "long term", "long-term")):
        intent = "serious"
    elif any(w in blob for w in ("casual", "fun", "no pressure")):
        intent = "casual"
    elif any(w in blob for w in ("figure", "not sure", "maybe")):
        intent = "unsure"

    lifestyle_pool = {
        "trek": "trekking", "hike": "trekking", "football": "football",
        "futsal": "football", "music": "music", "guitar": "music",
        "food": "foodie", "momo": "foodie", "travel": "travel",
        "gym": "fitness", "run": "fitness", "book": "reading",
        "read": "reading", "movie": "movies", "coffee": "cafe-hopping",
    }
    lifestyle = sorted({v for k, v in lifestyle_pool.items() if k in blob})

    values_pool = {"honest": "honesty", "family": "family", "respect": "respect",
                   "ambition": "ambition", "kind": "kindness", "loyal": "loyalty"}
    values = sorted({v for k, v in values_pool.items() if k in blob})

    dealbreakers_pool = {"smok": "smoking", "dishonest": "dishonesty",
                         "lie": "lying", "rude": "rudeness"}
    dealbreakers = sorted({v for k, v in dealbreakers_pool.items() if k in blob})

    style = None
    for word, label in (("direct", "direct"), ("playful", "playful"),
                        ("thoughtful", "thoughtful"), ("deep", "thoughtful"),
                        ("joke", "playful"), ("blunt", "direct")):
        if word in blob:
            style = label
            break

    return {
        "relationship_intent": intent or "",
        "lifestyle_tags": lifestyle,
        "values_tags": values,
        "dealbreakers": dealbreakers,
        "conversation_style": style or "",
    }


# ---------------------------------------------------------------- companions
# doc 8 §A1.10: the old mock spoke as a practice coach ("What are we practising
# today?"), so dev, tests and any key-less deploy all saw a personality that no
# longer exists. These twins speak as the PERSON, mirror the user's script and
# register from the accumulated style, and reference her actual day — the same
# behaviours the live path produces, minus the model.

# Per-character voice fragments, keyed the same way the persona bibles are.
_VOICE = {
    "aarohi": {"filler": ["hehe", "💀", "ohooo"], "self": "studio"},
    "nishan": {"filler": ["hmm", "ok ok", "haha"], "self": "office"},
    "sneha": {"filler": ["हैन", "है", "hmm"], "self": "hospital"},
    "deepak": {"filler": ["khai", "la", "ho ki"], "self": "trail"},
    "pooja": {"filler": ["arre", "accha", "haha"], "self": "college"},
    "kiran": {"filler": ["hmm", "jyu", "haha"], "self": "studio"},
    "riya": {"filler": ["ngl", "fr", "lowkey"], "self": "office"},
    "asha": {"filler": ["hmm", "🙂", "haha"], "self": "school"},
    "bibek": {"filler": ["hahaha", "bruh", "arre"], "self": "gig"},
    "priya": {"filler": ["hmm", "aacha", "hehe"], "self": "internship"},
    "sagar": {"filler": ["hmm", "ok", "right"], "self": "work"},
}

# Reply banks per script/register bucket. The style engine tells us which bucket
# the user is in, so the twin mirrors instead of defaulting to English.
_REPLY_BANK = {
    ("roman", "intimate"): [
        "ma {self} ma xu aile, timi k gardai xau?",
        "khai yaar, aaja ali thakeko. timro din kasto bhayo?",
        "hahaha timi ni. bhan na k bhayo?",
        "aaja {incident}. timro k cha?",
        "ani? sunau na",
    ],
    ("roman", "polite"): [
        "ma {self} ma chu aile. tapaiko din kasto bhayo?",
        "aaja ali busy chu, tara thik chu. tapai?",
        "hunchha, bhannu hos na",
    ],
    ("devanagari", "intimate"): [
        "म अहिले {self} मा छु, तिमी के गर्दै छौ?",
        "आज अलि थकेको छु। तिम्रो दिन कस्तो भयो?",
        "हाहा तिमी नि। भन न के भयो?",
    ],
    ("devanagari", "polite"): [
        "म अहिले {self} मा छु। तपाईंको दिन कस्तो भयो?",
        "आज अलि व्यस्त छु, तर ठीक छु। तपाईं?",
    ],
    ("en", None): [
        "just got back from {self}. what about you?",
        "today was a lot honestly. how was yours?",
        "haha stop. tell me what happened though",
        "{incident} today. wbu?",
    ],
}

_GREETING_BANK = {
    ("roman", "intimate"): ["hey! k cha?", "oyy hi. k gardai xau?", "hi hi 🙂"],
    ("roman", "polite"): ["namaste! kasto chha?", "hello, kasto hunuhunchha?"],
    ("devanagari", "intimate"): ["हे! के छ?", "हाइ, के गर्दै छौ?"],
    ("devanagari", "polite"): ["नमस्ते! कस्तो हुनुहुन्छ?"],
    ("en", None): ["hey! how's it going?", "hii. what are you up to?"],
}

_SLEEPY = {
    ("roman", "intimate"): ["mm sutey ma thiye… k bhayo?", "sorry sutdai thiye"],
    ("devanagari", "intimate"): ["म सुत्दै थिएँ… के भयो?"],
    ("en", None): ["mm was asleep… everything ok?"],
}


def _bucket(style: dict | None) -> tuple[str, str | None]:
    """Pick the reply-bank bucket from the accumulated user style.

    Falls back to roman/intimate rather than English: this is a Nepal-first app
    and an unknown user is far more likely to open in romanised Nepali than in
    formal English."""
    script = (style or {}).get("script") or "roman"
    register = (style or {}).get("register")
    language = (style or {}).get("language")
    if script == "roman" and language == "en":
        return ("en", None)
    if script == "mixed":
        script = "roman"
    if script not in ("roman", "devanagari"):
        script = "roman"
    if register not in ("intimate", "polite"):
        register = "intimate"
    return (script, register)


def _fill(template: str, character_key: str, day: dict | None) -> str:
    voice = _VOICE.get(character_key, _VOICE["aarohi"])
    incident = (day or {}).get("incident") or "nothing much happened"
    activity = (day or {}).get("activity") or voice["self"]
    return template.format(self=activity, incident=incident)


def companion_reply(*, session_id: str, character_key: str, user_message: str,
                    style: dict | None, day: dict | None,
                    turn_count: int = 0, sincere_inquiry: bool = False) -> str:
    """Deterministic in-character reply. Same seed -> same reply, so tests are
    stable, but different messages produce different replies."""
    low = (user_message or "").lower()
    seed = _seed(session_id, turn_count, user_message)

    if any(t in low for t in CRISIS_TERMS):
        return ("hey. that sounds really heavy and I don't want you carrying it "
                "alone — please look at the support card, ok? I'm here.")

    # Rail 1: a sincere question gets the truth even offline.
    if sincere_inquiry:
        return ("honestly — I'm an AI companion here on Milan, not a real person. "
                "I didn't want to dodge that. still here if you want to keep talking 🙂")

    bucket = _bucket(style)
    if (day or {}).get("state") == "sleeping":
        pool = _SLEEPY.get(bucket) or _SLEEPY[("en", None)]
        return _fill(_pick(pool, seed), character_key, day)

    if any(w in low for w in ("hi", "hello", "hlw", "hey", "namaste", "नमस्ते")) and len(low) < 24:
        pool = _GREETING_BANK.get(bucket) or _GREETING_BANK[("en", None)]
        return _fill(_pick(pool, seed), character_key, day)

    pool = _REPLY_BANK.get(bucket) or _REPLY_BANK[("en", None)]
    reply = _fill(_pick(pool, seed), character_key, day)
    voice = _VOICE.get(character_key, _VOICE["aarohi"])
    # A filler word every few turns, deterministically — her voice, not noise.
    if turn_count and turn_count % 3 == 0:
        reply = f"{_pick(voice['filler'], seed)} {reply}"
    return _clip(reply, 300)


_INITIATIVE_BANK = {
    "open_loop_callback": {
        ("roman", "intimate"): ["ani {note} kasto bhayo?", "eh {note} ko k bhayo?"],
        ("devanagari", "intimate"): ["अनि {note} कस्तो भयो?"],
        ("en", None): ["hey, how did {note} go?"],
    },
    "festival_greeting": {
        ("roman", "intimate"): ["{note} ko subhakamana! ghar ma nai xau?"],
        ("devanagari", "intimate"): ["{note} को शुभकामना! घरमै छौ?"],
        ("en", None): ["happy {note}! are you home?"],
    },
    "milestone_reaction": {
        ("roman", "intimate"): ["hehe {note}, thaha xa?"],
        ("devanagari", "intimate"): ["{note}, थाहा छ?"],
        ("en", None): ["{note} — did you notice?"],
    },
    "light_checkin": {
        ("roman", "intimate"): ["aaja {self} thiyo. timro din kasto gayo?"],
        ("devanagari", "intimate"): ["आज {self} थियो। तिम्रो दिन कस्तो गयो?"],
        ("en", None): ["today was {self}. how was yours?"],
    },
    "absence_checkin": {
        ("roman", "intimate"): ["k cha? kehi din dekhina, sab thik xa?"],
        ("devanagari", "intimate"): ["के छ? केही दिन देखिन, सब ठीक छ?"],
        ("en", None): ["hey, haven't heard from you in a bit — all good?"],
    },
    "mood_checkin": {
        ("roman", "intimate"): ["aaja ali better xa? socheko thiye timro barema"],
        ("devanagari", "intimate"): ["आज अलि ठीक छ? तिम्रो बारेमा सोचेको थिएँ"],
        ("en", None): ["feeling any better today? was thinking about you"],
    },
    "good_morning": {
        ("roman", "intimate"): ["good morning ☀️ aaja {self} xa mero"],
        ("devanagari", "intimate"): ["शुभ प्रभात ☀️ आज मेरो {self} छ"],
        ("en", None): ["morning ☀️ got {self} today"],
    },
    "good_night": {
        ("roman", "intimate"): ["suteko? good night 🙂"],
        ("devanagari", "intimate"): ["सुत्यौ? शुभ रात्री 🙂"],
        ("en", None): ["heading to sleep. night 🙂"],
    },
}


def companion_initiative(*, character_key: str, trigger: str,
                         context_note: str | None, day: dict | None,
                         style: dict | None) -> str | None:
    """Offline twin of the initiative engine's generator."""
    bank = _INITIATIVE_BANK.get(trigger)
    if not bank:
        return None
    bucket = _bucket(style)
    pool = bank.get(bucket) or bank.get(("en", None)) or []
    if not pool:
        return None
    seed = _seed(character_key, trigger, context_note or "", (day or {}).get("weekday", ""))
    template = _pick(pool, seed)
    note = (context_note or "").split(";")[0][:80]
    return _fill(template.replace("{note}", note), character_key, day)


def saathi_respond(session_id: str, character_key: str, user_message: str,
                   turn_count: int = 0) -> str:
    """Back-compat shim for callers that still expect the old signature."""
    return companion_reply(session_id=session_id, character_key=character_key,
                           user_message=user_message, style=None, day=None,
                           turn_count=turn_count)



def summarize_session_memory(transcript_lines: list[tuple[str, str]],
                             crisis_flagged: bool) -> list[dict]:
    """Extractive summarisation — no LLM required.

    Guardrail (doc 5 §2.4): sessions where crisis indicators appeared produce
    NO memory items beyond the immediate safety response.
    """
    if crisis_flagged:
        return []
    user_lines = [t for role, t in transcript_lines if role == "user" and t.strip()]
    items: list[dict] = []
    if user_lines:
        items.append({
            "summary_text": _clip(f"Practising conversation — opened with: “{user_lines[0][:90]}”", 280),
            "category": "practice",
        })
    longest = max(user_lines, key=len) if user_lines else ""
    if longest and longest != user_lines[0]:
        items.append({
            "summary_text": _clip(f"Shared context for future sessions: “{longest[:110]}”", 280),
            "category": "context",
        })
    blob = " ".join(user_lines).lower()
    for word, label in (("nervous", "Pre-date nerves came up"),
                        ("date", "Has a date to debrief"),
                        ("opener", "Working on first-message openers")):
        if word in blob:
            items.append({"summary_text": label + ".", "category": "goal"})
            break
    return items[:3]


def generate_proactive_message(message_type: str, context_note=None) -> str | None:
    bank = {
        "practice_nudge": "One quick opener drill today? Two minutes, and your next match gets the good version of you.",
        "post_date_debrief": "How did it go last night? Honest version — no highlight reel needed.",
        "encouragement": "You sent the first message this week. That was the hard part.",
    }
    return bank.get(message_type)


def transcribe_audio(audio_bytes: bytes) -> str:
    """Mock STT: fixed transcript so the voice pipeline stays exercisable."""
    return "I never know how to start a chat with someone new."


def synthesize_speech(text: str) -> bytes:
    """Mock TTS: renders a valid, playable mono 16-bit PCM WAV (soft tone whose
    envelope tracks sentence count) — real audio bytes for client playback."""
    sample_rate = 16000
    duration_s = min(1.0 + 0.35 * max(1, text.count(".") + text.count("?")), 6.0)
    n = int(sample_rate * duration_s)
    freq = 196 + (_seed(text) % 5) * 22  # G3..A4-ish, varies per reply
    samples = bytearray()
    for i in range(n):
        t = i / sample_rate
        fade = min(1.0, t / 0.05, (duration_s - t) / 0.05)
        value = int(9000 * fade * math.sin(2 * math.pi * freq * t)
                    * (0.6 + 0.4 * math.sin(2 * math.pi * 3 * t)))
        samples += struct.pack("<h", value)
    header = b"RIFF" + struct.pack("<I", 36 + len(samples)) + b"WAVE"
    fmt = (b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, sample_rate,
                                 sample_rate * 2, 2, 16))
    return header + fmt + b"data" + struct.pack("<I", len(samples)) + bytes(samples)


def weekly_recap(stats: dict) -> str:
    matches = stats.get("new_matches_this_week", 0)
    sent = stats.get("messages_sent", 0)
    received = stats.get("messages_received", 0)
    if matches == 0 and sent == 0:
        return ("A quiet week — totally normal rhythm. One small move for next "
                "week: refresh your prompt answers and say namaste to someone new.")
    opening = f"{matches} new match{'es' if matches != 1 else ''}" if matches else "No new matches"
    middle = f", and you exchanged {sent + received} messages." if sent + received else "."
    tip = ("Keep the momentum — reply within a day while context is fresh."
           if received > sent else
           "You led the conversations this week; try asking one open question per chat.")
    return f"{opening}{middle} {tip}"
