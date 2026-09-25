import re

PHONE_RE = re.compile(r"^(\+?977)?9[678]\d{8}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

ALLOWED_GENDERS = {"male", "female", "nonbinary", "other"}
ALLOWED_INTENT_MODES = {"serious", "casual"}
ALLOWED_SWIPE_DIRECTIONS = {"like", "pass", "superlike"}
ALLOWED_SNAP_VIEW_MODES = {"single_view", "24h"}
ALLOWED_WALLPAPER_TYPES = {"preset", "solid", "gradient", "custom_upload", "ai_generated"}
ALLOWED_BUBBLE_SHAPES = {"rounded", "compact"}
ALLOWED_SCOPES = {"global", "match", "saathi_session"}
ALLOWED_PAYMENT_PROVIDERS = {"esewa", "khalti", "fonepay", "connectips"}
ALLOWED_REPORT_TARGET_TYPES = {"user", "message", "reel"}
ALLOWED_NOTIFICATION_CATEGORIES = {"matches", "messages", "saathi", "social", "promo"}

HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def validate_phone(phone: str) -> bool:
    return bool(PHONE_RE.match((phone or "").replace(" ", "")))


def validate_email(email: str) -> bool:
    return bool(EMAIL_RE.match((email or "").strip()))


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def normalize_phone(phone: str) -> str:
    cleaned = (phone or "").replace(" ", "")
    if cleaned.startswith("+"):
        return cleaned
    return f"+977{cleaned}"


def validate_age_18(dob) -> bool:
    if dob is None:
        return False
    from datetime import date

    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age >= 18


def validate_hex_color(value: str | None) -> bool:
    if value is None:
        return True
    return bool(HEX_COLOR_RE.match(value))


def validate_theme_payload(data: dict) -> tuple[dict, list[str]]:
    errors = []
    cleaned: dict = {}

    wallpaper_type = data.get("wallpaper_type")
    if wallpaper_type not in ALLOWED_WALLPAPER_TYPES:
        errors.append("wallpaper_type must be one of: " + ", ".join(sorted(ALLOWED_WALLPAPER_TYPES)))
    else:
        cleaned["wallpaper_type"] = wallpaper_type
        wallpaper_value = data.get("wallpaper_value")
        if not isinstance(wallpaper_value, str) or not wallpaper_value.strip():
            errors.append("wallpaper_value is required")
        else:
            cleaned["wallpaper_value"] = wallpaper_value.strip()[:512]

    for field in ("bubble_color_sent", "bubble_color_received"):
        value = data.get(field)
        if value is not None and not validate_hex_color(value):
            errors.append(f"{field} must be a hex color")
        else:
            cleaned[field] = value

    bubble_shape = data.get("bubble_shape")
    if bubble_shape is not None and bubble_shape not in ALLOWED_BUBBLE_SHAPES:
        errors.append("bubble_shape must be 'rounded' or 'compact'")
    else:
        cleaned["bubble_shape"] = bubble_shape

    text_scale = data.get("text_scale")
    if text_scale is not None and not (0.5 <= float(text_scale) <= 2.0):
        errors.append("text_scale must be between 0.5 and 2.0")
    else:
        cleaned["text_scale"] = text_scale

    dark_brightness = data.get("dark_mode_brightness")
    if dark_brightness is not None and not (0.0 <= float(dark_brightness) <= 1.0):
        errors.append("dark_mode_brightness must be between 0.0 and 1.0")
    else:
        cleaned["dark_mode_brightness"] = dark_brightness

    doodle_overlay_id = data.get("doodle_overlay_id")
    if doodle_overlay_id is not None:
        try:
            import uuid as _uuid

            cleaned["doodle_overlay_id"] = _uuid.UUID(str(doodle_overlay_id))
        except ValueError:
            errors.append("doodle_overlay_id must be a valid id")

    return cleaned, errors
