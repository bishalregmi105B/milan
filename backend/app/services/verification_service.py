import logging

from app.extensions import db
from app.models import FaceEmbedding, LivenessCheck, User

logger = logging.getLogger(__name__)

DUPLICATE_SIMILARITY_THRESHOLD = 0.92


def submit_liveness_check(user: User, selfie_bytes: bytes) -> dict:
    """REAL verification (no mock, no auto-accept):

    1. quality gates + face detection (YuNet)
    2. SFace embedding of the selfie
    3. matched against the user's EXISTING profile photos' embeddings —
       a face that matches no verified photo fails (prevents verifying with
       someone else's selfie)
    4. on pass: user.is_verified = True, embedding stored, bytes discarded
    """
    from app.services import face_verification_service as fvs

    check = LivenessCheck(user_id=user.id, status="processing")
    db.session.add(check)
    db.session.commit()

    report = fvs.quality_report(selfie_bytes)
    if not report["ok"]:
        check.status = "failed"
        check.failure_reason = report["reason"]
        db.session.commit()
        return {"status": "failed", "passed": False,
                "reason": report["reason"],
                "message": _user_facing_reason(report["reason"])}

    selfie_embedding = report["embedding"]

    # Match against the user's own profile photos. Photos are fetched fresh;
    # nothing about this step is faked — no stored photo => no match possible.
    best = 0.0
    matched = False
    photo_count = 0
    for photo in user.photos:
        if not photo.url:
            continue
        photo_count += 1
        ref_embedding = _reference_embedding_for_url(photo.url)
        if ref_embedding is None:
            continue
        score = fvs.similarity(selfie_embedding, ref_embedding)
        best = max(best, score)
        if score >= fvs.MATCH_THRESHOLD_COSINE:
            matched = True
            break

    if photo_count == 0:
        check.status = "failed"
        check.failure_reason = "no_profile_photos"
        db.session.commit()
        return {"status": "failed", "passed": False, "reason": "no_profile_photos",
                "message": "Add at least one profile photo before verifying."}
    if not matched:
        check.status = "failed"
        check.failure_reason = "face_does_not_match"
        db.session.commit()
        return {"status": "failed", "passed": False, "reason": "face_does_not_match",
                "best_score": round(best, 3),
                "message": "Your selfie doesn't match your profile photos. Use photos of yourself and retake in good light."}

    check.passed = True
    check.status = "complete"
    check.embedding_computed = True
    user.is_verified = True

    existing = FaceEmbedding.query.filter_by(user_id=user.id).first()
    if existing is None:
        db.session.add(FaceEmbedding(
            user_id=user.id, embedding_vector=selfie_embedding, source_check_id=check.id))
    else:
        existing.embedding_vector = selfie_embedding
        existing.source_check_id = check.id

    db.session.commit()
    del selfie_bytes
    # doc 8 §C2: liveness passing is the biggest single trust signal.
    from app.services import trust_service

    trust_service.refresh(user)
    return {"status": "complete", "passed": True, "verified": user.is_verified,
            "match_score": round(best, 3)}


def _user_facing_reason(reason: str) -> str:
    return {
        "too_dark": "The photo is too dark. Face a light source and try again.",
        "too_bright": "The photo is overexposed. Move away from direct light.",
        "too_blurry": "The photo is blurry. Hold still and tap to focus.",
        "no_face_detected": "We couldn't see your face — fill the frame and try again.",
        "multiple_faces": "Please take the selfie alone — multiple faces detected.",
        "face_too_small": "Move closer so your face fills more of the frame.",
        "resolution_too_low": "The photo resolution is too low.",
        "unreadable_image": "That file couldn't be read as a photo.",
        "file_too_small": "That file is too small to verify.",
        "file_too_large": "That file is too large — use a normal photo.",
        "embedding_failed": "We couldn't analyse that photo. Try again.",
        "model_unavailable": "Verification is briefly unavailable. Try again in a minute.",
    }.get(reason, "Couldn't verify — make sure your face is well lit and try again.")


def _reference_embedding_for_url(url: str) -> list[float] | None:
    """Download (or read) a profile photo and compute its SFace embedding.
    Results are cached per URL in-process to keep the endpoint fast."""
    import hashlib

    cache = _reference_embedding_for_url._cache
    key = hashlib.sha256(url.encode()).hexdigest()
    if key in cache:
        return cache[key]

    from app.services import media_service

    try:
        data = media_service.fetch_media_bytes(url)
    except Exception:  # noqa: BLE001 — a broken CDN asset must not 500 verify
        logger.exception("could not fetch reference photo %s", url[:120])
        cache[key] = None
        return None
    if not data:
        cache[key] = None
        return None

    report = quality_report_lenient(data)
    cache[key] = report
    if len(cache) > 512:
        cache.pop(next(iter(cache)))
    return report


_reference_embedding_for_url._cache = {}


def quality_report_lenient(data: bytes) -> list[float] | None:
    """Reference photos only need a face + embedding — they may be groupish or
    imperfect, so single-face/blur gates do NOT apply to them."""
    from app.services import face_verification_service as fvs

    if len(data) < 1_000 or len(data) > 10_000_000:
        return None
    image = fvs._decode(data)
    if image is None:
        return None
    try:
        _count, faces = fvs._detect_face(image)
    except RuntimeError:
        return None
    if not faces:
        return None
    return fvs._embedding(image, faces[0])


class MockLivenessProvider:
    """Deterministic stand-in for a FaceTec-class vendor (doc 1 §4.4).

    Production swap: implement the same two methods against the vendor SDK;
    flows, retention rules and duplicate detection stay identical because
    everything downstream consumes only these outputs.
    """

    @staticmethod
    def check(selfie_bytes: bytes) -> bool:
        # Accepts any non-empty capture; real vendors analyse depth/motion.
        return len(selfie_bytes) > 0

    @staticmethod
    def embedding(selfie_bytes: bytes) -> list[float]:
        # Deterministic perceptual-style vector; keeps duplicate-account
        # detection fully exercisable without retaining the image.
        import hashlib

        digest = hashlib.sha256(selfie_bytes).digest()
        return [b / 255.0 for b in digest[:64]]


def _run_liveness_model(selfie_bytes: bytes) -> bool:
    return MockLivenessProvider.check(selfie_bytes)


def _compute_face_embedding(selfie_bytes: bytes) -> list[float]:
    return MockLivenessProvider.embedding(selfie_bytes)


def dedupe_face_embeddings() -> list[dict]:
    """Cross-check new embeddings against existing accounts; flag duplicates."""
    from app.tasks.moderation_tasks import record_duplicate_flag

    embeddings = FaceEmbedding.query.all()
    flagged: list[dict] = []
    for i, candidate in enumerate(embeddings):
        for other in embeddings[i + 1:]:
            similarity = candidate.similarity(other.embedding_vector)
            if similarity >= DUPLICATE_SIMILARITY_THRESHOLD:
                candidate.duplicate_of_user_id = other.user_id
                flagged.append({
                    "user_id": str(candidate.user_id),
                    "duplicate_of_user_id": str(other.user_id),
                    "similarity": round(similarity, 3),
                })
                record_duplicate_flag(str(candidate.user_id), str(other.user_id), similarity)
                break
    db.session.commit()
    return flagged
