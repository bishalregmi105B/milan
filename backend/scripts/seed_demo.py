"""Seed demo users with realistic Nepali profiles and downloaded photos.

Run on the VPS:
    cd /var/www/milan/backend && set -a && . ./.env && set +a && \
    MILAN_ENV=prod ./venv/bin/python scripts/seed_demo.py
"""
import io
import sys
import time
import urllib.request
import uuid as uuid_module
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, "/var/www/milan/backend")

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import User, Profile, Photo  # noqa: E402

# url, gender-neutral name pool handled below
PHOTO_URLS_F = [
    "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=600&q=80",
    "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=600&q=80",
    "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=600&q=80",
    "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=600&q=80",
    "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=600&q=80",
    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=600&q=80",
]
PHOTO_URLS_M = [
    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600&q=80",
    "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=600&q=80",
    "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=600&q=80",
    "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=600&q=80",
    "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=600&q=80",
    "https://images.unsplash.com/photo-1500649297466-74794c70acfc?w=600&q=80",
]

DEMO_USERS = [
    # (name, gender, email, city, lat, lng, profession, bio, interests, photo_idx)
    ("Aarati Sharma", "female", "aarati.demo@milanapp.live", "Kathmandu", 27.7172, 85.3240,
     "UX Designer", "Momos over small talk any day. Chasing sunsets from Chandragiri and sketching corners of Patan on weekends.",
     ["photography", "hiking", "art", "momo hunting"], 0),
    ("Bibek Thapa", "male", "bibek.demo@milanapp.live", "Lalitpur", 27.6588, 85.3247,
     "Software Engineer", "Building apps by day, chasing waterfalls by weekend. Looking for someone to share sekuwa with.",
     ["coding", "trekking", "music", "cooking"], 0),
    ("Sneha Karki", "female", "sneha.demo@milanapp.live", "Pokhara", 28.2096, 83.9856,
     "Travel Blogger", "Fewa Lake mornings, mountain trails whenever possible. Tell me your favorite hidden gem.",
     ["travel", "yoga", "street food", "poetry"], 1),
    ("Dipesh Gurung", "male", "dipesh.demo@milanapp.live", "Pokhara", 28.2282, 83.9847,
     "Photographer", "Annapurna views and paragliding skies. I document stories, would love to document ours.",
     ["photography", "paragliding", "films", "biking"], 1),
    ("Prisha Maharjan", "female", "prisha.demo@milanapp.live", "Bhaktapur", 27.6710, 85.4298,
     "Architect", "Newa culture enthusiast. I know every hidden courtyard in Bhaktapur — let me show you.",
     ["architecture", "history", "coffee", "cycling"], 2),
    ("Rohan Shrestha", "male", "rohan.demo@milanapp.live", "Kathmandu", 27.7215, 85.3620,
     "Chef", "I cook, you judge. Newari cuisine specialist with a soft spot for late-night conversations.",
     ["cooking", "cricket", "jazz", "travelling"], 2),
    ("Anisha Rai", "female", "anisha.demo@milanapp.live", "Dharan", 26.8125, 87.2837,
     "Doctor", "Healing by profession, dancing by passion. Eastern hills girl looking for genuine connection.",
     ["dancing", "reading", "badminton", "tea"], 3),
    ("Suman Bhattarai", "male", "suman.demo@milanapp.live", "Chitwan", 27.5291, 84.3542,
     "Wildlife Guide", "Sauraha sunsets and jungle walks. If you love nature as much as I do, we will get along.",
     ["wildlife", "canoeing", "camping", "guitar"], 3),
    ("Kripa Adhikari", "female", "kripa.demo@milanapp.live", "Kathmandu", 27.7000, 85.3000,
     "Content Creator", "Making reels about Nepal's untold stories. Swipe right if you have one to share.",
     ["content creation", "fashion", "hiking", "vlogging"], 4),
    ("Nabin Joshi", "male", "nabin.demo@milanapp.live", "Biratnagar", 26.4525, 87.2718,
     "Entrepreneur", "Building my startup from the east. Ambitious but grounded. Tea person, not coffee.",
     ["startups", "chess", "reading", "cricket"], 4),
    ("Maya Tamang", "female", "maya.demo@milanapp.live", "Kathmandu", 27.7100, 85.3500,
     "Music Teacher", "Guitar chords and mountain roads. Looking for a duet partner in life.",
     ["music", "trekking", "baking", "dogs"], 5),
    ("Aashish Karki", "male", "aashish.demo@milanapp.live", "Butwal", 27.7000, 83.4486,
     "Civil Engineer", "Bridging gaps in construction and in conversation. Weekend cyclist, momo critic.",
     ["cycling", "photography", "movies", "badminton"], 5),
]

# Small deterministic prompts per user for the profile prompts table if empty.
CITIES = ["Kathmandu", "Lalitpur", "Pokhara", "Bhaktapur", "Dharan", "Chitwan", "Biratnagar", "Butwal"]


def fetch_photo(url: str) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (MilanSeeder)"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except Exception as exc:  # noqa: BLE001
        print(f"    ! photo fetch failed: {exc}")
        return None


def store_photo_locally(user_id, url: str) -> str | None:
    data = fetch_photo(url)
    if not data:
        return None
    import pathlib

    ext = "jpg"
    root = pathlib.Path("/var/www/milan/backend/instance/uploads")
    key = f"photo/{user_id}/{uuid_module.uuid4().hex}.{ext}"
    target = root / key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return f"/media/{key}"


def main() -> None:
    app = create_app("prod")
    with app.app_context():
        created = 0
        for (name, gender, email, city, lat, lng, profession, bio, interests, p_idx) in DEMO_USERS:
            if User.query.filter_by(email=email).first():
                print(f"  = {email} exists, skipping")
                continue
            user = User(
                email=email,
                auth_provider="email",
                is_verified=True,
                date_of_birth=date(1996, (hash(name) % 12) + 1, (hash(name) % 27) + 1),
                gender=gender,
                intent_mode="serious",
                account_status="active",
                role="user",
            )
            db.session.add(user)
            db.session.flush()

            profile = Profile(
                user_id=user.id,
                display_name=name,
                bio=bio,
                interests=interests,
                latitude=lat,
                longitude=lng,
                city=city,
                profession=profession,
                conversation_style="playful" if gender == "male" else "thoughtful",
                lifestyle_tags=["urban", "active"],
                values_tags=["family", "honesty"],
                relationship_intent="serious relationship",
                interview_completed_at=datetime.now(timezone.utc) - timedelta(days=3),
            )
            db.session.add(profile)

            url_pool = PHOTO_URLS_F if gender == "female" else PHOTO_URLS_M
            photo_url = store_photo_locally(user.id, url_pool[p_idx])
            if photo_url:
                db.session.add(Photo(user_id=user.id, url=photo_url, order_index=0,
                                     moderation_status="approved"))
                db.session.add(Photo(user_id=user.id, url=url_pool[(p_idx + 1) % len(url_pool)], order_index=1,
                                     moderation_status="approved"))
            created += 1
            print(f"  + created {name} ({email}) {city}")
            time.sleep(0.4)  # be gentle with unsplash

        # Second photo as remote URL fallback if local fetch failed.
        db.session.commit()

        total = User.query.count()
        print(f"\nDONE. users_created={created} total_users={total}")


if __name__ == "__main__":
    main()
