import os

# eventlet monkey-patching is required for Flask-SocketIO WebSocket support
# under the gunicorn eventlet worker — but it BREAKS Celery's prefork pool
# ("RLock(s) were not greened", workers hang without consuming tasks). Gate it
# on the gunicorn entrypoint so the API greens itself and Celery does not.
if os.environ.get("MILAN_GREEN") == "1":
    import eventlet

    eventlet.monkey_patch()

from app import create_app
from app.extensions import celery_app, init_celery

flask_app = create_app(os.environ.get("MILAN_ENV", "prod"))
celery = init_celery(flask_app)

if __name__ == "__main__":
    flask_app.run(
        host=os.environ.get("MILAN_HOST", "127.0.0.1"),
        port=int(os.environ.get("MILAN_PORT", "5000")),
        debug=os.environ.get("MILAN_DEBUG", "1") == "1",
        use_reloader=os.environ.get("MILAN_RELOAD", "0") == "1",
    )
