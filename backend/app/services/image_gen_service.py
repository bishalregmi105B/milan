"""Phase 3 image generation (master plan §12.1): AI-illustrated companion
media behind a hard service boundary. Compliance spine:
- ALWAYS AI-labeled (every payload carries an ai_label the client must show);
- ILLUSTRATED/ARTISTIC ONLY — prompts are post-pended with an illustration
  directive and a photorealistic-human ban, so no output can pass as a real
  photo of a person;
- free providers (Pollinations flux via g4f) with graceful degradation.
"""
import logging
import secrets
import urllib.parse

import requests

logger = logging.getLogger(__name__)

ILLUSTRATION_SUFFIX = (
    ", soft illustrated anime-adjacent art style, warm colors, NOT a photo, "
    "no real human likeness, painterly"
)

_PollinationsImage = None  # cached g4f provider class


def _g4f_client():
    """g4f client with PollinationsImage pinned (active_by_default=False in
    g4f, so it must be explicit). Returns None when g4f is unavailable."""
    global _PollinationsImage
    try:
        import g4f.Provider as P
    except Exception:  # noqa: BLE001 — g4f optional at runtime
        return None
    if _PollinationsImage is None:
        _PollinationsImage = P.PollinationsImage
    from g4f.client import Client

    return Client(image_provider=_PollinationsImage)


def generate_image(prompt: str, *, width: int = 768, height: int = 768,
                   seed: int | None = None) -> dict:
    """Return {"url", "ai_label", "provider"} for an illustrated image, or
    raise ImageGenUnavailableError. Primary: g4f PollinationsImage (durable
    URLs); fallback: the Pollinations direct-URL API (verified live)."""
    styled = f"{prompt[:700]}{ILLUSTRATION_SUFFIX}"
    seed = seed if seed is not None else secrets.randbelow(1_000_000)
    errors: list[str] = []

    client = _g4f_client()
    if client is not None:
        try:
            resp = client.images.generate(
                model="flux", prompt=styled, response_format="url",
                width=width, height=height, seed=seed, nologo=True,
            )
            url = getattr(resp.data[0], "url", None)
            if url:
                return {"url": url, "ai_label": "AI-illustrated", "provider": "g4f/pollinations"}
            errors.append("g4f returned empty url")
        except Exception as exc:  # noqa: BLE001 — provider rotation is normal
            errors.append(f"g4f: {exc}")

    # direct Pollinations URL API — plain GET, no key (research §6)
    try:
        q = urllib.parse.urlencode({
            "width": width, "height": height, "model": "flux",
            "nologo": "true", "seed": seed,
        })
        direct = ("https://image.pollinations.ai/prompt/"
                  + urllib.parse.quote(styled) + "?" + q)
        probe = requests.head(direct, timeout=30, allow_redirects=True)
        if probe.status_code == 200:
            return {"url": direct, "ai_label": "AI-illustrated", "provider": "pollinations"}
        errors.append(f"pollinations HEAD {probe.status_code}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"pollinations: {exc}")

    raise ImageGenUnavailableError("; ".join(errors) or "no provider available")


class ImageGenUnavailableError(Exception):
    pass
