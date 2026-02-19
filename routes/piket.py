import os
import json
import logging
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from routes.auth import token_required
from extensions import db
from models import JadwalPiket, PiketAssignment, EmailReminderLog
from email_service import get_email_service

bp = Blueprint("piket", __name__)
logger = logging.getLogger(__name__)

WIB = timezone(timedelta(hours=7))
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
ADMIN_ROLES = {"admin", "ketua", "pembina"}


def _require_admin():
    current_user = request.current_user
    if current_user.role not in ADMIN_ROLES:
        return jsonify({"success": False, "message": "Access denied"}), 403


@bp.route("/api/piket")
@token_required
def view_piket():
    current_user = request.current_user
    today_idx = datetime.now(WIB).weekday()
    schedule = []
    for idx, name in enumerate(DAY_NAMES):
        jadwal = JadwalPiket.query.filter_by(day_of_week=idx).first()
        assignments = []
        if jadwal:
            assignments = [
                {
                    "user_id": a.user.id,
                    "name": a.user.name,
                    "class_name": a.user.class_name,
                    "email": a.user.email,
                    "is_current_user": a.user.id == current_user.id,
                }
                for a in jadwal.assignments
            ]
        schedule.append({
            "day_of_week": idx,
            "day_name": name,
            "is_today": idx == today_idx,
            "assignments": assignments,
            "updated_at": jadwal.updated_at.isoformat() if jadwal and jadwal.updated_at else None,
        })
    return jsonify({"success": True, "schedule": schedule})


@bp.route("/api/piket", methods=["POST"])
@token_required
def update_piket():
    err = _require_admin()
    if err:
        return err

    data = request.get_json() or {}
    day_of_week = data.get("day_of_week")
    user_ids = data.get("user_ids", [])

    if day_of_week is None or not (0 <= int(day_of_week) <= 6):
        return jsonify({"success": False, "message": "Invalid day_of_week (0–6)"}), 400

    day_of_week = int(day_of_week)
    try:
        jadwal = JadwalPiket.query.filter_by(day_of_week=day_of_week).first()
        if not jadwal:
            jadwal = JadwalPiket(day_of_week=day_of_week, day_name=DAY_NAMES[day_of_week])
            db.session.add(jadwal)
            db.session.flush()

        PiketAssignment.query.filter_by(jadwal_id=jadwal.id).delete()
        for uid in user_ids:
            if uid:
                db.session.add(PiketAssignment(jadwal_id=jadwal.id, user_id=int(uid)))

        jadwal.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"success": True, "message": f"Piket for {DAY_NAMES[day_of_week]} updated"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@bp.route("/api/piket/<int:day_of_week>", methods=["DELETE"])
@token_required
def clear_piket(day_of_week):
    err = _require_admin()
    if err:
        return err

    jadwal = JadwalPiket.query.filter_by(day_of_week=day_of_week).first()
    if not jadwal:
        return jsonify({"success": False, "message": "No schedule found for that day"}), 404

    PiketAssignment.query.filter_by(jadwal_id=jadwal.id).delete()
    db.session.commit()
    return jsonify({"success": True, "message": "Assignments cleared"})


@bp.route("/api/piket/logs")
@token_required
def piket_logs():
    err = _require_admin()
    if err:
        return err

    logs = EmailReminderLog.query.order_by(EmailReminderLog.sent_at.desc()).limit(100).all()
    result = [
        {
            "id": log.id,
            "day_of_week": log.day_of_week,
            "day_name": log.day_name,
            "recipients_count": log.recipients_count,
            "recipients": json.loads(log.recipients) if log.recipients else [],
            "sent_at": log.sent_at.isoformat() if log.sent_at else None,
            "status": log.status,
            "error_message": log.error_message,
        }
        for log in logs
    ]
    return jsonify({"success": True, "logs": result})


@bp.route("/api/piket/test", methods=["POST"])
@token_required
def test_piket_reminder():
    current_user = request.current_user
    if current_user.role != "admin":
        return jsonify({"success": False, "message": "Admin only"}), 403

    data = request.get_json() or {}
    day_of_week = int(data.get("day_of_week", datetime.now(WIB).weekday()))
    day_name = DAY_NAMES[day_of_week]

    jadwal = JadwalPiket.query.filter_by(day_of_week=day_of_week).first()
    if not jadwal or not jadwal.assignments:
        return jsonify({"success": False, "message": f"No assignments for {day_name}"}), 404

    recipients = [a.user.email for a in jadwal.assignments if a.user and a.user.email]
    if not recipients:
        return jsonify({"success": False, "message": "No valid email addresses found"}), 404

    result = get_email_service().send_piket_reminder(
        recipients=recipients,
        day_name=day_name,
        date_str=datetime.now().strftime("%d %B %Y"),
        additional_info="⚠️ This is a TEST reminder from the admin panel.",
    )
    return jsonify({
        "success": result["success"],
        "message": result["message"],
        "failed_emails": result.get("failed_emails", []),
    })


# ---------------------------------------------------------------------------
# Cron endpoint (no login required — protected by secret token)
# ---------------------------------------------------------------------------

@bp.route("/api/cron/piket-reminder", methods=["POST"])
def cron_piket_reminder():
    expected = os.environ.get("CRON_SECRET_TOKEN")
    if not expected:
        return jsonify({"success": False, "error": "Service not configured"}), 503

    provided = request.headers.get("X-Cron-Secret") or (request.get_json() or {}).get("secret")
    if not provided or provided != expected:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        now_wib = datetime.now(WIB)
        day_of_week = now_wib.weekday()
        day_name = DAY_NAMES[day_of_week]
        date_str = now_wib.strftime("%d %B %Y")

        def _log(status, error=None, count=0, recipients="[]"):
            log = EmailReminderLog(
                day_of_week=day_of_week, day_name=day_name,
                recipients_count=count, recipients=recipients,
                status=status, error_message=error,
            )
            db.session.add(log)
            db.session.commit()

        jadwal = JadwalPiket.query.filter_by(day_of_week=day_of_week).first()
        if not jadwal:
            _log("skipped", "No jadwal piket configured for this day")
            return jsonify({"success": True, "message": f"No piket for {day_name}", "recipients_count": 0})

        assignments = PiketAssignment.query.filter_by(jadwal_id=jadwal.id).all()
        if not assignments:
            _log("skipped", "No members assigned")
            return jsonify({"success": True, "message": f"No members for {day_name}", "recipients_count": 0})

        recipients = [a.user.email for a in assignments if a.user and a.user.email]
        if not recipients:
            _log("failed", "No valid emails")
            return jsonify({"success": False, "error": "No valid emails"}), 500

        result = get_email_service().send_piket_reminder(
            recipients=recipients, day_name=day_name, date_str=date_str
        )
        _log(
            "success" if result["success"] else "partial",
            result.get("message") if not result["success"] else None,
            len(recipients),
            json.dumps(recipients),
        )
        return jsonify({
            "success": True,
            "message": result["message"],
            "day": day_name,
            "date": date_str,
            "recipients_count": len(recipients),
            "failed_emails": result.get("failed_emails", []),
        })

    except Exception as e:
        logger.exception("Cron reminder error")
        return jsonify({"success": False, "error": str(e)}), 500
