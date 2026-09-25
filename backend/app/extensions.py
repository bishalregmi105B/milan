from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from celery import Celery

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
socketio = SocketIO()
cors = CORS()
limiter = Limiter(key_func=get_remote_address)
cache = None

celery_app = Celery("milan", include=[
    "app.tasks.media_tasks",
    "app.tasks.moderation_tasks",
    "app.tasks.notification_tasks",
    "app.tasks.matching_tasks",
    "app.tasks.verification_tasks",
    "app.tasks.companion_tasks",
])


def init_celery(app):
    celery_app.conf.update(
        broker_url=app.config["CELERY_BROKER_URL"],
        result_backend=app.config["CELERY_RESULT_BACKEND"],
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Asia/Kathmandu",
        enable_utc=True,
        # Beat schedule (master plan §7.3): the milan-beat systemd service runs
        # `celery beat`, so these now actually fire — proactive messaging,
        # status posts, mood decay and the notification queue were previously
        # dead code without an external trigger.
        beat_schedule={
            "saathi-proactive-check": {
                "task": "app.tasks.notification_tasks.saathi_proactive_check",
                "schedule": 3600.0,  # hourly, master plan §4.4
            },
            "saathi-status-posts": {
                "task": "app.tasks.notification_tasks.saathi_status_posts",
                "schedule": 60.0 * 60.0 * 5.5,  # ~3x/day within tier caps
            },
            "saathi-open-loop-followup": {
                "task": "app.tasks.notification_tasks.saathi_open_loop_followup",
                "schedule": 60.0 * 60.0 * 26.0,  # daily sweep at drifting hours
            },
            "saathi-mood-decay": {
                "task": "app.tasks.notification_tasks.saathi_mood_decay",
                "schedule": 60.0 * 60.0 * 24.0,  # nightly-ish
            },
            "saathi-persona-evolution": {
                "task": "app.tasks.notification_tasks.saathi_persona_evolution",
                "schedule": 60.0 * 60.0 * 24.0,  # §13.3 nightly continuous evolution
            },
            "saathi-nightly-diary": {
                "task": "app.tasks.notification_tasks.saathi_nightly_diary",
                "schedule": 60.0 * 60.0 * 24.0,  # companion diary after 21:00 NPT
            },
            "saathi-quests-refresh": {
                "task": "app.tasks.notification_tasks.saathi_quests_refresh",
                "schedule": 60.0 * 60.0 * 26.0,  # duo quests + anniversary capsules
            },
            "send-scheduled-notifications": {
                "task": "app.tasks.notification_tasks.send_scheduled_notifications",
                "schedule": 300.0,  # every 5 minutes — predicted send times
            },
            # ── doc 8 §C5 initiative engine ───────────────────────────────
            # Replaces the hourly proactive check as the primary driver: a
            # scored tick every 10 minutes can catch the moment the user is
            # usually online, which an hourly job structurally cannot.
            "companion-initiative-tick": {
                "task": "app.tasks.companion_tasks.companion_initiative_tick",
                "schedule": 600.0,
            },
            # Recovery sweep for deferred replies whose ETA task was lost with
            # the broker (the reply is on the session row, so it is never lost).
            "companion-deferred-sweep": {
                "task": "app.tasks.companion_tasks.deliver_due_deferred_replies",
                "schedule": 120.0,
            },
            # Context compaction: bulk 8B work, kept off the request path.
            "companion-compaction": {
                "task": "app.tasks.companion_tasks.compact_stale_contexts",
                "schedule": 60.0 * 60.0 * 6.0,
            },
            # Match expiry: warn at 48h of silence, expire at 72h.
            "match-expiry-sweep": {
                "task": "app.tasks.matching_tasks.expire_stale_matches",
                "schedule": 60.0 * 60.0,
            },
        },
    )

    class ContextTask(celery_app.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = ContextTask
    return celery_app


def dispatch(task, *args, **kwargs) -> bool:
    """Queue a Celery task without ever blocking or failing the request path.
    When the broker is unreachable (dev without Redis, brief outage), the task
    is skipped and logged — the API response still goes out.

    `countdown=` is passed through to apply_async so callers can schedule a task
    for later (deferred companion replies) without importing Celery directly."""
    import logging

    countdown = kwargs.pop("countdown", None)
    try:
        celery_app.conf.broker_connection_timeout = 1
        celery_app.conf.task_publish_retry_policy = {"max_retries": 0}
        if countdown:
            task.apply_async(args=args, kwargs=kwargs, countdown=countdown)
        else:
            task.delay(*args, **kwargs)
        return True
    except Exception as exc:  # kombu/redis connection errors land here
        logging.getLogger(__name__).warning(
            "broker unavailable; skipped task %s (%s)", task.name, exc
        )
        return False
