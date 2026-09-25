import logging
import uuid

import click
from flask import Flask, jsonify, send_from_directory

from app.utils.validators import normalize_phone

from app.config import config_by_name, validate_config
from app.extensions import db, migrate, jwt, socketio, cors, limiter


def create_app(config_name: str = "dev") -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    app.config["MILAN_ENV"] = config_name
    validate_config(app.config, config_name)

    configure_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    cors.init_app(
        app,
        origins=app.config["CORS_ALLOWED_ORIGINS"],
        supports_credentials=True,
    )

    from app.models import User
    from app.utils.validators import validate_age_18

    @jwt.user_lookup_loader
    def load_current_user(_jwt_header, jwt_data):
        identity = jwt_data.get("sub")
        try:
            user = db.session.get(User, uuid.UUID(identity)) if identity else None
        except (TypeError, ValueError, AttributeError):
            return None
        if user is None or user.deleted_at is not None or user.account_status != "active":
            return None
        if not validate_age_18(user.date_of_birth):
            return None
        return user

    @jwt.user_lookup_error_loader
    def user_lookup_error(_jwt_header, _jwt_data):
        return jsonify({"error": "account_suspended", "message": "This account is unavailable."}), 401

    @jwt.additional_claims_loader
    def add_role_claims(identity: str) -> dict:
        try:
            user = db.session.get(User, uuid.UUID(identity)) if identity else None
        except (ValueError, AttributeError):
            user = None
        return {"role": user.role if user else "user"}

    from app import models  # noqa: F401  (register all models with SQLAlchemy)
    from app.blueprints.auth import auth_bp
    from app.blueprints.profile import profile_bp, verification_bp
    from app.blueprints.media import media_bp
    from app.blueprints.discovery import discovery_bp
    from app.blueprints.matching import matching_bp
    from app.blueprints.chat import chat_bp
    from app.blueprints.jhalak import jhalak_bp
    from app.blueprints.saathi import saathi_bp
    from app.blueprints.safety import safety_bp
    from app.blueprints.notifications import notifications_bp
    from app.blueprints.billing import billing_bp
    from app.blueprints.personalization import personalization_bp
    from app.blueprints.admin import admin_bp

    api_prefix = "/api/v1"
    app.register_blueprint(auth_bp, url_prefix=f"{api_prefix}/auth")
    app.register_blueprint(profile_bp, url_prefix=f"{api_prefix}/profile")
    # /verification prefix MUST match the app's paths (mobile posts to
    # /verification/liveness) — a bare prefix here overrides the blueprint's
    # own url_prefix and 404s every verification call
    app.register_blueprint(verification_bp, url_prefix=f"{api_prefix}/verification")
    app.register_blueprint(media_bp, url_prefix=f"{api_prefix}/media")
    app.register_blueprint(discovery_bp, url_prefix=f"{api_prefix}/discovery")
    app.register_blueprint(matching_bp, url_prefix=f"{api_prefix}")
    app.register_blueprint(chat_bp, url_prefix=f"{api_prefix}/matches")
    app.register_blueprint(jhalak_bp, url_prefix=f"{api_prefix}/jhalak")
    app.register_blueprint(saathi_bp, url_prefix=f"{api_prefix}/saathi")
    app.register_blueprint(safety_bp, url_prefix=f"{api_prefix}/safety")
    app.register_blueprint(notifications_bp, url_prefix=f"{api_prefix}/notifications")
    app.register_blueprint(billing_bp, url_prefix=f"{api_prefix}/billing")
    app.register_blueprint(personalization_bp, url_prefix=f"{api_prefix}/personalization")
    app.register_blueprint(admin_bp, url_prefix=f"{api_prefix}/admin")

    from app.sockets.chat_events import register_chat_events
    from app.sockets.presence_events import register_presence_events
    from app.sockets.audio_room_events import register_audio_room_events

    # async_mode: "threading" CANNOT serve WebSocket — it forces every client
    # onto long-polling. With eventlet installed the default auto-detect picks
    # eventlet, which upgrades properly.
    #
    # message_queue is the fix for AI/auto-text messages never appearing live:
    # Celery workers run in a SEPARATE process, so their broadcast_message /
    # broadcast_typing emits went into a socketio instance with zero connected
    # clients and vanished. Routing emits through Redis makes any process able
    # to reach the API process's sockets.
    socketio.init_app(
        app,
        cors_allowed_origins=app.config["CORS_ALLOWED_ORIGINS"],
        message_queue=app.config.get("CELERY_BROKER_URL") or "redis://localhost:6379/0",
        channel="milan-socketio",
    )
    register_chat_events(socketio)
    register_presence_events(socketio)
    register_audio_room_events(socketio)

    @app.get("/media/<path:key>")
    def serve_media(key: str):
        from pathlib import Path

        uploads = Path(app.instance_path) / "uploads"
        return send_from_directory(uploads, key)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "milan-api"})

    @app.cli.command("init-db")
    def init_db():
        """Create all tables (dev bootstrap; production uses Alembic)."""
        with app.app_context():
            db.create_all()
        click.echo("database initialized")

    @app.cli.command("seed-admin")
    @click.argument("phone")
    def seed_admin(phone: str):
        """Promote a phone-verified user to admin role."""
        from app.models import User

        normalized = normalize_phone(phone)
        with app.app_context():
            user = User.query.filter_by(phone=normalized).first()
            if user is None:
                click.echo(f"no user found for {normalized}; sign up first, then re-run")
                return
            user.role = "admin"
            db.session.commit()
        click.echo(f"{normalized} is now an admin")

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "not_found",
                        "message": "We couldn't find what you were looking for."}), 404

    @app.errorhandler(500)
    def server_error(_e):
        return jsonify({"error": "internal_error",
                        "message": "Something went wrong on our side. Please try again."}), 500

    return app


def configure_logging(app: Flask) -> None:
    level = logging.DEBUG if app.config.get("DEBUG") else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
