"""Canonical interest taxonomy (doc 8 §C9, §A5 — imported pattern from dobato,
seeded with a Nepali taxonomy). `Profile.interests` stores catalog KEYS so
ranking's jaccard term compares like with like; the table owns the human
label, Nepali label, icon and grouping for the picker.

`ensure_seeded()` is idempotent and lazily invoked by the catalog endpoint —
the same pattern `ensure_characters_seeded()` uses for companions."""

CATALOG: list[dict] = [
    # food & drink
    {"key": "momo", "label": "Momo", "label_ne": "मम", "icon": "🥟", "category": "food"},
    {"key": "chiya", "label": "Chiya", "label_ne": "चिया", "icon": "☕", "category": "food"},
    {"key": "cooking", "label": "Cooking", "label_ne": "पकाउने", "icon": "🍳", "category": "food"},
    {"key": "street_food", "label": "Street food", "label_ne": "स्ट्रिट फुड", "icon": "🍢", "category": "food"},
    {"key": "newari_food", "label": "Newari food", "label_ne": "नेवारी खाना", "icon": "🍚", "category": "food"},
    {"key": "coffee", "label": "Coffee", "label_ne": "कफी", "icon": "☕", "category": "food"},
    # outdoors & sport
    {"key": "hiking", "label": "Hiking", "label_ne": "हाइकिङ", "icon": "🥾", "category": "outdoors"},
    {"key": "trekking", "label": "Trekking", "label_ne": "ट्रेकिङ", "icon": "⛰️", "category": "outdoors"},
    {"key": "camping", "label": "Camping", "label_ne": "क्याम्पिङ", "icon": "🏕️", "category": "outdoors"},
    {"key": "cycling", "label": "Cycling", "label_ne": "साइकल", "icon": "🚴", "category": "outdoors"},
    {"key": "football", "label": "Football", "label_ne": "फुटबल", "icon": "⚽", "category": "sports"},
    {"key": "cricket", "label": "Cricket", "label_ne": "क्रिकेट", "icon": "🏏", "category": "sports"},
    {"key": "badminton", "label": "Badminton", "label_ne": "ब्याडमिन्टन", "icon": "🏸", "category": "sports"},
    {"key": "basketball", "label": "Basketball", "label_ne": "बास्केटबल", "icon": "🏀", "category": "sports"},
    {"key": "gym", "label": "Gym", "label_ne": "जिम", "icon": "🏋️", "category": "sports"},
    {"key": "yoga", "label": "Yoga", "label_ne": "योग", "icon": "🧘", "category": "sports"},
    {"key": "running", "label": "Running", "label_ne": "दौड", "icon": "🏃", "category": "sports"},
    # arts & culture
    {"key": "music", "label": "Music", "label_ne": "सङ्गीत", "icon": "🎵", "category": "arts"},
    {"key": "guitar", "label": "Guitar", "label_ne": "गितार", "icon": "🎸", "category": "arts"},
    {"key": "singing", "label": "Singing", "label_ne": "गाउने", "icon": "🎤", "category": "arts"},
    {"key": "dancing", "label": "Dancing", "label_ne": "नाच्ने", "icon": "💃", "category": "arts"},
    {"key": "photography", "label": "Photography", "label_ne": "फोटोग्राफी", "icon": "📷", "category": "arts"},
    {"key": "art", "label": "Art", "label_ne": "कला", "icon": "🎨", "category": "arts"},
    {"key": "reading", "label": "Reading", "label_ne": "पढ्ने", "icon": "📚", "category": "arts"},
    {"key": "writing", "label": "Writing", "label_ne": "लेख्ने", "icon": "✍️", "category": "arts"},
    {"key": "poetry", "label": "Poetry", "label_ne": "कविता", "icon": "📝", "category": "arts"},
    {"key": "movies", "label": "Movies", "label_ne": "चलचित्र", "icon": "🎬", "category": "arts"},
    {"key": "anime", "label": "Anime", "label_ne": "एनिमे", "icon": "🎌", "category": "arts"},
    {"key": "gaming", "label": "Gaming", "label_ne": "गेमिङ", "icon": "🎮", "category": "arts"},
    {"key": "festivals", "label": "Festivals", "label_ne": "चाडपर्व", "icon": "🏮", "category": "culture"},
    {"key": "heritage", "label": "Heritage walks", "label_ne": "सम्पदा", "icon": "🛕", "category": "culture"},
    {"key": "volunteering", "label": "Volunteering", "label_ne": "सेवा", "icon": "🤝", "category": "culture"},
    {"key": "pets", "label": "Pets", "label_ne": "पाल्तु जनावर", "icon": "🐕", "category": "culture"},
    # lifestyle & tech
    {"key": "travel", "label": "Travel", "label_ne": "यात्रा", "icon": "✈️", "category": "lifestyle"},
    {"key": "road_trips", "label": "Road trips", "label_ne": "रोड ट्रिप", "icon": "🛣️", "category": "lifestyle"},
    {"key": "motorcycling", "label": "Motorcycling", "label_ne": "मोटरसाइकल", "icon": "🏍️", "category": "lifestyle"},
    {"key": "fashion", "label": "Fashion", "label_ne": "फेसन", "icon": "👕", "category": "lifestyle"},
    {"key": "startups", "label": "Startups", "label_ne": "स्टार्टअप", "icon": "🚀", "category": "tech"},
    {"key": "technology", "label": "Technology", "label_ne": "प्रविधि", "icon": "💻", "category": "tech"},
    {"key": "ai", "label": "AI", "label_ne": "एआई", "icon": "🤖", "category": "tech"},
]

CATEGORY_ORDER = ["food", "outdoors", "sports", "arts", "culture", "lifestyle", "tech"]

# legacy free-text values that map onto catalog keys (case/space tolerant)
_ALIASES = {
    "momos": "momo", "tea": "chiya", "chai": "chiya", "trek": "trekking",
    "hike": "hiking", "bike": "motorcycling", "biking": "motorcycling",
    "books": "reading", "book": "reading", "photo": "photography",
    "games": "gaming", "movie": "movies", "films": "movies",
    "travelling": "travel", "traveling": "travel", "tech": "technology",
    "gym_": "gym", "workout": "gym", "football_fan": "football",
}


def normalize_interests(values: list | None, *, max_count: int = 10) -> list[str]:
    """Map raw values to catalog keys where possible, dedupe, cap the count.
    Unknown values are kept verbatim (lowercased) so legacy profiles survive;
    matching stays tolerant in ranking via the jaccard term."""
    if not values:
        return []
    known = {entry["key"] for entry in CATALOG}
    by_label = {entry["label"].lower(): entry["key"] for entry in CATALOG}
    by_label_ne = {entry["label_ne"]: entry["key"] for entry in CATALOG if entry.get("label_ne")}

    out: list[str] = []
    for raw in values:
        value = str(raw).strip()
        if not value:
            continue
        lowered = value.lower().replace(" ", "_")
        key = lowered if lowered in known else None
        if key is None:
            key = _ALIASES.get(lowered) or _ALIASES.get(lowered.replace("_", " "))
        if key is None:
            key = by_label.get(value.lower())
        if key is None:
            key = by_label_ne.get(value)
        out.append(key or lowered)
        if len(out) >= max_count:
            break
    return list(dict.fromkeys(out))


def ensure_seeded() -> None:
    """Upsert the taxonomy. Cheap: ~40 rows, one query per cold call."""
    from app.extensions import db
    from app.models import Interest

    existing = {i.key: i for i in Interest.query.all()}
    changed = False
    for entry in CATALOG:
        row = existing.get(entry["key"])
        if row is None:
            db.session.add(Interest(
                key=entry["key"], label=entry["label"], label_ne=entry.get("label_ne"),
                icon=entry.get("icon"), category=entry.get("category", "other")))
            changed = True
        else:
            if row.label != entry["label"] or row.icon != entry.get("icon"):
                row.label = entry["label"]
                row.icon = entry.get("icon")
                changed = True
    if changed:
        db.session.commit()
