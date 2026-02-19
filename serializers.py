from datetime import timezone, timedelta

WIB = timezone(timedelta(hours=7))


def serialize_user(user, include_email=True):
    data = {
        "id": user.id,
        "name": user.name,
        "role": user.role,
        "class_name": user.class_name,
        "can_mark_attendance": user.can_mark_attendance,
        "must_change_password": user.must_change_password,
        "pic_id": user.pic_id,
        "pic_name": user.pic.name if user.pic else None,
        "profile_picture_url": f"/api/profile/picture/{user.id}",
    }
    if include_email:
        data["email"] = user.email
    return data


def serialize_session(s):
    return {
        "id": s.id,
        "name": s.name,
        "date": s.date,
        "is_locked": s.is_locked,
        "session_type": s.session_type,
        "description": s.description,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "assigned_pics": [{"id": p.id, "name": p.name} for p in s.assigned_pics],
        "attendance_count": len(s.attendances),
    }


def serialize_pic(pic):
    return {
        "id": pic.id,
        "name": pic.name,
        "description": pic.description,
        "created_at": pic.created_at.isoformat() if pic.created_at else None,
        "member_count": len(pic.members),
        "members": [{"id": m.id, "name": m.name} for m in pic.members],
    }


def serialize_attendance(att):
    return {
        "id": att.id,
        "session_id": att.session_id,
        "session_name": att.session.name if att.session else None,
        "session_date": att.session.date if att.session else None,
        "user_id": att.user_id,
        "status": att.status,
        "attendance_type": att.attendance_type,
        "timestamp": att.timestamp.astimezone(WIB).isoformat() if att.timestamp else None,
    }


def serialize_notulensi(note):
    return {
        "id": note.id,
        "session_id": note.session_id,
        "session_name": note.session.name if note.session else None,
        "session_date": note.session.date if note.session else None,
        "content": note.content,
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
    }
