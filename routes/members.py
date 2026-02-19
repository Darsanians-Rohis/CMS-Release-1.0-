import csv
from io import TextIOWrapper, StringIO
from flask import Blueprint, request, jsonify
from routes.auth import token_required
from sqlalchemy.exc import IntegrityError
from extensions import db, bcrypt
from models import User
from serializers import serialize_user

bp = Blueprint("members", __name__)

ADMIN_ROLES = {"admin", "ketua", "pembina"}


def _require_admin():
    current_user = request.current_user
    if current_user.role not in ADMIN_ROLES:
        return jsonify({"success": False, "message": "Access denied"}), 403


@bp.route("/api/members")
@token_required
def list_members():
    users = User.query.order_by(User.name).all()
    return jsonify({"success": True, "members": [serialize_user(u) for u in users]})


@bp.route("/api/members", methods=["POST"])
@token_required
def add_member():
    err = _require_admin()
    if err:
        return err

    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    class_name = data.get("class_name") or None
    role = data.get("role", "member")

    if not name or not email:
        return jsonify({"success": False, "message": "Name and email are required"}), 400

    hashed = bcrypt.generate_password_hash("rohisnew").decode("utf-8")
    user = User(name=name, email=email, class_name=class_name, role=role, password=hashed)
    try:
        db.session.add(user)
        db.session.commit()
        return jsonify({"success": True, "message": f"Member {name} created", "member": serialize_user(user)}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({"success": False, "message": "A user with that email already exists"}), 409


@bp.route("/api/members/batch-add", methods=["POST"])
@token_required
def batch_add_members():
    err = _require_admin()
    if err:
        return err

    hashed = bcrypt.generate_password_hash("rohisnew").decode("utf-8")
    added, errors = 0, []

    def _add(name, email, class_name, role):
        nonlocal added
        if not name or not email:
            return
        email_l = email.strip().lower()
        if User.query.filter_by(email=email_l).first():
            errors.append(f"User with email {email_l} already exists")
            return
        try:
            db.session.add(User(
                name=name.strip(), email=email_l,
                class_name=class_name or None,
                role=role or "member", password=hashed,
            ))
            db.session.commit()
            added += 1
        except IntegrityError:
            db.session.rollback()
            errors.append(f"Failed to add {email_l}")

    csv_file = request.files.get("csv_file")
    if csv_file and csv_file.filename:
        try:
            stream = TextIOWrapper(csv_file.stream, encoding="utf-8")
            for row in csv.reader(stream):
                if len(row) >= 2:
                    _add(row[0], row[1], row[2] if len(row) > 2 else None, row[3] if len(row) > 3 else "member")
        except Exception as e:
            errors.append(f"CSV parse error: {e}")

    bulk_text = (request.form.get("bulk_text") or "").strip()
    if not bulk_text and request.is_json:
        bulk_text = (request.get_json() or {}).get("bulk_text", "")
    for line in StringIO(bulk_text):
        parts = [p.strip() for p in line.strip().split(",")]
        if len(parts) >= 2:
            _add(parts[0], parts[1], parts[2] if len(parts) > 2 else None, parts[3] if len(parts) > 3 else "member")

    return jsonify({"success": True, "added": added, "errors": errors}), 201 if added else 200


@bp.route("/api/members/batch-delete", methods=["POST"])
@token_required
def batch_delete_members():
    current_user = request.current_user
    err = _require_admin()
    if err:
        return err

    data = request.get_json() or {}
    ids = data.get("ids", [])
    if not ids:
        return jsonify({"success": False, "message": "No member IDs provided"}), 400

    users_to_delete = User.query.filter(User.id.in_(ids)).all()
    if any(u.id == current_user.id for u in users_to_delete):
        return jsonify({"success": False, "message": "Cannot delete your own account"}), 400

    admin_count = User.query.filter_by(role="admin").count()
    removing_admins = sum(1 for u in users_to_delete if u.role == "admin")
    if admin_count - removing_admins < 1:
        return jsonify({"success": False, "message": "Cannot remove the last admin"}), 400

    deleted, failed = 0, []
    for u in users_to_delete:
        try:
            db.session.delete(u)
            db.session.commit()
            deleted += 1
        except Exception:
            db.session.rollback()
            failed.append(u.email)

    return jsonify({"success": True, "deleted": deleted, "failed": failed})


@bp.route("/api/members/<int:user_id>", methods=["DELETE"])
@token_required
def delete_member(user_id):
    current_user = request.current_user
    err = _require_admin()
    if err:
        return err

    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({"success": False, "message": "Cannot delete your own account"}), 400
    if user.role == "admin" and User.query.filter_by(role="admin").count() <= 1:
        return jsonify({"success": False, "message": "Cannot delete the last admin"}), 400

    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"success": True, "message": "Member deleted"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@bp.route("/api/members/<int:user_id>/role", methods=["PUT"])
@token_required
def change_member_role(user_id):
    err = _require_admin()
    if err:
        return err

    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    new_role = data.get("role")
    if not new_role:
        return jsonify({"success": False, "message": "Role is required"}), 400

    if user.role == "admin" and new_role != "admin":
        if User.query.filter_by(role="admin").count() <= 1:
            return jsonify({"success": False, "message": "Cannot remove the last admin's role"}), 400

    user.role = new_role
    db.session.commit()
    return jsonify({"success": True, "message": "Role updated", "member": serialize_user(user)})


@bp.route("/api/members/<int:user_id>/pic", methods=["PUT"])
@token_required
def assign_member_pic(user_id):
    err = _require_admin()
    if err:
        return err

    from models import Pic
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    pic_id = data.get("pic_id")

    if pic_id:
        pic = Pic.query.get(pic_id)
        if not pic:
            return jsonify({"success": False, "message": "Invalid PIC"}), 404
        user.pic_id = pic_id
        message = f"{user.name} assigned to {pic.name}"
    else:
        user.pic_id = None
        message = f"PIC assignment removed from {user.name}"

    db.session.commit()
    return jsonify({"success": True, "message": message, "member": serialize_user(user)})


@bp.route("/api/members/<int:user_id>/attendance-permission", methods=["PUT"])
@token_required
def toggle_attendance_permission(user_id):
    err = _require_admin()
    if err:
        return err

    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    if "can_mark" in data:
        user.can_mark_attendance = bool(data["can_mark"])
    else:
        user.can_mark_attendance = not user.can_mark_attendance

    db.session.commit()
    return jsonify({
        "success": True,
        "can_mark_attendance": user.can_mark_attendance,
        "member": serialize_user(user),
    })
