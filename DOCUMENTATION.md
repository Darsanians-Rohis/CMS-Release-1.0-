# ManageSpace Backend — Documentation

**Author:** Haidar Ali Fawwaz Nasirodin  
**Organization:** Global Darussalam Academy  
**Built for:** Rohis GDA (adaptable for any organization)  
**License:** MIT © 2026 Dadarzz  

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Tech Stack](#tech-stack)
3. [System Architecture](#system-architecture)
4. [Database Models](#database-models)
5. [API Reference](#api-reference)
6. [Authentication](#authentication)
7. [AI Assistant](#ai-assistant)
8. [Email Service](#email-service)
9. [Environment Variables](#environment-variables)
10. [Getting Started](#getting-started)
11. [Deployment](#deployment)
12. [Adapting for Your Organization](#adapting-for-your-organization)

---

## Project Overview

ManageSpace is an open-source backend for organization management systems. It was originally developed as a Passion Project at Global Darussalam Academy to replace the manual, fragmented administrative processes of the Rohis student organization — attendance tracked via messaging apps, meeting notes in scattered documents, and duty rosters managed informally.

The backend handles members, sessions, attendance, duty rosters, meeting notes, an AI assistant, automated email reminders, and calendar events. It is designed to be cloned and adapted for any organization: student bodies, clubs, community groups, or workplaces.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python |
| Framework | Flask |
| Database | PostgreSQL |
| ORM | SQLAlchemy + Flask-Migrate (Alembic) |
| Authentication | JWT (PyJWT) |
| Password Hashing | Flask-Bcrypt |
| AI Assistant | Groq API (Llama 3.1) |
| Email | Resend (preferred) / Mailjet (fallback) |
| Deployment | Render |

---

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                  React Frontend (Vercel)             │
└───────────────────────┬─────────────────────────────┘
                        │ HTTPS / REST API
┌───────────────────────▼─────────────────────────────┐
│               Flask Backend (Render)                 │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  Routes  │  │   Auth   │  │   AI Assistant   │  │
│  │(Blueprints) │  │  (JWT)   │  │  (Groq API)     │  │
│  └────┬─────┘  └──────────┘  └──────────────────┘  │
│       │                                              │
│  ┌────▼─────────────────────────────────────────┐   │
│  │            SQLAlchemy ORM                    │   │
│  └────┬─────────────────────────────────────────┘   │
└───────┼─────────────────────────────────────────────┘
        │
┌───────▼──────────────┐   ┌──────────────────────────┐
│  PostgreSQL Database  │   │  External Services       │
│  (Render Postgres)   │   │  - Groq API (LLM)        │
└──────────────────────┘   │  - Resend (Email)        │
                           └──────────────────────────┘
```

The backend follows a **modular blueprint architecture**, where each feature domain (members, sessions, attendance, etc.) lives in its own route file registered as a Flask blueprint. This separation makes the codebase maintainable and easy to extend.

---

## Database Models

### User
| Field | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| name | String | Full name |
| email | String | Unique |
| password | String | Bcrypt hashed |
| role | String | `admin`, `ketua`, `pembina`, `member` |
| profile_picture | LargeBinary | Stored as BLOB in DB |
| force_password_change | Boolean | True on first login |

### Session
| Field | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| title | String | Session name |
| date | Date | Session date |
| session_type | String | `all`, `core`, `event` |
| is_locked | Boolean | Locks attendance after closing |
| pic_id | Integer | FK → PIC |

### Attendance
| Field | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| user_id | Integer | FK → User |
| session_id | Integer | FK → Session |
| status | String | `present`, `absent`, `excused` |

### PIC (Division/Committee)
| Field | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| name | String | Division name |

### Notulensi (Meeting Notes)
| Field | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| session_id | Integer | FK → Session |
| content | Text | Rich text (HTML) |
| summary | Text | AI-generated summary |

### Piket (Duty Roster)
| Field | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| user_id | Integer | FK → User |
| day_of_week | Integer | 0 = Monday, 6 = Sunday |

---

## API Reference

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/login` | Login, returns JWT |
| GET | `/api/auth/me` | Returns current user info |
| POST | `/api/auth/logout` | Invalidates session |

### Members
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/members` | List all members |
| POST | `/api/members` | Add a single member |
| POST | `/api/members/batch` | Batch import via CSV |
| PUT | `/api/members/<id>` | Update member |
| DELETE | `/api/members/<id>` | Remove member |

### Sessions
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/sessions` | List all sessions |
| POST | `/api/sessions` | Create session |
| PUT | `/api/sessions/<id>` | Update session |
| DELETE | `/api/sessions/<id>` | Delete session |
| POST | `/api/sessions/<id>/lock` | Lock session |

### Attendance
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/attendance/<session_id>` | Get attendance for session |
| POST | `/api/attendance/<session_id>` | Mark attendance |
| GET | `/api/attendance/history/<user_id>` | Per-member history |
| GET | `/api/attendance/<session_id>/export` | Export to `.docx` |

### Notulensi (Meeting Notes)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/notulensi` | List all notes |
| GET | `/api/notulensi/<id>` | Get single note |
| POST | `/api/notulensi` | Create note |
| PUT | `/api/notulensi/<id>` | Update note |
| DELETE | `/api/notulensi/<id>` | Delete note |
| POST | `/api/notulensi/<id>/summarize` | AI-generate summary |

### PICs / Divisions
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/pics` | List all divisions |
| POST | `/api/pics` | Create division |
| DELETE | `/api/pics/<id>` | Delete division |

### Piket (Duty Roster)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/piket` | Get weekly roster |
| PUT | `/api/piket` | Update assignments |
| POST | `/api/cron/piket-reminder` | Trigger email reminders (cron) |

### Calendar
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/calendar` | Get session + holiday events |
| GET | `/api/feed` | Activity feed |

### Profile
| Method | Endpoint | Description |
|---|---|---|
| PUT | `/api/profile/password` | Change password |
| POST | `/api/profile/picture` | Upload profile picture |
| GET | `/api/profile/picture/<id>` | Retrieve profile picture |

### AI Chat
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/chat` | Send message, receive reply + optional navigate action |

---

## Authentication

All protected endpoints require a JWT passed in the `Authorization` header:

```
Authorization: Bearer <token>
```

Tokens are issued on `/api/auth/login` and verified via the `@token_required` decorator applied to each protected route. First-login users have `force_password_change: true` returned in the `/api/auth/me` response, which the frontend uses to redirect them to the password change page before accessing the app.

**Role hierarchy:**
- `admin` — full access
- `ketua` — leadership access (same as admin in most contexts)
- `pembina` — can mark attendance for any session
- `member` — standard access, restricted controls

---

## AI Assistant

The AI assistant is powered by the **Groq API (Llama 3.1)** and handles two types of responses:

1. **Conversational answers** — answering questions about the organization, system navigation, or general queries
2. **Navigation actions** — returning a `navigate` key in the response that instructs the frontend to redirect to a specific page

```python
# Example response structure from /api/chat
{
  "reply": "Sure! Here's how to mark attendance...",
  "navigate": "/attendance"   # optional
}
```

The assistant's persona and knowledge domain are defined in `ai.py` via a system prompt. The route map that controls navigation targets is also defined there and should be updated to match your frontend routes.

The meeting notes summarizer (`summarizer.py`) uses the same Groq API but with a separate prompt focused on generating concise meeting minutes summaries from rich-text content.

---

## Email Service

Automated duty roster (piket) reminders are sent via **Resend** (preferred) or **Mailjet** (fallback). The system detects which provider is configured based on environment variables.

The cron endpoint `/api/cron/piket-reminder` is protected by a secret token header (`X-Cron-Secret`) and is intended to be called by an external cron job scheduler (e.g. Render Cron Jobs, cron-job.org).

**Recommended cron schedule:** `0 5 * * 1-5` (5:00 AM UTC, Monday–Friday)

Both an HTML email template and a plain-text fallback are generated for each reminder.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ | Flask session + JWT signing key |
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `FRONTEND_ORIGIN` | ✅ | Frontend URL (for CORS) |
| `GROQ_API_KEY` | Optional | Enables AI assistant and summarizer |
| `CRON_SECRET_TOKEN` | Optional | Protects cron reminder endpoint |
| `RESEND_API_KEY` | Optional* | Email provider (preferred) |
| `MAILJET_API_KEY` | Optional* | Email provider (fallback) |
| `MAILJET_API_SECRET` | Optional* | Mailjet secret |
| `SENDER_EMAIL` | Optional* | From address for reminder emails |
| `SENDER_NAME` | Optional* | Display name for reminder emails |

*Required only if using duty roster email reminders.

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

### 2. Configure environment

```env
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:password@host/dbname
FRONTEND_ORIGIN=http://localhost:8080
GROQ_API_KEY=your-groq-api-key
```

### 3. Seed the database and create first admin

```bash
python seed.py
```

### 4. Run the server

```bash
flask run
```

---

## Deployment

Configured for **Render** (backend). Steps:

1. Push to GitHub and create a new Web Service on Render
2. Set all required environment variables in Render's dashboard
3. Render will run `gunicorn app:app` automatically
4. Set up a Cron Job on Render pointing to `/api/cron/piket-reminder` if email reminders are needed

---

## Adapting for Your Organization

Key files to update when forking for a different organization:

| File | What to change |
|---|---|
| `ai.py` | Assistant persona, system prompt, navigation route map |
| `email_service.py` | Email subject, HTML template, org name in footer |
| `utils.py` | Role definitions for permissions |
| `routes/*.py` | `ADMIN_ROLES` constant in all six route files |
| `models.py` | Default session type |
| `routes/sessions.py` | Allowed session type values |
| `routes/piket.py` | Day names (translate or filter) |
| `routes/calendar.py` | Holiday overlay (replace or remove Islamic holidays) |
| `summarizer.py` | Summarizer persona |
| `routes/members.py` | Default password for new members |
