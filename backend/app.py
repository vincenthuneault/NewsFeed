"""Factory Flask — application principale."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from flask import Flask, send_from_directory

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def create_app(config: dict | None = None) -> Flask:
    """Crée et configure l'application Flask."""
    app = Flask(
        __name__,
        static_folder=str(PROJECT_ROOT / "static"),
        static_url_path="/static",
    )

    if config is None:
        from core.config import load_config
        config = load_config()

    app.config["PROJECT_CONFIG"] = config
    app.config["SECRET_KEY"] = config.get("server", {}).get("secret_key", "dev-secret")
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

    # Blueprints API
    from backend.api.auth import auth_bp
    from backend.api.bugs import bugs_bp
    from backend.api.comments import comments_bp
    from backend.api.feed import feed_bp
    from backend.api.feedback import feedback_bp
    from backend.api.health import health_bp
    from backend.api.settings import settings_bp
    from backend.api.speech import speech_bp

    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(bugs_bp, url_prefix="/api")
    app.register_blueprint(comments_bp, url_prefix="/api")
    app.register_blueprint(feed_bp, url_prefix="/api")
    app.register_blueprint(feedback_bp, url_prefix="/api")
    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(settings_bp, url_prefix="/api")
    app.register_blueprint(speech_bp, url_prefix="/api")

    frontend_dir = PROJECT_ROOT / "frontend"

    # Fichiers qui ne doivent jamais être mis en cache par le navigateur.
    # Le SW fait déjà Network First pour JS/CSS, mais le cache HTTP du browser
    # est consulté même lors d'un fetch() SW — no-cache force une revalidation.
    _NO_CACHE_EXTS = {".html", ".js", ".css"}

    def _add_no_cache(response):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        return response

    # Service worker doit être servi à la racine
    @app.route("/sw.js")
    def service_worker():
        resp = send_from_directory(str(frontend_dir), "sw.js",
                                   mimetype="application/javascript")
        return _add_no_cache(resp)

    @app.route("/manifest.json")
    def manifest():
        return send_from_directory(str(frontend_dir), "manifest.json",
                                   mimetype="application/json")

    @app.route("/")
    def index():
        return _add_no_cache(send_from_directory(str(frontend_dir), "index.html"))

    @app.route("/<path:filename>")
    def frontend_files(filename: str):
        resp = send_from_directory(str(frontend_dir), filename)
        if any(filename.endswith(ext) for ext in _NO_CACHE_EXTS):
            _add_no_cache(resp)
        return resp

    return app
