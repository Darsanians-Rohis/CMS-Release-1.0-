# ManageSpace

A open-source backend template for organization management systems — built to handle members, attendance, duty rosters, meeting notes, and an AI assistant out of the box. Designed to be cloned and adapted for any organization: student bodies, clubs, community groups, or workplaces.

> This codebase was originally built for a school Islamic organization (Rohis). The Rohis-specific content lives in well-documented spots so you can swap it out quickly. See [Adapting for Your Organization](#adapting-for-your-organization).

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Seeding the First Admin](#seeding-the-first-admin)
- [Environment Variables](#environment-variables)
- [Adapting for Your Organization](#adapting-for-your-organization)
- [Deployment](#deployment)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Database | PostgreSQL (SQLAlchemy + Flask-Migrate) |
| Auth | JWT (PyJWT) |
| AI Assistant | Groq API (Llama 3.1) |
| Email | Resend (preferred) or Mailjet (fallback) |
| Deployment | Render (backend) + Vercel (frontend) |

---

## Features

- **Member management** — add, remove, bulk import via CSV, assign roles and divisions
- **Session management** — create sessions by type, lock after attendance closes
- **Attendance tracking** — mark attendance per session, export to `.docx`
- **Duty roster** — weekly schedule with automated email reminders via cron
- **Meeting notes** — rich-text notes per session with AI-generated summaries
- **Calendar** — session events with optional holiday overlays
- **AI assistant** — answers organization questions and navigates between pages
- **Profile pictures** — stored as BLOBs directly in PostgreSQL

---

## Project Structure

```
├── app.py               # App factory, blueprint registration, error handlers
├── config.py            # Config class (reads from .env)
├── extensions.py        # Flask extensions (db, bcrypt, login_manager, etc.)
├── models.py            # SQLAlchemy models
├── serializers.py       # Dict serialization helpers for API responses
├── utils.py             # Permission helpers
├── ai.py                # Groq chatbot integration + in-app navigation
├── summarizer.py        # Groq-powered meeting notes summarizer
├── email_service.py     # Email via Resend or Mailjet
├── seed.py              # CLI script to create the first admin user
├── routes/
│   ├── auth.py          # Login, logout, JWT token_required decorator
│   ├── attendance.py    # Mark, view, export attendance
│   ├── members.py       # CRUD for members
│   ├── sessions.py      # CRUD for sessions + division assignment
│   ├── pics.py          # CRUD for divisions/committees
│   ├── notulensi.py     # Meeting notes CRUD
│   ├── calendar.py      # Calendar events + news feed
│   ├── piket.py         # Duty roster + email cron endpoint
│   ├── profile.py       # Password change + profile picture upload
│   └── chat.py          # AI assistant endpoint
└── migrations/          # Alembic migration files
```

---

## Getting Started

### 1. Clone and install

```bash
git clone <your-repo-url>
cd managespace-backend

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:password@host/dbname
FRONTEND_ORIGIN=http://localhost:8080

# Optional — enables AI assistant and meeting note summaries
GROQ_API_KEY=your-groq-api-key

# Optional — protects the cron email reminder endpoint
CRON_SECRET_TOKEN=your-cron-secret

# Optional — required only if you use duty roster email reminders
RESEND_API_KEY=your-resend-api-key        # preferred
# OR:
MAILJET_API_KEY=your-mailjet-key
MAILJET_API_SECRET=your-mailjet-secret
SENDER_EMAIL=noreply@yourorg.com
SENDER_NAME=Your Organization
```

### 3. Seed the database and create the first admin

```bash
python seed.py
```

This applies all pending migrations and walks you through creating the first admin account. See [Seeding the First Admin](#seeding-the-first-admin) for full details.

### 4. Run the server

```bash
flask run
# or for production:
gunicorn app:app
```

---

## Seeding the First Admin

There is no registration page — the first admin is created via `seed.py`. Once that admin exists, they can add all other members through the app's member management interface.

### Interactive mode

```bash
python seed.py
```

You'll be prompted for each field:

```
[OK] Database migrations applied.

=== ManageSpace — Create First Admin ===

  Full name: Jane Smith
  Email address: jane@yourorg.com
  Password (min 6 chars):
  Confirm password:

[SUCCESS] Admin created!
          Name  : Jane Smith
          Email : jane@yourorg.com
          Role  : admin

  Log in to the app and add your members from the dashboard.
```

### Non-interactive mode

Pass values as environment variables — useful for CI/CD pipelines, Docker entrypoints, or automated deploys:

```bash
SEED_NAME="Jane Smith" \
SEED_EMAIL="jane@yourorg.com" \
SEED_PASSWORD="yourpassword" \
python seed.py
```

### Notes

- The script runs `flask db upgrade` automatically, so you don't need a separate migration step on first setup.
- If an admin already exists, the script warns you and asks for confirmation before proceeding.
- After seeding, log in and go to **Members → Add Member** (or use the CSV batch import) to add the rest of your organization.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ | Flask session + JWT signing key |
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `FRONTEND_ORIGIN` | ✅ | Your frontend URL (for CORS) |
| `GROQ_API_KEY` | Optional | Enables AI assistant and meeting note summaries |
| `CRON_SECRET_TOKEN` | Optional | Protects `/api/cron/piket-reminder` |
| `RESEND_API_KEY` | Optional* | Email provider (preferred) |
| `MAILJET_API_KEY` | Optional* | Email provider (fallback) |
| `MAILJET_API_SECRET` | Optional* | Mailjet secret key |
| `SENDER_EMAIL` | Optional* | From address for reminder emails |
| `SENDER_NAME` | Optional* | Display name for reminder emails |

*Required only if you use duty roster email reminders.

---

## Adapting for Your Organization

ManageSpace was built with a specific organization in mind but is designed to be forked. Below is a precise guide to every file and line that carries organization-specific content.

---

### Branding and organization name

**`ai.py`** — the AI assistant's identity and knowledge

```python
# Lines 9–21: Change the assistant's persona and domain
SYSTEM_PROMPT = """
You are an Islamic educational assistant for a school Rohis organization.
# ↑ Replace with your org's name, purpose, and any rules for the assistant
"""

# Lines 14–18: Update navigation targets to match your frontend routes
ROUTE_MAP = {
    "dashboard": "/",
    "attendance": "/attendance",
    "members": "/member-list",
    "login": "/login",
}
```

**`email_service.py`** — duty reminder emails

```python
# Line 57: Change the email subject
subject = f"Reminder: Jadwal Piket {day_name}"
# ↑ e.g. f"Duty Reminder: {day_name}"

# Lines 95–170: _generate_email_html()
# Update three things in the HTML template:
#   1. "Rohis Attendance System" in the header → your org name
#   2. The <ul> responsibilities list → your org's duty checklist
#   3. "GDA Jogja" in the footer → your org's name/location

# Lines 172–200: _generate_email_text()
# Same changes for the plain-text fallback
```

---

### Roles and permissions

The system ships with four roles: `admin`, `ketua`, `pembina`, `member`. Change them everywhere they appear:

**`utils.py`**

```python
# Line 2: who can mark attendance for any session
def can_mark_attendance(user, target_pic_id):
    if user.role in ['admin', 'pembina']:  # ← your admin-level roles
        ...

# Line 9: who counts as a leadership/core user
def is_core_user(user):
    return user.role in ["admin", "ketua"]  # ← your leadership roles
```

**All route files** — each defines the same constant; update all six:

```python
# routes/attendance.py  line 16
# routes/members.py     line 11
# routes/notulensi.py   line 11
# routes/pics.py        line 11
# routes/piket.py       line 13
# routes/sessions.py    line 11
ADMIN_ROLES = {"admin", "ketua", "pembina"}  # ← update to match your roles
```

---

### Session types

Sessions have three types: `all`, `core`, `event`. Rename or extend them:

```python
# models.py — line 36: default type
session_type = db.Column(db.String(50), default='all', nullable=False)

# routes/sessions.py — line 23: allowed values
if session_type not in ("all", "core", "event"):  # ← update this list
    session_type = "all"
```

---

### Duty roster day names

The roster uses Python's `weekday()` convention (0 = Monday, 6 = Sunday). Translate or filter days:

```python
# routes/piket.py — line 17
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
# ↑ Translate to your language, or remove days your org doesn't use
```

---

### Calendar holiday overlay

The calendar currently overlays Islamic holidays using Hijri date conversion. To replace or remove it:

```python
# routes/calendar.py — lines 16–44
ISLAMIC_HOLIDAYS = { ... }
# ↑ Replace with your own holiday dict, or delete entirely

# routes/calendar.py — lines 82–99 (inside calendar_events())
# Remove or replace the while loop that generates holiday events
```

To remove the Hijri dependency entirely, delete `ummalqura` from `requirements.txt`.

---

### Meeting notes summarizer persona

```python
# summarizer.py — line 9
"""You are a meeting minutes summarizer for a school Islamic organization (Rohis)."""
# ↑ Change to match your organization type
```

---

### Default password for new members

When an admin adds a member through the app, they're given a default password:

```python
# routes/members.py — lines 35 and 56
hashed = bcrypt.generate_password_hash("rohisnew").decode("utf-8")
#                                        ↑ change to something relevant to your org
```

---

### Deployment URLs

```yaml
# render.yaml — line 10
- key: FRONTEND_ORIGIN
  value: https://managespace-rohis.vercel.app  # ← your frontend URL
```

```python
# config.py — line 19
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:8080")
```

---

## Deployment

This project is configured for **Render** (backend) and works with any static frontend host such as Vercel.

```bash
# Render runs:
gunicorn app:app
```

To enable automated duty reminder emails, configure a cron job (Render Cron Jobs, cron-job.org, or similar) to hit:

```
POST /api/cron/piket-reminder
Header: X-Cron-Secret: <your CRON_SECRET_TOKEN>
```

A typical schedule for weekday morning reminders: `0 5 * * 1-5` (5 AM UTC, Monday–Friday).

---

## License

MIT © 2026 Dadarzz 