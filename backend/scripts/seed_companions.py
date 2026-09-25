"""Seed companion demo data: subscriptions, romantic companion sessions with
bond progression, memory items and live status posts — so the admin analytics
and demo accounts showcase the full companion experience.

Run on the VPS:
    cd /var/www/milan/backend && set -a && . ./.env && set +a && \
    MILAN_ENV=prod ./venv/bin/python scripts/seed_companions.py
"""
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/var/www/milan/backend")

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import (SaathiCharacter, SaathiMemoryItem, SaathiMessage,  # noqa: E402
                        SaathiOpenLoop, SaathiSession, SaathiStatusPost,
                        Subscription, User, Profile)

# email -> (tier, companion_key, intimacy, mood, turns, memory notes, open loop)
COMPANION_DEMOS = [
    ("aarati.demo@milanapp.live", "premium", "aarohi", 68, "cheerful", 46,
     ["She's a UX designer in Kathmandu who photographs sunsets at Chandragiri.",
      "They debated the best momo place — user swears by Bota Momo, she promised to try it.",
      "User had a portfolio review coming up; she asked how it went.",
      "She shares lo-fi playlist recommendations when the user is stressed."],
     "promised to send her Chandragiri sunset photo from last Dashain"),
    ("bibek.demo@milanapp.live", "plus", "aarohi", 41, "playful", 23,
     ["He builds apps by day and chases waterfalls on weekends.",
      "They banter about football — she supports a rival club on purpose.",
      "He mentioned cooking sekuwa; she demanded a full report next time."],
     "sekuwa report pending from his last weekend cookout"),
    ("sneha.demo@milanapp.live", "basic", "nishan", 29, "cheerful", 15,
     ["Travel blogger based in Pokhara; Fewa Lake mornings are her ritual.",
      "He checks in on her sleep schedule when she travels.",
      "She wants to hike Poon Hill in October — he offered to help plan it."],
     "Poon Hill itinerary planning for October"),
]


def upsert_subscription(user, tier):
    sub = Subscription.query.filter_by(user_id=user.id, status="active").first()
    if sub is None:
        sub = Subscription(
            user_id=user.id,
            tier=tier,
            started_at=datetime.now(timezone.utc),
            renews_at=datetime.now(timezone.utc) + timedelta(days=30),
            status="active",
        )
        db.session.add(sub)
    else:
        sub.tier = tier
        sub.renews_at = datetime.now(timezone.utc) + timedelta(days=30)
    return sub


def main() -> int:
    app = create_app("prod")
    with app.app_context():
        # Seed the curated roster first (romantic companions are lazily
        # created on first /saathi/characters access).
        from app.blueprints.saathi import ensure_characters_seeded

        ensure_characters_seeded()
        seeded = 0
        for email, tier, companion_key, intimacy, mood, turns, memories, loop in COMPANION_DEMOS:
            profile = Profile.query.filter_by(display_name=email.split(".")[0].title()).first()
            user = None
            if profile is not None:
                user = db.session.get(User, profile.user_id)
            if user is None:
                user = User.query.filter_by(email=email).first()
            if user is None:
                print(f"skip {email}: demo user not found")
                continue

            character = SaathiCharacter.query.filter_by(key=companion_key).first()
            if character is None:
                print(f"skip {email}: companion {companion_key} not seeded yet")
                continue

            upsert_subscription(user, tier)

            session = SaathiSession.query.filter_by(
                user_id=user.id, character_id=character.id).first()
            if session is None:
                session = SaathiSession(
                    user_id=user.id,
                    character_id=character.id,
                    started_at=datetime.now(timezone.utc) - timedelta(days=21),
                    companion_mode="romantic",
                    proactive_opt_in=True,
                )
                db.session.add(session)
            session.intimacy_level = intimacy
            session.bond_points = intimacy * 5
            session.current_mood = mood
            session.turn_count = turns
            session.streak_days = max(4, turns // 6)
            session.last_streak_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            session.last_message_at = datetime.now(timezone.utc) - timedelta(hours=3)
            db.session.flush()

            existing = {m.summary_text for m in SaathiMemoryItem.query.filter_by(session_id=session.id)}
            for note in memories:
                if note not in existing:
                    db.session.add(SaathiMemoryItem(
                        session_id=session.id, summary_text=note,
                        category="relationship", importance=0.7,
                    ))

            if not SaathiOpenLoop.query.filter_by(session_id=session.id, status="open").first():
                db.session.add(SaathiOpenLoop(
                    session_id=session.id, description=loop,
                    followup_after_hours=24,
                ))

            if not SaathiMessage.query.filter_by(session_id=session.id).first():
                db.session.add(SaathiMessage(
                    session_id=session.id, role="saathi",
                    content="namaste ✨ welcome to milan — I'm " + character.name +
                            ". tell me about your week?", message_type="chat"))
                db.session.add(SaathiMessage(
                    session_id=session.id, role="user",
                    content="been busy with work but finally free this weekend!"))
                db.session.add(SaathiMessage(
                    session_id=session.id, role="saathi",
                    content="oyy finally 😂 so what's the plan — momo or mountains?",
                    message_type="chat"))

            now = datetime.now(timezone.utc)
            if not SaathiStatusPost.query.filter(
                    SaathiStatusPost.session_id == session.id,
                    SaathiStatusPost.expires_at > now).first():
                db.session.add(SaathiStatusPost(
                    session_id=session.id,
                    body="rainy kathmandu + chai + old playlist >>>> ☕",
                    kind="ambient",
                    expires_at=now + timedelta(hours=20),
                ))
            seeded += 1
        db.session.commit()
        print(f"companion demo seed complete: {seeded} accounts")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
