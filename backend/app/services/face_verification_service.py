"""Real selfie verification — NO mock, NO auto-accept (user directive).

Pipeline for `submit_liveness_check`:
  1. decode + basic sanity (resolution, format)
  2. quality gates: brightness, blur (Laplacian variance), single-face,
     minimum face size — reject with a SPECIFIC reason each
  3. face embedding via SFace (OpenCV FaceRecognizerSF, Apache-2.0 model)
  4. match against the user's existing profile photos (cosine similarity);
     a selfie that matches nobody is rejected as "face_does_not_match"
  5. store ONLY the embedding + verdict — the selfie bytes are deleted

Models (downloaded to backend/models/, both Apache-2.0 licensed via opencv_zoo):
  - face_detection_yunet_2023mar.onnx   (YuNet detector)
  - face_recognition_sface_2021dec.onnx (SFace recognizer)
"""
import logging

try:  # cv2/numpy are heavy; the import is guarded so test environments
    # without OpenCV can still import the app (verification then fails
    # closed with reason "model_unavailable" rather than crashing).
    import cv2
    import numpy as np
except ImportError:  # pragma: no cover
    cv2 = None
    np = None

logger = logging.getLogger(__name__)

# Quality gates (industry-typical starting values; tuned for phone selfies)
MIN_RESOLUTION = (240, 240)
MAX_RESOLUTION = (4096, 4096)
MIN_FACE_PX = 90            # face box must be at least this wide
MIN_FACE_RATIO = 0.08       # face width / image width
MAX_FACES = 1               # exactly one face — group shots are rejected
MIN_BRIGHTNESS = 40.0       # mean luma 0-255
MAX_BRIGHTNESS = 235.0
MIN_BLUR_VARIANCE = 45.0    # Laplacian variance (blurry photos reject)
# SFace cosine thresholds (opencv_zoo benchmark): >= 0.363 same person
MATCH_THRESHOLD_COSINE = 0.363

_yunet = None
_sface = None


def _models_dir() -> str:
    import os

    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "models")


def _detector():
    global _yunet
    if _yunet is None:
        import os

        path = os.path.join(_models_dir(), "face_detection_yunet_2023mar.onnx")
        if not os.path.exists(path):
            raise RuntimeError("YuNet model missing — run the model download step")
        # score threshold 0.6 = conservative detection
        _yunet = cv2.FaceDetectorYN.create(path, "", (320, 320), score_threshold=0.6)
    return _yunet


def _recognizer():
    global _sface
    if _sface is None:
        import os

        path = os.path.join(_models_dir(), "face_recognition_sface_2021dec.onnx")
        if not os.path.exists(path):
            raise RuntimeError("SFace model missing — run the model download step")
        _sface = cv2.FaceRecognizerSF.create(path, "")
    return _sface


def _decode(data: bytes) -> np.ndarray | None:
    buffer = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    return image


def _detect_face(image: np.ndarray):
    detector = _detector()
    h, w = image.shape[:2]
    detector.setInputSize((w, h))
    count, faces = detector.detect(image)
    if faces is None or count is None:
        return None, []
    valid = [f for f in faces if f is not None and len(f) >= 4]
    return (count if isinstance(count, int) else len(valid)), valid


def _crop_for_recognition(image: np.ndarray, face) -> np.ndarray | None:
    try:
        return _recognizer().alignCrop(image, face)
    except cv2.error:
        x, y, fw, fh = [int(v) for v in face[:4]]
        crop = image[max(0, y):y + fh, max(0, x):x + fw]
        return crop if crop.size else None


def _embedding(image: np.ndarray, face) -> list[float] | None:
    aligned = _crop_for_recognition(image, face)
    if aligned is None or aligned.size == 0:
        return None
    vec = _recognizer().feature(aligned)
    return np.asarray(vec).flatten().tolist()


def _cosine(a: list[float], b: list[float]) -> float:
    va, vb = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0.0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def quality_report(data: bytes) -> dict:
    """Run the full gate chain. Returns
    {ok: bool, reason: code|None, faces, embedding, image_shape}."""
    if cv2 is None:
        return {"ok": False, "reason": "model_unavailable", "faces": 0,
                "embedding": None, "image_shape": None}
    if len(data) < 1_000:
        return {"ok": False, "reason": "file_too_small", "faces": 0,
                "embedding": None, "image_shape": None}
    if len(data) > 10_000_000:
        return {"ok": False, "reason": "file_too_large", "faces": 0,
                "embedding": None, "image_shape": None}

    image = _decode(data)
    if image is None:
        return {"ok": False, "reason": "unreadable_image", "faces": 0,
                "embedding": None, "image_shape": None}
    h, w = image.shape[:2]
    shape = [int(w), int(h)]
    if w < MIN_RESOLUTION[0] or h < MIN_RESOLUTION[1]:
        return {"ok": False, "reason": "resolution_too_low", "faces": 0,
                "embedding": None, "image_shape": shape}
    if w > MAX_RESOLUTION[0] or h > MAX_RESOLUTION[1]:
        return {"ok": False, "reason": "resolution_too_high", "faces": 0,
                "embedding": None, "image_shape": shape}

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    brightness = float(gray.mean())
    if brightness < MIN_BRIGHTNESS:
        return {"ok": False, "reason": "too_dark", "faces": 0,
                "embedding": None, "image_shape": shape}
    if brightness > MAX_BRIGHTNESS:
        return {"ok": False, "reason": "too_bright", "faces": 0,
                "embedding": None, "image_shape": shape}

    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if blur < MIN_BLUR_VARIANCE:
        return {"ok": False, "reason": "too_blurry", "faces": 0,
                "embedding": None, "image_shape": shape}

    try:
        face_count, faces = _detect_face(image)
    except RuntimeError as exc:
        return {"ok": False, "reason": "model_unavailable", "faces": 0,
                "embedding": None, "image_shape": shape,
                "detail": str(exc)}
    if face_count == 0 or not faces:
        return {"ok": False, "reason": "no_face_detected", "faces": 0,
                "embedding": None, "image_shape": shape}
    if face_count > MAX_FACES:
        return {"ok": False, "reason": "multiple_faces", "faces": face_count,
                "embedding": None, "image_shape": shape}

    face = faces[0]
    face_w = float(face[2])
    if face_w < MIN_FACE_PX or (face_w / w) < MIN_FACE_RATIO:
        return {"ok": False, "reason": "face_too_small", "faces": 1,
                "embedding": None, "image_shape": shape}

    embedding = _embedding(image, face)
    if embedding is None:
        return {"ok": False, "reason": "embedding_failed", "faces": 1,
                "embedding": None, "image_shape": shape}

    return {"ok": True, "reason": None, "faces": 1, "embedding": embedding,
            "image_shape": shape, "brightness": brightness, "blur": blur}


def similarity(a: list[float], b: list[float]) -> float:
    return _cosine(a, b)
