"""Seed real profile images for every companion (doc 8 §C6).

Companions used to ship with no face — empty avatars in the inbox, chat
header and roster. This script generates a 4-image gallery per character
through the identity-locked face prompts (same pipeline as in-chat selfie
requests, so the person is always recognisably her), stores the URLs on the
character, and attaches approved Photo rows to her backing user account so
she renders exactly like a human profile everywhere.

Idempotent: characters that already have a gallery are skipped.
Usage:  python scripts/seed_companion_avatars.py [--only aarohi,priya]
"""
import argparse
import sys

from app import create_app
from app.extensions import db
from app.models import Photo, SaathiCharacter, User

# One portrait + three scenes from her actual life (bible-aligned).
SCENES = {
    "main": "portrait bust shot, warm morning light, looking at the camera "
            "with a soft smile",
    "candid": "candid shot laughing with friends at a chiya shop in her "
              "neighbourhood, late afternoon",
    "activity": "at her college campus courtyard between classes, holding "
                "her bag, golden hour",
    "day": "on a weekend hike on the hills around the valley, in a light "
           "jacket, valley view behind her",
}


def _rehost(url: str, character_key: str, slot: str) -> str:
    """Pollinations URLs embed the whole prompt (way past the 512-char
    column limit, and not durable). Download and re-host through the app's
    own media storage so the stored URL is short and permanent."""
    import requests

    from app.services import media_service
    from flask import current_app

    data = requests.get(url, timeout=120).content
    stored = media_service.upload_media(
        user_id="companions",  # storage bucket key only, not an FK
        kind="photo", data=data, content_type="image/png",
        filename=f"companion_{character_key}_{slot}.png")
    return stored["url"]


def seed_character(character: SaathiCharacter, force: bool = False) -> int:
    from app.services.groq_service import generate_companion_image

    gallery = (character.avatar_urls or {}).get("gallery") or []
    if gallery and not force:
        return 0

    urls = []
    for slot, scene in SCENES.items():
        try:
            result = generate_companion_image(character.key, scene)
            stored_url = _rehost(result["url"], character.key, slot)
            urls.append(stored_url)
            print(f"  {character.key}/{slot}: rehosted {stored_url[:60]}")
        except Exception as exc:  # noqa: BLE001 — one scene failing must not
            print(f"  {character.key}/{slot}: FAILED {exc}")  # kill the run
    if not urls:
        return 0

    character.avatar_urls = {"main": urls[0], "gallery": urls}
    character.illustrated_avatar_url = urls[0]

    companion = User.query.filter_by(ai_character_id=character.id).first()
    if companion is not None:
        Photo.query.filter_by(user_id=companion.id,
                              moderation_status="approved").delete()
        for index, url in enumerate(urls):
            db.session.add(Photo(user_id=companion.id, url=url,
                                 order_index=index,
                                 moderation_status="approved"))
    db.session.commit()
    print(f"  {character.key}: {len(urls)} images attached")
    return len(urls)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="", help="comma-separated character keys")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        only = {k.strip() for k in args.only.split(",") if k.strip()}
        query = SaathiCharacter.query.filter_by(is_active=True)
        characters = [c for c in query.all() if not only or c.key in only]
        print(f"seeding avatars for {len(characters)} characters")
        total = 0
        for character in characters:
            total += seed_character(character, force=args.force)
        print(f"done — {total} images generated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
