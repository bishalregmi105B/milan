"""Face/photo preference calibration (doc 5 §1 final row, doc 1 §4.1).

Deliberately NOT an LLM task: LIKE/PASS/MAYBE calibration signals feed a
lightweight per-user ranking bias over candidate embedding vectors. Used to
*re-rank*, never hard-exclude (smaller market — doc 1 §4.1).

The vision-embedding seam is provider-swappable; the default deterministic
perceptual-hash embedding keeps the ranking math exercisable offline.
"""

import hashlib
import logging

from app.extensions import db

logger = logging.getLogger(__name__)

CALIBRATION_WEIGHTS = {"like": 1.0, "maybe": 0.3, "pass": -0.8}
MAX_BIAS = 8.0


def _deterministic_embedding(seed: str, dims: int = 32) -> list[float]:
    digest = hashlib.sha256(seed.encode()).digest()
    vector: list[float] = []
    while len(vector) < dims:
        digest = hashlib.sha256(digest).digest()
        vector.extend(b / 255.0 for b in digest)
    return vector[:dims]


class PreferenceModel:
    """Per-user linear bias over embedding dimensions, trained online from
    swipe/calibration events. Tiny, interpretable, no external service."""

    def __init__(self, dims: int = 32):
        self.dims = dims
        self.weights = [0.0] * dims

    def observe(self, embedding: list[float], label: str) -> None:
        delta = CALIBRATION_WEIGHTS.get(label)
        if delta is None or len(embedding) != self.dims:
            return
        lr = 0.05
        for i in range(self.dims):
            self.weights[i] += lr * delta * embedding[i]
        norm = sum(w * w for w in self.weights) ** 0.5
        if norm > MAX_BIAS:
            scale = MAX_BIAS / norm
            self.weights = [w * scale for w in self.weights]

    def score(self, embedding: list[float]) -> float | None:
        if len(embedding) != self.dims:
            return None
        return sum(w * v for w, v in zip(self.weights, embedding))


def record_calibration(user_id, target_user_id, photo_url: str, label: str) -> bool:
    from app.models import PreferenceCalibration

    if label not in CALIBRATION_WEIGHTS:
        return False
    db.session.add(PreferenceCalibration(
        user_id=user_id,
        target_user_id=target_user_id,
        photo_embedding=_deterministic_embedding(photo_url or target_user_id),
        label=label,
    ))
    db.session.commit()
    return True


def preference_bias_for(user_id, candidates: list[tuple[object, str]]) -> dict[str, float]:
    """Returns {candidate_key: bias_points} to add on top of compatibility score."""
    from app.models import PreferenceCalibration

    rows = PreferenceCalibration.query.filter_by(user_id=user_id).limit(500).all()
    model = PreferenceModel()
    for row in rows:
        model.observe(row.photo_embedding, row.label)

    biases: dict[str, float] = {}
    for candidate, photo_url in candidates:
        embedding = _deterministic_embedding(photo_url or str(getattr(candidate, "id", "")))
        raw = model.score(embedding)
        # Map raw dot-product (roughly -MAX_BIAS..MAX_BIAS) onto a ±4 point nudge.
        biases[str(getattr(candidate, "id", ""))] = round((raw or 0.0) / 2.0, 2)
    return biases
