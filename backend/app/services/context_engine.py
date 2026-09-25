"""Context engine (doc 8 §C2) — memory that survives a real relationship.

Before: a fixed 10-turn window plus EVERY memory item dumped into the prompt
([groq_service._session_context]). Two failures follow from that:
  - month 3 of a relationship costs 40x month 1 in tokens, then silently
    truncates at the model limit — she starts forgetting mid-sentence;
  - the 10-turn wall means anything said 11 turns ago is simply gone.

After: a token-budgeted assembly with six layers in priority order, plus
compaction. Layer 1 is never trimmed, layer 6 absorbs whatever budget is left.

  1 identity + voice          always (built by companion_prompt)
  2 core memory               pinned items — she must never lose these
  3 rolling summary           everything older than the raw window, compacted
  4 retrieved memory          top-N relevant to THIS message
  5 open loops                things she is waiting to hear about
  6 raw turns                 as many recent turns as fit

Compaction runs when unsummarised turns exceed COMPACT_EVERY_TURNS: a cheap 8B
call folds them into `rolling_summary` and advances the watermark. A
2,000-message relationship then costs the same per turn as a 20-message one and
nothing is silently dropped.
"""
import logging
import re

logger = logging.getLogger(__name__)

# Devanagari is far less token-efficient than Latin in BPE vocabularies, so a
# naive len/4 estimate under-counts Nepali by ~2x and silently blows the budget.
_CHARS_PER_TOKEN_LATIN = 3.9
_CHARS_PER_TOKEN_DEVANAGARI = 2.2
_DEVANAGARI = re.compile(r"[\u0900-\u097F]")

DEFAULT_BUDGET = 3000
COMPACT_EVERY_TURNS = 24
RAW_TURNS_MIN = 6
RAW_TURNS_MAX = 24
# Words too common to discriminate between memories.
_STOPWORDS = {
    "the", "and", "you", "your", "that", "this", "with", "have", "was", "for",
    "but", "not", "are", "his", "her", "she", "him", "they", "them", "about",
    "just", "like", "what", "when", "then", "there", "here", "from", "will",
    "cha", "chha", "xa", "ho", "hoina", "pani", "mero", "timro", "ta", "ni",
}


def estimate_tokens(text: str) -> int:
    """Script-aware token estimate. Deliberately cheap (no tokenizer download)
    and deliberately slightly pessimistic — over-estimating costs a few unused
    tokens, under-estimating costs a truncated reply."""
    if not text:
        return 0
    deva = len(_DEVANAGARI.findall(text))
    other = len(text) - deva
    return int(deva / _CHARS_PER_TOKEN_DEVANAGARI + other / _CHARS_PER_TOKEN_LATIN) + 1


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z\u0900-\u097F]{3,}", (text or "").lower())
    return {w for w in words if w not in _STOPWORDS}


def score_memory(item, query_tokens: set[str], now) -> float:
    """Relevance of one memory to the current message.

    0.5 keyword overlap + 0.3 stated importance + 0.2 recency-of-recall. Recall
    recency (not creation) is used deliberately: a fact she brought up yesterday
    is live in the relationship; one stored months ago and never used is not."""
    overlap = 0.0
    item_tokens = _tokens(getattr(item, "summary_text", ""))
    if query_tokens and item_tokens:
        overlap = len(query_tokens & item_tokens) / len(query_tokens)
    importance = float(getattr(item, "importance", 0.5) or 0.5)

    recency = 0.0
    stamp = getattr(item, "last_recalled_at", None) or getattr(item, "created_at", None)
    if stamp is not None and now is not None:
        try:
            if stamp.tzinfo is None:
                from datetime import timezone as _tz

                stamp = stamp.replace(tzinfo=_tz.utc)
            days = max(0.0, (now - stamp).total_seconds() / 86400.0)
            recency = 1.0 / (1.0 + days / 14.0)  # half-weight at two weeks
        except (TypeError, AttributeError):
            recency = 0.0
    return round(0.5 * overlap + 0.3 * importance + 0.2 * recency, 4)


def _config(key: str, default: int) -> int:
    try:
        from flask import current_app

        return int(current_app.config.get(key, default))
    except Exception:  # noqa: BLE001 — usable outside an app context (tests, tools)
        return default


def assemble(*, session, identity_block: str, user_message: str,
             memory_items: list, open_loops: list, raw_history: list[dict]) -> dict:
    """Build the final message list within budget.

    Returns {"system": str, "history": [...], "recalled_ids": [...],
             "tokens": int, "raw_turns_used": int}. `recalled_ids` lets the
    caller stamp `last_recalled_at` so the recency term stays meaningful."""
    budget = _config("COMPANION_CONTEXT_TOKEN_BUDGET", DEFAULT_BUDGET)
    raw_min = _config("COMPANION_RAW_TURNS_MIN", RAW_TURNS_MIN)
    raw_max = _config("COMPANION_RAW_TURNS_MAX", RAW_TURNS_MAX)

    blocks: list[str] = [identity_block]
    used = estimate_tokens(identity_block)

    # ── layer 2: core memory (pinned) — reserved, never trimmed ───────────
    pinned = [m for m in memory_items if getattr(m, "is_pinned", False)]
    if pinned:
        text = ("THINGS YOU MUST NEVER FORGET ABOUT THEM:\n"
                + "\n".join(f"- {m.summary_text}" for m in pinned[:12]) + "\n")
        blocks.append(text)
        used += estimate_tokens(text)

    # ── layer 3: rolling summary of everything before the raw window ──────
    summary = (getattr(session, "rolling_summary", None) or "").strip()
    if summary:
        text = ("YOUR HISTORY WITH THEM SO FAR (everything before the recent "
                "messages below):\n" + summary + "\n")
        blocks.append(text)
        used += estimate_tokens(text)

    # ── layer 4: retrieved memory, relevant to THIS message ───────────────
    recalled_ids: list = []
    unpinned = [m for m in memory_items if not getattr(m, "is_pinned", False)]
    if unpinned:
        from app.models.base import utcnow

        query_tokens = _tokens(user_message)
        ranked = sorted(unpinned,
                        key=lambda m: score_memory(m, query_tokens, utcnow()),
                        reverse=True)
        picked: list[str] = []
        # Cap retrieval at a third of the budget: raw conversation matters more
        # than recall, and a wall of remembered facts reads like a dossier.
        recall_ceiling = used + int(budget * 0.33)
        for item in ranked[:10]:
            line = f"- {item.summary_text}"
            cost = estimate_tokens(line)
            if used + cost > recall_ceiling:
                break
            picked.append(line)
            recalled_ids.append(getattr(item, "id", None))
            used += cost
        if picked:
            blocks.append("RELEVANT TO WHAT THEY JUST SAID:\n" + "\n".join(picked) + "\n")

    # ── layer 5: open loops she is waiting on ─────────────────────────────
    if open_loops:
        lines = [f"- {l.description}" for l in open_loops[:5]]
        text = ("STILL UNRESOLVED BETWEEN YOU (bring these up naturally, do not "
                "interrogate):\n" + "\n".join(lines) + "\n")
        cost = estimate_tokens(text)
        if used + cost <= budget:
            blocks.append(text)
            used += cost

    # ── layer 6: raw turns, newest-first until the budget runs out ────────
    system = "\n".join(b for b in blocks if b)
    system_tokens = estimate_tokens(system)
    remaining = max(0, budget - system_tokens)
    kept: list[dict] = []
    for turn in reversed(raw_history[-raw_max:]):
        cost = estimate_tokens(turn.get("content", "")) + 4  # role overhead
        if kept and cost > remaining and len(kept) >= raw_min:
            break
        remaining -= cost
        kept.append(turn)
    kept.reverse()

    return {
        "system": system,
        "history": kept,
        "recalled_ids": [i for i in recalled_ids if i is not None],
        "tokens": system_tokens + sum(estimate_tokens(t.get("content", "")) + 4 for t in kept),
        "raw_turns_used": len(kept),
    }


def mark_recalled(memory_ids: list) -> None:
    """Stamp `last_recalled_at` on the memories that made it into the prompt."""
    if not memory_ids:
        return
    from app.extensions import db
    from app.models import SaathiMemoryItem
    from app.models.base import utcnow

    try:
        (SaathiMemoryItem.query
         .filter(SaathiMemoryItem.id.in_(memory_ids))
         .update({"last_recalled_at": utcnow()}, synchronize_session=False))
        db.session.commit()
    except Exception:  # noqa: BLE001 — recall stamping must never break a reply
        db.session.rollback()
        logger.exception("mark_recalled failed")


def needs_compaction(session) -> bool:
    """True when enough has been said since the last summary to be worth folding
    in. Counted in MESSAGES since the watermark, not turns since session start,
    so a long-dormant chat doesn't trigger a pointless summary on resume."""
    from app.models import SaathiMessage

    every = _config("COMPANION_COMPACT_EVERY_TURNS", COMPACT_EVERY_TURNS)
    query = SaathiMessage.query.filter_by(session_id=session.id)
    watermark = getattr(session, "summary_upto_message_at", None)
    if watermark is not None:
        query = query.filter(SaathiMessage.created_at > watermark)
    return query.count() >= every * 2  # 2 messages per turn (user + her)


def compact(session) -> str | None:
    """Fold messages older than the raw window into `rolling_summary`.

    Runs on the cheap 8B model — this is bulk work, not voice work. Deliberately
    REWRITES the previous summary together with the new turns rather than
    appending, so the summary stays a coherent relationship narrative instead of
    growing into a changelog. Returns the new summary, or None if unchanged."""
    from app.extensions import db
    from app.models import SaathiMessage
    from app.services import groq_service

    raw_max = _config("COMPANION_RAW_TURNS_MAX", RAW_TURNS_MAX)
    query = SaathiMessage.query.filter_by(session_id=session.id)
    watermark = getattr(session, "summary_upto_message_at", None)
    if watermark is not None:
        query = query.filter(SaathiMessage.created_at > watermark)
    pending = query.order_by(SaathiMessage.created_at.asc()).all()
    # Leave the newest raw_max*2 messages alone — they still belong in layer 6.
    foldable = pending[:-(raw_max * 2)] if len(pending) > raw_max * 2 else []
    if not foldable:
        return None

    transcript = "\n".join(
        f"{'them' if m.role == 'user' else 'you'}: {m.content}" for m in foldable
    )[-12000:]
    previous = (getattr(session, "rolling_summary", None) or "").strip()

    if groq_service._mock_mode():
        # Deterministic offline twin: keep the narrative shape without a model.
        head = previous or "You two started talking."
        new_summary = (head + f" Since then you exchanged {len(foldable)} more messages.")[:4000]
    else:
        system = (
            "You maintain the running memory of ONE ongoing relationship for a "
            "chat companion. You get the previous summary and the newer messages. "
            "Rewrite ONE merged summary (max 250 words) covering: who they are and "
            "what is going on in their life, what you two have talked about, "
            "inside jokes and recurring themes, promises or plans either of you "
            "made, how close you have become, and anything sensitive to handle "
            "with care. Write it as second-person notes to yourself ('they told "
            "you...'). Keep concrete details — names, places, dates. Drop small "
            "talk. Never invent anything."
        )
        try:
            new_summary = groq_service._chat(
                groq_service.MODELS["prompt_grade"],
                [{"role": "system", "content": system},
                 {"role": "user", "content":
                  f"PREVIOUS SUMMARY:\n{previous or '(none yet)'}\n\nNEWER MESSAGES:\n{transcript}"}],
                temperature=0.3, max_tokens=520,
            ).strip()[:4000]
        except groq_service.GroqUnavailableError:
            logger.warning("compaction skipped (AI unavailable) session=%s", session.id)
            return None
    if not new_summary:
        return None

    session.rolling_summary = new_summary
    session.summary_upto_message_at = foldable[-1].created_at
    db.session.commit()
    return new_summary


