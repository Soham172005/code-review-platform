# CodeReview Platform

A full-stack code review platform that replicates core GitHub workflows — repositories, pull requests, inline diff comments, AI-powered reviews, and real-time notifications.

## Features

- **JWT Authentication** with registration, login, logout, and GitHub OAuth2
- **Role-Based Access Control** — admin, reviewer, and author roles with permission enforcement
- **Repository & PR Management** — full CRUD with FSM-powered state machine (draft → open → in_review → approved → merged/closed)
- **Inline Diff Viewer** — GitHub-style unified diffs with syntax highlighting via Prism.js
- **Threaded Review Comments** — nested replies, resolution tracking, and auto-created pending reviews
- **AI Code Reviewer** — Claude-powered bot that automatically reviews PRs on open, posting inline comments with severity levels
- **GitHub Webhooks** — HMAC-verified ingestion of push, PR, and review events
- **Real-Time Notifications** — Server-Sent Events with unread badges, grouped history, and mark-all-read
- **Async Task Processing** — Celery workers for webhook processing, notifications, and AI reviews
- **Structured Logging** — structlog with JSON output in production, colored console in dev
- **Error Tracking** — Sentry integration with configurable sample rates
- **Docker Ready** — Multi-stage builds, production Compose with health checks, nginx reverse proxy

## Architecture

```
                        ┌─────────────┐
                        │   Browser   │
                        └──────┬──────┘
                               │
                        ┌──────▼──────┐
                        │    nginx    │
                        │  (React)    │
                        └──────┬──────┘
                               │ /api/*
                        ┌──────▼──────┐        ┌───────────┐
                        │   Django /  │◄──────►│ PostgreSQL│
                        │  Gunicorn   │        └───────────┘
                        └──┬───┬──────┘
                           │   │
              ┌────────────┘   └──────────┐
              ▼                           ▼
       ┌─────────────┐           ┌────────────────┐
       │    Redis     │◄─────────│ Celery Worker   │
       │  (Broker)    │           │ • AI Reviews    │
       └─────────────┘           │ • Notifications  │
                                 │ • Webhooks       │
   ┌──────────┐                  └────────────────┘
   │  GitHub   │─── Webhooks ──►  Django
   └──────────┘
```

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend | Django 4.2 + DRF | Battle-tested, excellent ORM, rapid API development |
| Auth | simplejwt + social-auth | Stateless JWT with GitHub OAuth2 support |
| State Machine | django-fsm | PR transitions enforced at model layer, not view layer |
| Async | Celery + Redis | Decoupled task processing, eager mode for dev |
| AI Reviewer | Anthropic Claude API | Structured JSON output for reliable comment parsing |
| Database | PostgreSQL (prod) / SQLite (dev) | Zero-config dev, production-grade in prod |
| Frontend | React 18 + Vite + Tailwind | Fast builds, utility-first CSS, dark mode |
| Server State | TanStack React Query v5 | Automatic caching, background refetching |
| Notifications | SSE + react-hot-toast | Lightweight real-time without WebSocket complexity |
| Observability | Sentry + structlog | Error tracking + structured JSON logging |
| CI/CD | GitHub Actions + GHCR | Automated testing, Docker image publishing |

## Key Engineering Decisions

**JSONB for diff storage.** Diffs are stored as structured JSON in a `JSONField` rather than raw text. This lets the frontend render hunks, line numbers, and change types without re-parsing. The `GitDiffParser` converts unified diff text into a normalized structure at ingestion time, making the API response self-contained.

**FSM at model layer, not view layer.** PR state transitions use `django-fsm` on the `PullRequest` model. Invalid transitions raise `TransitionNotAllowed` before reaching the database, and transition history is recorded automatically. This means the business rules are testable without HTTP and can't be bypassed by a new view or management command.

**SSE over WebSockets for notifications.** Server-Sent Events are unidirectional (server → client), which is exactly the notification use case. They work over standard HTTP, need no special proxy configuration beyond disabling buffering, and reconnect automatically. WebSockets would add bidirectional complexity we don't need.

**AI reviewer posts as a bot user.** The Claude-powered reviewer creates a `Review` and `ReviewComment` objects under a dedicated `ai-reviewer` user account. This means AI comments appear in the same comment threads as human reviews, use the same resolution workflow, and are fully auditable through the existing review API.

## Quick Start

### Local Development (no Docker needed)

```bash
# Clone and install
git clone <repo-url> && cd code-review-platform
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env — defaults work for SQLite dev mode

# Migrate and run
python manage.py migrate
python manage.py runserver

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

Frontend: http://localhost:5173 | Backend: http://localhost:8000 | Admin: http://localhost:8000/admin/

### Production (Docker)

```bash
# Start everything
docker compose -f docker-compose.prod.yml up -d --build

# Run migrations
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
```

App: http://localhost (nginx serves frontend + proxies API)

### Infrastructure Only (PostgreSQL + Redis)

```bash
docker compose up -d
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/token/` | Obtain JWT access + refresh tokens |
| POST | `/api/token/refresh/` | Refresh access token |
| POST | `/api/users/register/` | Create account |
| GET/PATCH | `/api/users/me/` | Current user profile |
| POST | `/api/users/logout/` | Blacklist refresh token |
| POST | `/api/users/auth/github/` | GitHub OAuth → JWT |
| GET/POST | `/api/repos/` | List / create repositories |
| GET | `/api/repos/{id}/` | Repository detail |
| GET/POST | `/api/repos/{id}/prs/` | List / create PRs for a repo |
| GET | `/api/prs/{id}/` | PR detail |
| GET | `/api/prs/{id}/diff/` | Commits + diff files |
| POST | `/api/prs/{id}/comments/` | Add inline comment |
| POST | `/api/prs/{id}/reviews/` | Submit review |
| POST | `/api/prs/{id}/transition/` | State transition |
| GET | `/api/prs/{id}/history/` | Transition history |
| POST | `/api/reviews/comments/{id}/resolve/` | Toggle comment resolved |
| GET | `/api/notifications/` | Notification list |
| PATCH | `/api/notifications/{id}/read/` | Mark notification read |
| POST | `/api/notifications/mark-all-read/` | Mark all read |
| GET | `/api/notifications/stream/` | SSE notification stream |
| POST | `/api/webhooks/github/` | GitHub webhook receiver |

## Running Tests

```bash
# Backend (91 tests)
pytest

# Frontend (20 tests)
cd frontend && npm test
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | — | Django secret key |
| `DB_ENGINE` | `postgresql` | `sqlite3` for local dev |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker + result backend |
| `ANTHROPIC_API_KEY` | — | Enables AI code reviews |
| `SENTRY_DSN` | — | Enables error tracking |
| `GITHUB_WEBHOOK_SECRET` | `dev-secret` | HMAC verification for webhooks |
| `GITHUB_OAUTH_CLIENT_ID` | — | GitHub OAuth app |
| `GITHUB_OAUTH_CLIENT_SECRET` | — | GitHub OAuth app |

## License

MIT
