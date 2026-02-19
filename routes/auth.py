import jwt
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from flask_login import logout_user, login_required, current_user
from models import User
from extensions import bcrypt
from serializers import serialize_user
from functools import wraps

bp = Blueprint("auth", __name__)


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return jsonify({"success": False, "error": "unauthorized"}), 401
        try:
            data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
            user = User.query.get(data["user_id"])
            if not user:
                return jsonify({"success": False, "error": "unauthorized"}), 401
            request.current_user = user
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "error": "token_expired"}), 401
        except Exception:
            return jsonify({"success": False, "error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


@bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"success": False, "message": "Invalid email or password"}), 401

    token = jwt.encode({
        "user_id": user.id,
        "exp": datetime.utcnow() + timedelta(days=7)
    }, current_app.config["SECRET_KEY"], algorithm="HS256")

    return jsonify({
        "success": True,
        "token": token,
        "user": serialize_user(user),
        "must_change_password": user.must_change_password,
    })


@bp.route("/api/auth/logout", methods=["POST"])
def logout():
    return jsonify({"success": True, "message": "Logged out"})


@bp.route("/api/auth/me")
@token_required
def me():
    return jsonify({"success": True, "user": serialize_user(request.current_user)})