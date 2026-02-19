from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Pic, SessionPIC
from serializers import serialize_pic

bp = Blueprint("pics", __name__)

ADMIN_ROLES = {"admin", "ketua", "pembina"}


def _require_admin():
    if current_user.role not in ADMIN_ROLES:
        return jsonify({"success": False, "message": "Access denied"}), 403


@bp.route("/api/pics")
@login_required
def list_pics():
    pics = Pic.query.order_by(Pic.name).all()
    return jsonify({"success": True, "pics": [serialize_pic(p) for p in pics]})


@bp.route("/api/pics", methods=["POST"])
@login_required
def create_pic():
    err = _require_admin()
    if err:
        return err

    data = request.get_json() or {}
    name = data.get("name", "").strip()
    description = data.get("description", "").strip() or None

    if not name:
        return jsonify({"success": False, "message": "PIC name is required"}), 400
    if Pic.query.filter_by(name=name).first():
        return jsonify({"success": False, "message": f"PIC '{name}' already exists"}), 409

    pic = Pic(name=name, description=description)
    db.session.add(pic)
    db.session.commit()
    return jsonify({"success": True, "message": f"PIC '{name}' created", "pic": serialize_pic(pic)}), 201


@bp.route("/api/pics/<int:pic_id>", methods=["DELETE"])
@login_required
def delete_pic(pic_id):
    err = _require_admin()
    if err:
        return err

    pic = Pic.query.get_or_404(pic_id)
    for user in pic.members:
        user.pic_id = None
        user.can_mark_attendance = False
    SessionPIC.query.filter_by(pic_id=pic_id).delete()
    db.session.delete(pic)
    db.session.commit()
    return jsonify({"success": True, "message": f"PIC '{pic.name}' deleted"})
