import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base


class SaathiCharacter(AuditMixin, Base):
    __tablename__ = "saathi_characters"

    key: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    persona_description: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt_template_id: Mapped[str] = mapped_column(String(64), nullable=False)
    illustrated_avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    default_theme_preset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("chat_theme_presets.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Companion expansion (master plan §7.1): romantic-mode roster with tier
    # locks, texting-style realism, per-character TTS voice and presence.
    companion_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    min_tier: Mapped[str] = mapped_column(String(16), default="free", nullable=False)
    relationship_style: Mapped[str | None] = mapped_column(String(32), nullable=True)
    texting_style: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    voice_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    avatar_urls: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    backstory_template: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Persona bible (doc 8 §C2): the character's WHOLE life as data — family,
    # history, loves/hates, insecurities, quirks, boundaries, weekly rhythm.
    # This is what makes her a person instead of a one-line description; the
    # prompt builder renders it and the day generator reads `week` from it.
    persona_bible: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    birthday: Mapped[str | None] = mapped_column(String(5), nullable=True)  # MM-DD
    hometown: Mapped[str | None] = mapped_column(String(120), nullable=True)

    sessions = relationship("SaathiSession", back_populates="character")
    presence_schedule = relationship(
        "SaathiPresenceSchedule", back_populates="character", uselist=False
    )


class SaathiPresenceSchedule(AuditMixin, Base):
    """Simulated weekly life per character (master plan §4.1).

    schedule JSON shape:
      {"sleep_window": [23, 7], "weekday_windows": [{"start": 10, "end": 16,
       "activity": "college", "state": "busy"}], "weekend_windows": [...],
       "spontaneity": 0.3}
    All hours are Asia/Kathmandu local time. Never fabricates states implying
    the companion is with someone else (banned jealousy pattern)."""
    __tablename__ = "saathi_presence_schedules"

    character_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("saathi_characters.id"), unique=True, nullable=False
    )
    schedule: Mapped[dict] = mapped_column(JSON, nullable=False)

    character = relationship("SaathiCharacter", back_populates="presence_schedule")


class SaathiSession(AuditMixin, Base):
    __tablename__ = "saathi_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    character_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("saathi_characters.id"), nullable=False)
    # Companions live in the normal inbox (§14): the session is bound 1:1 to a
    # real Match row so chat, realtime, themes and read receipts need no forks.
    match_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("matches.id"), index=True, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_proactive_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    proactive_messages_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    proactive_cap_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    proactive_opt_in: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    turn_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    crisis_flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Companion-mode relationship state (intimacy progression, master plan §4.6).
    # doc 8: the 'practice' mode is gone — every character is a real partner, so
    # this is 'dating' for every session and no code branches on it any more. The
    # column stays for historical rows and for a future mode (e.g. 'paused').
    companion_mode: Mapped[str] = mapped_column(String(16), default="dating", nullable=False)
    intimacy_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bond_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_mood: Mapped[str] = mapped_column(String(24), default="cheerful", nullable=False)
    # §13.4 realtime user-mood read (lexical belt per message, refined by the
    # evolution job) — proactive engine reads this to time/tune its tone
    user_mood: Mapped[str | None] = mapped_column(String(24), nullable=True)
    user_mood_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_streak_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status_posts_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status_cap_date: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # ── Language mirroring (doc 8 §C4) ──────────────────────────────────────
    # EWMA of how THIS user actually writes: {"script", "language", "register",
    # "romanization", "avg_len", "emoji_rate", "msgs_per_turn", "slang": [],
    # "samples"}. One odd message can't flip her voice; a real switch converges
    # in ~3 turns. Rendered into the prompt and post-enforced on the draft.
    user_style: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ── Context compaction (doc 8 §C2) ─────────────────────────────────────
    # Everything older than `summary_upto_message_at` lives here instead of in
    # the raw window, so a 2,000-message relationship costs the same per turn
    # as a 20-message one and nothing is silently forgotten.
    rolling_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_upto_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    # ── Initiative engine (doc 8 §C5) ──────────────────────────────────────
    # She asked something and is waiting: penalises further auto-texts so she
    # never double-, triple-texts into silence.
    awaiting_user_reply: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # A busy/asleep reply she chose to defer; the ETA task delivers it later.
    deferred_reply_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    deferred_reply_body: Mapped[str | None] = mapped_column(Text, nullable=True)

    character: Mapped[SaathiCharacter] = relationship(back_populates="sessions")
    messages = relationship("SaathiMessage", back_populates="session", lazy="dynamic")
    memory_items = relationship("SaathiMemoryItem", back_populates="session")
    status_posts = relationship("SaathiStatusPost", back_populates="session")
    open_loops = relationship("SaathiOpenLoop", back_populates="session")
    persona_profile = relationship(
        "SaathiPersonaProfile", back_populates="session", uselist=False
    )
    lorebook = relationship("SaathiLorebookEntry", back_populates="session")
    diary_entries = relationship("SaathiDiaryEntry", back_populates="session")
    mirror_questions = relationship("SaathiMirrorQuestion", back_populates="session")
    quests = relationship("SaathiQuest", back_populates="session")
    capsules = relationship("SaathiMomentCapsule", back_populates="session")
    recap_cards = relationship("SaathiRecapCard", back_populates="session")
    media_items = relationship("SaathiMediaItem", back_populates="session")


class SaathiMessage(AuditMixin, Base):
    __tablename__ = "saathi_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("saathi_sessions.id"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # chat | proactive | status_reply — proactive messages land IN the chat
    # (master plan §4.4) so the companion actually texts first.
    message_type: Mapped[str] = mapped_column(String(24), default="chat", nullable=False)
    # Retry metadata for swipe-to-regenerate: {"variant": n, "superseded": bool}
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    session: Mapped[SaathiSession] = relationship(back_populates="messages")


class SaathiMemoryItem(AuditMixin, Base):
    __tablename__ = "saathi_memory_items"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("saathi_sessions.id"), index=True, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Memory shaping (master plan §12.2 #28): pin promotes into the always-on
    # core block; edits are re-sanitized before save (memory is attack surface).
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    importance: Mapped[float] = mapped_column(default=0.5, nullable=False)
    # Retrieval recency (doc 8 §C2): recency of RECALL, not of creation — a fact
    # she brought up yesterday outranks one stored months ago and never used.
    last_recalled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    session: Mapped[SaathiSession] = relationship(back_populates="memory_items")


class SaathiStatusPost(AuditMixin, Base):
    """Ambient 'her day' status/story posts (master plan §4.5). 24h expiry,
    reactable, zero-pressure presence the user can lurk without replying."""
    __tablename__ = "saathi_status_posts"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("saathi_sessions.id"), index=True, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(24), default="ambient", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reaction: Mapped[str | None] = mapped_column(String(8), nullable=True)
    reacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[SaathiSession] = relationship(back_populates="status_posts")


class SaathiOpenLoop(AuditMixin, Base):
    """'Things she's waiting on' — extracted unfinished threads (master plan
    §12.2 #30). The proactive engine fires from open loops first: follow-ups
    grounded in real shared history beat generic daily nudges."""
    __tablename__ = "saathi_open_loops"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("saathi_sessions.id"), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    followup_after_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="open", nullable=False)
    last_callback_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[SaathiSession] = relationship(back_populates="open_loops")


class SaathiPersonaProfile(AuditMixin, Base):
    """Learned per-user persona (dynamic-persona engine, §13).

    NOTHING about how the companion behaves toward a specific user is
    hardcoded: either the user trains it (chat history in any format via
    /persona/train) or it evolves continuously from their chats. `traits`
    JSON schema: {"nickname_for_user", "vibe", "texting_style", "emoji_habits",
    "language_mix", "inside_jokes": [], "favorite_topics": [],
    "attachment_style", "pace", "origins": "default|imported|evolved",
    "source_label"}. `persona_prompt` is the LLM-rewritten always-on block."""
    __tablename__ = "saathi_persona_profiles"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("saathi_sessions.id"), unique=True, index=True, nullable=False
    )
    traits: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    persona_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    # mines the user's OTHER Milan chats (only style traits, never message
    # text) so the companion mirrors how the user actually texts
    style_mining_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    style_digest: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evolution_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    evolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[SaathiSession] = relationship(back_populates="persona_profile")


class SaathiLorebookEntry(AuditMixin, Base):
    """User-trainable facts ("train it into"): key -> value injected into the
    companion prompt whenever the key shows up in recent context."""
    __tablename__ = "saathi_lorebook_entries"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("saathi_sessions.id"), index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(16), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    session: Mapped[SaathiSession] = relationship(back_populates="lorebook")


class SaathiDiaryEntry(AuditMixin, Base):
    """Companion diary (master plan #29): end-of-day reflective entries,
    optionally illustrated (AI-labeled, never photorealistic-human)."""
    __tablename__ = "saathi_diary_entries"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("saathi_sessions.id"), index=True, nullable=False)
    day_key: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD KTM
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    mood: Mapped[str | None] = mapped_column(String(24), nullable=True)
    illustrated_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    reaction: Mapped[str | None] = mapped_column(String(8), nullable=True)

    session: Mapped[SaathiSession] = relationship(back_populates="diary_entries")


class SaathiMirrorQuestion(AuditMixin, Base):
    """Mirror Questions (master plan #39): the companion asks the user one
    reflective question; answers feed back into the persona profile."""
    __tablename__ = "saathi_mirror_questions"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("saathi_sessions.id"), index=True, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    reflection: Mapped[str | None] = mapped_column(Text, nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[SaathiSession] = relationship(back_populates="mirror_questions")


class SaathiQuest(AuditMixin, Base):
    """Duo quests / streak rituals (Phase 4): bond-building activities with
    freeze rules — never a punishment path (no streak-loss grief)."""
    __tablename__ = "saathi_quests"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("saathi_sessions.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(24), default="duo", nullable=False)  # duo|streak|festival
    target: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reward_points: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    freeze_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[SaathiSession] = relationship(back_populates="quests")


class SaathiMomentCapsule(AuditMixin, Base):
    """Moment Capsules (Phase 4): a note/message the companion (or user)
    seals now, unlockable at a future moment."""
    __tablename__ = "saathi_moment_capsules"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("saathi_sessions.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(16), default="companion", nullable=False)
    unlock_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[SaathiSession] = relationship(back_populates="capsules")


class SaathiRecapCard(AuditMixin, Base):
    """Milan Recap share cards (Phase 4): deterministic stats from real data
    + one grounded narrative line. Share token renders a public card."""
    __tablename__ = "saathi_recap_cards"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("saathi_sessions.id"), index=True, nullable=False)
    period: Mapped[str] = mapped_column(String(24), nullable=False)  # week|month|all_time
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    share_token: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    watermark: Mapped[str] = mapped_column(String(64), default="AI companion · Milan", nullable=False)

    session: Mapped[SaathiSession] = relationship(back_populates="recap_cards")


class SaathiMediaItem(AuditMixin, Base):
    """AI-illustrated media (Phase 3 selfie packs, diary art): always
    AI-labeled, illustrated style, never photorealistic-human deception."""
    __tablename__ = "saathi_media_items"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("saathi_sessions.id"), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(24), default="selfie", nullable=False)  # selfie|diary_art
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    ai_label: Mapped[str] = mapped_column(String(64), default="AI-illustrated", nullable=False)
    pack_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    session: Mapped[SaathiSession] = relationship(back_populates="media_items")


class SaathiHeartLedger(AuditMixin, Base):
    """Affection hearts economy (master plan #25, ethical: earned by bond
    activities and real-connection wins, never purchasable with money)."""
    __tablename__ = "saathi_heart_ledger"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
