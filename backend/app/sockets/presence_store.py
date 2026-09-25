"""Redis-backed presence store (doc 8 §C9 — the dobato import).

Milan's presence was a per-process dict: with more than one gunicorn worker
each worker only saw its own sockets, so "online" silently lied. One Redis
SET per user holds every connected socket id with a TTL so a hard crash
cannot orphan a presence key. Multi-worker safe; degrades to no-op (never
crashes) when Redis is unreachable."""
import logging

logger = logging.getLogger(__name__)

_TTL_SECONDS = 86400  # 24h — heartbeat renews long before expiry


def _redis():
    from flask import current_app

    client = current_app.extensions.get("redis_presence_client")
    if client is not None:
        return client
    import redis as redis_lib

    try:
        url = current_app.config.get("REDIS_URL") or "redis://localhost:6379/0"
        client = redis_lib.Redis.from_url(url, decode_responses=True, socket_connect_timeout=1)
        client.ping()
    except Exception:
        logger.warning("presence store: redis unavailable; presence degrades")
        client = None
    current_app.extensions["redis_presence_client"] = client
    return client


def _key(user_id: str) -> str:
    return f"presence:user:{user_id}"


def _beat_key(user_id: str) -> str:
    return f"presence:beat:{user_id}"


def register_connection(user_id: str, socket_id: str) -> None:
    client = _redis()
    if client is None:
        return
    try:
        pipe = client.pipeline()
        pipe.sadd(_key(user_id), socket_id)
        pipe.expire(_key(user_id), _TTL_SECONDS)
        pipe.execute()
    except Exception:
        logger.warning("presence register failed", exc_info=True)


def mark_active(user_id: str, ttl_seconds: int = 150) -> None:
    """Socket-independent liveness marker set by the REST heartbeat.

    A socket id is removed on disconnect; an HTTP beat has no such event, so
    this key expires on its own. [is_online] treats either signal as online,
    which keeps "Active now" true while the socket is reconnecting."""
    client = _redis()
    if client is None:
        return
    try:
        client.set(_beat_key(user_id), "1", ex=ttl_seconds)
    except Exception:
        logger.warning("presence beat failed", exc_info=True)


def remove_connection(user_id: str, socket_id: str) -> None:
    client = _redis()
    if client is None:
        return
    try:
        client.srem(_key(user_id), socket_id)
    except Exception:
        logger.warning("presence remove failed", exc_info=True)


def is_online(user_id: str) -> bool:
    client = _redis()
    if client is None:
        return False
    try:
        if client.scard(_key(user_id)) > 0:
            return True
        return bool(client.exists(_beat_key(user_id)))
    except Exception:
        return False
