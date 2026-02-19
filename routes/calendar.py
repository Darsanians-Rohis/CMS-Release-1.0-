import os
import logging
from datetime import datetime, date
from flask import Blueprint, jsonify
from flask_login import login_required
from ummalqura.hijri_date import HijriDate
from models import Session, Notulensi, Pic, SessionPIC
from extensions import db
from summarizer import summarize_notulensi

bp = Blueprint("calendar", __name__)
logger = logging.getLogger(__name__)

ISLAMIC_HOLIDAYS = {
    "01-01": "Islamic New Year",
    "01-09": "Day of Tasua",
    "01-10": "Day of Ashura",
    "03-12": "Mawlid al-Nabi",
    "07-01": "Start of Rajab",
    "07-27": "Isra and Mi'raj",
    "08-15": "Mid-Sha'ban (Laylat al-Bara'ah)",
    "09-01": "Start of Ramadan",
    "09-17": "Nuzul al-Qur'an",
    "09-21": "Laylat al-Qadr (possible)",
    "09-23": "Laylat al-Qadr (possible)",
    "09-25": "Laylat al-Qadr (possible)",
    "09-27": "Laylat al-Qadr (possible)",
    "09-29": "Laylat al-Qadr (possible)",
    "10-01": "Eid al-Fitr",
    "10-02": "Eid al-Fitr (Day 2)",
    "11-01": "Start of Dhu al-Qi'dah",
    "12-01": "Start of Dhu al-Hijjah",
    "12-08": "Day of Tarwiyah",
    "12-09": "Day of Arafah",
    "12-10": "Eid al-Adha",
    "12-11": "Days of Tashreeq",
    "12-12": "Days of Tashreeq",
    "12-13": "Days of Tashreeq",
}


def _get_hijri_date(gregorian_date_str):
    try:
        g = datetime.strptime(gregorian_date_str, "%Y-%m-%d").date()
        h = HijriDate(g.year, g.month, g.day, gr=True)
        return f"{h.day} {h.month_name} {h.year} H"
    except Exception:
        return ""


def _get_hijri_key(g_date):
    h = HijriDate(g_date.year, g_date.month, g_date.day, gr=True)
    return f"{h.month:02d}-{h.day:02d}", h


def _plain_preview(html_content, max_len=150):
    import re
    from html import unescape
    text = unescape(re.sub("<[^<]+?>", "", html_content)).strip()
    return (text[:max_len] + "...") if len(text) > max_len else (text or "Meeting notes available.")


@bp.route("/api/calendar")
@login_required
def calendar_events():
    events = []
    for s in Session.query.all():
        hijri = _get_hijri_date(s.date)
        events.append({
            "title": f"{s.name} ({hijri})",
            "start": s.date,
            "extendedProps": {"type": "rohis_session", "session_id": s.id},
        })

    today = date.today()
    current = date(today.year - 1, 1, 1)
    end = date(today.year + 1, 12, 31)
    while current <= end:
        key, h = _get_hijri_key(current)
        if key in ISLAMIC_HOLIDAYS:
            events.append({
                "title": f"{ISLAMIC_HOLIDAYS[key]} ({h.day} {h.month_name} {h.year} H)",
                "start": current.isoformat(),
                "allDay": True,
                "backgroundColor": "#1e88e5",
                "borderColor": "#1565c0",
                "textColor": "#ffffff",
                "extendedProps": {
                    "type": "islamic_holiday",
                    "hijri": f"{h.day} {h.month_name} {h.year} H",
                },
            })
        current = current.fromordinal(current.toordinal() + 1)

    return jsonify(events)


@bp.route("/api/feed")
@login_required
def news_feed():
    try:
        today_str = str(date.today())
        upcoming = Session.query.filter(Session.date >= today_str).order_by(Session.date.asc()).limit(3).all()
        recent = (
            db.session.query(Notulensi, Session)
            .join(Session, Notulensi.session_id == Session.id)
            .order_by(Notulensi.updated_at.desc())
            .limit(3)
            .all()
        )

        upcoming_data = []
        for s in upcoming:
            pics = Pic.query.join(SessionPIC, Pic.id == SessionPIC.pic_id).filter(SessionPIC.session_id == s.id).all()
            upcoming_data.append({
                "id": s.id,
                "name": s.name,
                "date": s.date,
                "pic": ", ".join(p.name for p in pics) if pics else "No PIC assigned",
            })

        recent_data = []
        for note, s in recent:
            summary = "Meeting notes available."
            if note.content:
                try:
                    summary = (
                        summarize_notulensi(note.content)
                        if os.environ.get("GROQ_API_KEY")
                        else _plain_preview(note.content)
                    )
                except Exception:
                    summary = _plain_preview(note.content)
            recent_data.append({
                "id": s.id,
                "session_name": s.name,
                "session_date": s.date,
                "summary": summary,
                "updated_at": (note.updated_at or note.created_at).strftime("%d %b %Y"),
            })

        return jsonify({"success": True, "upcoming": upcoming_data, "recent": recent_data})
    except Exception as e:
        logger.exception("News feed error")
        return jsonify({"success": True, "upcoming": [], "recent": [], "error": str(e)})
