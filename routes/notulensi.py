from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Session, Notulensi
from serializers import serialize_session, serialize_notulensi

bp = Blueprint("notulensi", __name__)

ADMIN_ROLES = {"admin", "ketua", "pembina"}


def _require_admin():
    if current_user.role not in ADMIN_ROLES:
        return jsonify({"success": False, "message": "Access denied"}), 403


@bp.route("/api/notulensi")
@login_required
def list_notulensi():
    sessions = Session.query.order_by(Session.date.desc()).all()
    notes = {n.session_id: n for n in Notulensi.query.all()}
    result = [
        {
            "session_id": s.id,
            "session_name": s.name,
            "session_date": s.date,
            "has_notulensi": s.id in notes,
            "notulensi": serialize_notulensi(notes[s.id]) if s.id in notes else None,
        }
        for s in sessions
    ]
    return jsonify({"success": True, "items": result})


@bp.route("/api/notulensi/<int:session_id>", methods=["GET"])
@login_required
def get_notulensi(session_id):
    s = Session.query.get_or_404(session_id)
    note = Notulensi.query.filter_by(session_id=session_id).first()
    return jsonify({
        "success": True,
        "session": serialize_session(s),
        "notulensi": serialize_notulensi(note) if note else None,
        "can_edit": current_user.role in ADMIN_ROLES,
    })


@bp.route("/api/notulensi/<int:session_id>", methods=["POST"])
@login_required
def save_notulensi(session_id):
    err = _require_admin()
    if err:
        return err

    data = request.get_json() or {}
    content = data.get("content", "").strip()
    if not content or content in ["<p><br></p>", "<p></p>"]:
        return jsonify({"success": False, "message": "Content cannot be empty"}), 400

    note = Notulensi.query.filter_by(session_id=session_id).first()
    if note:
        note.content = content
        note.updated_at = datetime.utcnow()
    else:
        note = Notulensi(session_id=session_id, content=content)
        db.session.add(note)

    db.session.commit()
    return jsonify({"success": True, "notulensi": serialize_notulensi(note)})


@bp.route("/api/notulensi/by-id/<int:notulensi_id>", methods=["DELETE"])
@login_required
def delete_notulensi(notulensi_id):
    err = _require_admin()
    if err:
        return err

    note = Notulensi.query.get_or_404(notulensi_id)
    db.session.delete(note)
    db.session.commit()
    return jsonify({"success": True, "message": "Notulensi deleted"})
