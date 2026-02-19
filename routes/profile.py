import os
from flask import Blueprint, request, jsonify, Response
from routes.auth import token_required
from werkzeug.utils import secure_filename
from extensions import db, bcrypt
from models import User
from serializers import serialize_user

bp = Blueprint("profile", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route("/api/profile", methods=["PUT"])
@token_required
def update_profile():
    current_user = request.current_user
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if username:
        existing = User.query.filter_by(username=username).first()
        if existing and existing.id != current_user.id:
            return jsonify({"success": False, "message": "Username already taken"}), 409
        current_user.username = username

    if password:
        current_user.password = bcrypt.generate_password_hash(password).decode("utf-8")

    db.session.commit()
    return jsonify({"success": True, "message": "Profile updated", "user": serialize_user(current_user)})


@bp.route("/api/profile/password", methods=["PUT"])
@token_required
def change_password():
    current_user = request.current_user
    data = request.get_json() or {}
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")
    confirm_password = data.get("confirm_password", "")

    if not bcrypt.check_password_hash(current_user.password, old_password):
        return jsonify({"success": False, "message": "Incorrect current password"}), 400
    if new_password != confirm_password:
        return jsonify({"success": False, "message": "New passwords do not match"}), 400
    if len(new_password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters"}), 400

    current_user.password = bcrypt.generate_password_hash(new_password).decode("utf-8")
    current_user.must_change_password = False
    db.session.commit()
    return jsonify({"success": True, "message": "Password updated successfully"})


@bp.route("/api/profile/picture", methods=["POST"])
@token_required
def upload_pfp():
    current_user = request.current_user
    file = request.files.get("pfp")
    if not file or not file.filename:
        return jsonify({"success": False, "message": "No file provided"}), 400
    if not _allowed_file(file.filename):
        return jsonify({"success": False, "message": "Invalid file type. Allowed: png, jpg, jpeg, webp"}), 400

    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > 5 * 1024 * 1024:
        return jsonify({"success": False, "message": "File too large (max 5 MB)"}), 400

    current_user.profile_picture_data = file.read()
    current_user.profile_picture_filename = secure_filename(file.filename)
    db.session.commit()
    return jsonify({
        "success": True,
        "message": "Profile picture updated",
        "url": f"/api/profile/picture/{current_user.id}",
    })


@bp.route("/api/profile/picture/<int:user_id>")
def serve_profile_picture(user_id):
    user = User.query.get_or_404(user_id)
    if user.profile_picture_data:
        filename = user.profile_picture_filename or "image.png"
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
        mime = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
        }.get(ext, "image/png")
        return Response(user.profile_picture_data, mimetype=mime)

    default = os.path.join("static", "uploads", "profiles", "default.png")
    if os.path.exists(default):
        with open(default, "rb") as f:
            return Response(f.read(), mimetype="image/png")
    return jsonify({"error": "not_found"}), 404
