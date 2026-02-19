"""
Rohis Management System — REST API Backend
==========================================
All routes return JSON. Auth is session-based (Flask-Login + cookie).
For cross-origin deployments set FRONTEND_ORIGIN in .env and ensure
the frontend sends credentials (credentials: 'include' in fetch).
"""

import os
import logging
from datetime import datetime
from flask import Flask, jsonify
from config import Config
from extensions import db, bcrypt, login_manager, migrate, cors
from models import User

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config["SESSION_COOKIE_SAMESITE"] = "None"
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    # ------------------------------------------------------------------
    # Extensions
    # ------------------------------------------------------------------
    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(
        app,
        origins=[app.config["FRONTEND_ORIGIN"]],
        supports_credentials=True,
    )
    login_manager.init_app(app)

    # ------------------------------------------------------------------
    # Login manager
    # ------------------------------------------------------------------
    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({
            "success": False,
            "error": "unauthorized",
            "message": "Login required",
        }), 401

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ------------------------------------------------------------------
    # Blueprints
    # ------------------------------------------------------------------
    from routes.auth import bp as auth_bp
    from routes.profile import bp as profile_bp
    from routes.members import bp as members_bp
    from routes.sessions import bp as sessions_bp
    from routes.attendance import bp as attendance_bp
    from routes.pics import bp as pics_bp
    from routes.notulensi import bp as notulensi_bp
    from routes.calendar import bp as calendar_bp
    from routes.piket import bp as piket_bp
    from routes.chat import bp as chat_bp

    for blueprint in (
        auth_bp, profile_bp, members_bp, sessions_bp,
        attendance_bp, pics_bp, notulensi_bp, calendar_bp,
        piket_bp, chat_bp,
    ):
        app.register_blueprint(blueprint)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------
    @app.route("/health")
    def health_check():
        return jsonify({
            "status": "ok",
            "service": "Rohis Attendance API",
            "timestamp": datetime.utcnow().isoformat(),
        })

    # ------------------------------------------------------------------
    # Error handlers
    # ------------------------------------------------------------------
    @app.errorhandler(403)
    def forbidden(_):
        return jsonify({"success": False, "error": "forbidden", "message": "You do not have permission"}), 403

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"success": False, "error": "not_found", "message": "Resource not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_):
        return jsonify({"success": False, "error": "method_not_allowed"}), 405

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"success": False, "error": "internal_server_error", "message": str(e)}), 500

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
