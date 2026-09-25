import base64
import os

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import String, TypeDecorator

from flask import current_app


def _fernet() -> Fernet:
    key = current_app.config.get("ENCRYPTION_KEY") or ""
    if not key:
        key = Fernet.generate_key().decode()
    if len(key) < 44 or not key.endswith("="):
        key = base64.urlsafe_b64encode(key.encode().ljust(32)[:32]).decode()
    return Fernet(key.encode())


class EncryptedString(TypeDecorator):
    """Application-layer encrypted string column for sensitive data (phone, location)."""

    impl = String(512)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return _fernet().encrypt(str(value).encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return _fernet().decrypt(value.encode()).decode()
        except (InvalidToken, ValueError):
            return None


def generate_encryption_key() -> str:
    return Fernet.generate_key().decode()


def hash_face_embedding(vector: list[float]) -> str:
    import hashlib

    packed = ",".join(f"{v:.6f}" for v in vector).encode()
    return hashlib.sha256(packed).hexdigest()


def new_otp(length: int = 6) -> str:
    return "".join(str(os.urandom(1)[0] % 10) for _ in range(length))
