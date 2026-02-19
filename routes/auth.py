from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from extensions import bcrypt
from serializers import serialize_user

bp = Blueprint("auth", __name__)


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

    login_user(user)
    return jsonify({
        "success": True,
        "user": serialize_user(user),
        "must_change_password": user.must_change_password,
    })


@bp.route("/api/auth/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"success": True, "message": "Logged out"})


@bp.route("/api/auth/me")
@login_required
def me():
    return jsonify({"success": True, "user": serialize_user(current_user)})
