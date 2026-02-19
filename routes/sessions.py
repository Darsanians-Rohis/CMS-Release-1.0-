from flask import Blueprint, request, jsonify
from routes.auth import token_required
from extensions import db
from models import Session, Attendance, Notulensi, SessionPIC, Pic
from serializers import serialize_session, serialize_attendance

bp = Blueprint("sessions", __name__)

ADMIN_ROLES = {"admin", "ketua", "pembina"}


def _require_admin():
    current_user = request.current_user
    if current_user.role not in ADMIN_ROLES:
        return jsonify({"success": False, "message": "Access denied"}), 403


@bp.route("/api/sessions")
@token_required
def list_sessions():
    session_type = request.args.get("type")
    q = Session.query
    if session_type:
        q = q.filter_by(session_type=session_type)
    sessions = q.order_by(Session.date.desc()).all()
    return jsonify({"success": True, "sessions": [serialize_session(s) for s in sessions]})


@bp.route("/api/sessions", methods=["POST"])
@token_required
def create_session():
    err = _require_admin()
    if err:
        return err

    data = request.get_json() or {}
    name = data.get("name", "").strip()
    date_val = data.get("date", "").strip()
    session_type = data.get("session_type", "all")
    description = data.get("description", "").strip() or None

    if not name or not date_val:
        return jsonify({"success": False, "message": "Name and date are required"}), 400
    if session_type not in ("all", "core", "event"):
        session_type = "all"

    s = Session(name=name, date=date_val, session_type=session_type, description=description)
    try:
        db.session.add(s)
        db.session.commit()
        return jsonify({"success": True, "message": "Session created", "session": serialize_session(s)}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@bp.route("/api/sessions/<int:session_id>", methods=["DELETE"])
@token_required
def delete_session(session_id):
    err = _require_admin()
    if err:
        return err

    s = Session.query.get_or_404(session_id)
    name = s.name
    try:
        SessionPIC.query.filter_by(session_id=session_id).delete()
        Attendance.query.filter_by(session_id=session_id).delete()
        Notulensi.query.filter_by(session_id=session_id).delete()
        db.session.delete(s)
        db.session.commit()
        return jsonify({"success": True, "message": f'Session "{name}" deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@bp.route("/api/sessions/<int:session_id>/lock", methods=["POST"])
@token_required
def lock_session(session_id):
    err = _require_admin()
    if err:
        return err

    s = Session.query.get_or_404(session_id)
    s.is_locked = True
    db.session.commit()
    return jsonify({"success": True, "is_locked": True, "session": serialize_session(s)})


@bp.route("/api/sessions/<int:session_id>/status")
@token_required
def get_session_status(session_id):
    s = Session.query.get_or_404(session_id)
    return jsonify({"success": True, "is_locked": s.is_locked, "session_id": s.id, "name": s.name})


@bp.route("/api/sessions/<int:session_id>/attendance")
@token_required
def get_session_attendance(session_id):
    Session.query.get_or_404(session_id)
    records = Attendance.query.filter_by(session_id=session_id).all()
    return jsonify({"success": True, "records": [serialize_attendance(r) for r in records]})


@bp.route("/api/sessions/<int:session_id>/pics", methods=["GET"])
@token_required
def get_session_pics(session_id):
    s = Session.query.get_or_404(session_id)
    return jsonify({
        "success": True,
        "session_id": session_id,
        "assigned_pics": [{"id": p.id, "name": p.name, "description": p.description} for p in s.assigned_pics],
    })


@bp.route("/api/sessions/<int:session_id>/pics", methods=["PUT"])
@token_required
def assign_pics_to_session(session_id):
    err = _require_admin()
    if err:
        return err

    s = Session.query.get_or_404(session_id)
    data = request.get_json() or {}
    pic_ids = data.get("pic_ids", [])

    try:
        SessionPIC.query.filter_by(session_id=session_id).delete()
        for pid in pic_ids:
            if Pic.query.get(pid):
                db.session.add(SessionPIC(session_id=session_id, pic_id=pid))
        db.session.commit()
        return jsonify({"success": True, "message": "PICs updated", "session": serialize_session(s)})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@bp.route("/api/sessions/<int:session_id>/pics/<int:pic_id>", methods=["DELETE"])
@token_required
def remove_pic_from_session(session_id, pic_id):
    err = _require_admin()
    if err:
        return err

    sp = SessionPIC.query.filter_by(session_id=session_id, pic_id=pic_id).first()
    if not sp:
        return jsonify({"success": False, "message": "PIC assignment not found"}), 404

    name = sp.pic.name
    db.session.delete(sp)
    db.session.commit()
    return jsonify({"success": True, "message": f"Removed {name} from session"})
