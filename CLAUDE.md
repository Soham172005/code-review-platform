# Code Review Platform — Project Brief

This is a Django 4.2 REST API that replicates core GitHub code-review workflows: repositories, pull requests, commit diffs, inline review comments, and notifications.

---

## Phase 1 — Completed (Session 1)

Everything below was scaffolded and verified in the first session. Phase 2 begins from here.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Web framework | Django 4.2 |
| REST API | Django REST Framework (DRF) |
| Auth | djangorestframework-simplejwt (JWT) |
| State machine | django-fsm (wired, not yet used) |
| Async tasks | Celery + Redis |
| Database | PostgreSQL (prod) / SQLite (local dev) |
| Git parsing | GitPython + custom parser |
| Testing | pytest + pytest-django + factory_boy |
| Config | python-decouple (.env) |
| Containers | Docker Compose |

---

## Project Layout

```
codereview/          ← Django project package
  settings/
    base.py          ← shared settings (DB, DRF, Celery, installed apps)
    dev.py           ← DEBUG=True, console email backend
    prod.py          ← HTTPS/HSTS headers, SMTP email, DEBUG=False
  celery.py          ← Celery app, autodiscover_tasks()
  urls.py            ← root URL conf (JWT + 4 app includes)
  wsgi.py / asgi.py

users/               ← custom User model
repos/               ← Repository, PullRequest, Commit, DiffFile
reviews/             ← Review, ReviewComment
notifications/       ← scaffold only (model empty, no tasks yet)

docker-compose.yml   ← postgres:15 on 5432, redis:7 on 6379
pytest.ini           ← points pytest at codereview.settings.dev
.env                 ← local secrets (not committed)
.env.example         ← documents all required env vars
```

---

## Settings Pattern

`manage.py` and `wsgi/asgi` default to `codereview.settings.dev`.

`base.py` reads all secrets via `python-decouple`:
```
SECRET_KEY, DB_ENGINE, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, REDIS_URL, ALLOWED_HOSTS
```

**DB flexibility:** `base.py` checks `DB_ENGINE` env var. `.env` currently sets it to `django.db.backends.sqlite3` so local dev works without Docker. To use PostgreSQL, change `DB_ENGINE` in `.env` to `django.db.backends.postgresql` and run `docker compose up -d`.

`prod.py` adds HSTS, SSL redirect, secure cookies, and SMTP email on top of base.

---

## Installed Apps Order

```python
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
# THIRD_PARTY: rest_framework, rest_framework_simplejwt, django_fsm
# LOCAL: users, repos, reviews, notifications
```

---

## Auth

JWT via simplejwt. Two root endpoints:
- `POST /api/token/`         — returns access + refresh tokens
- `POST /api/token/refresh/` — exchanges refresh token for new access token

DRF default permission is `IsAuthenticated` — all endpoints require a valid JWT unless explicitly overridden.

---

## Data Models

### users.User (`users/models.py`)
Extends `AbstractUser`. Extra fields: `bio`, `avatar_url`, `github_username`.
Registered as `AUTH_USER_MODEL = "users.User"`.

### repos app (`repos/models.py`)

**Repository**
- `name`, `github_url`, `created_at`
- FK → `User` (owner)
- `unique_together`: (owner, name)

**PullRequest**
- `title`, `description`, `base_branch`, `head_branch`, `created_at`, `updated_at`
- FK → `Repository`, FK → `User` (author)
- `status` via `TextChoices`: `draft → open → in_review → approved → merged / closed`

**Commit**
- `sha` (40 chars), `message`, `committed_at`
- FK → `PullRequest`, FK → `User` (author)
- `unique_together`: (pr, sha)

**DiffFile**
- `file_path`, `change_type` (`added / modified / deleted`)
- FK → `Commit`
- `patch` — `JSONField` storing the structured hunk list produced by `GitDiffParser`

### reviews app (`reviews/models.py`)

**Review**
- FK → `PullRequest`, FK → `User` (reviewer)
- `status` via `TextChoices`: `pending / approved / changes_requested`
- `submitted_at` (nullable until submitted)
- `unique_together`: (pr, reviewer) — one review per reviewer per PR

**ReviewComment**
- FK → `Review`, FK → `DiffFile`
- `commit_sha`, `line_position`, `body`, `created_at`
- `parent` — self-referential FK (`null=True`) for threaded replies

---

## Git Diff Parser (`repos/utils.py`)

`GitDiffParser.parse_diff(raw_diff_text)` turns unified diff text into structured Python:

```python
[
  {
    "file_path": "foo.py",
    "change_type": "modified",   # added | modified | deleted
    "hunks": [
      {
        "old_start": 1, "old_lines": 4,
        "new_start": 1, "new_lines": 4,
        "lines": [
          {"content": "...", "line_type": "context", "old_lineno": 1, "new_lineno": 1},
          {"content": "...", "line_type": "removed", "old_lineno": 2, "new_lineno": None},
          {"content": "...", "line_type": "added",   "old_lineno": None, "new_lineno": 2},
        ]
      }
    ]
  }
]
```

How it works:
- Splits on `diff --git` boundary using `re.split` with a lookahead so the delimiter is kept
- Detects `added` / `deleted` from header lines (`new file mode` / `deleted file mode`)
- Tracks `old_lineno` / `new_lineno` counters per hunk, advancing them correctly for each line type

---

## Tests (`repos/tests/test_diff_parser.py`)

29 unit tests across 5 classes:
- `TestSingleFileDiff` — path, change type, hunk header, line counts, context/added/removed content
- `TestMultiFileDiff` — two files parsed, correct paths and line content
- `TestChangeTypeDetection` — added/deleted files, line type purity, lineno nulls
- `TestMultiHunkDiff` — two hunks, correct start positions
- `TestEdgeCases` — empty string, whitespace-only input

Run with:
```
pytest
```

---

## Celery (`codereview/celery.py`)

```python
app = Celery("codereview")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

Broker and result backend both point to Redis (`REDIS_URL` env var, default `redis://localhost:6379/0`). Any `tasks.py` in an app is auto-discovered.

No tasks have been written yet — the wiring is ready.

---

## Docker Compose

```
docker compose up -d
```

Starts:
- `postgres:15-alpine` → `localhost:5432`, DB `codereview`, user/pass `postgres/postgres`
- `redis:7-alpine` → `localhost:6379`

Both services use named volumes (`postgres_data`, `redis_data`) for persistence.

---

## URL Structure (wired, views not yet written)

```
/admin/
/api/token/
/api/token/refresh/
/api/users/         ← users.urls (empty)
/api/repos/         ← repos.urls (empty)
/api/reviews/       ← reviews.urls (empty)
/api/notifications/ ← notifications.urls (empty)
```

---

## Phase 2 — Completed (Session 2)

Everything below was built and verified (68 tests passing) in the second session.

---

## Auth & Registration

### JWT (simplejwt)

Token obtain and refresh were wired in Phase 1. Phase 2 added:

- **Token blacklist** — `rest_framework_simplejwt.token_blacklist` added to `INSTALLED_APPS`.
- **SIMPLE_JWT settings** in `base.py`: 30-min access token, 1-day refresh, rotate on refresh, blacklist after rotation.
- **Logout endpoint** — `POST /api/users/logout/` accepts `{"refresh": "<token>"}`, blacklists it, returns `205`.
- **Registration** — `POST /api/users/register/` accepts `username`, `email`, `password`. Validates password strength via Django validators. Returns `201` with user data (password excluded).
- **Me** — `GET/PATCH /api/users/me/` returns/updates the current user's profile.

### GitHub OAuth2 (python-social-auth)

Package: `social-auth-app-django==5.4.3` (compatible with Django 4.2).

**Settings** (`base.py`):
```python
AUTHENTICATION_BACKENDS = [
    "social_core.backends.github.GithubOAuth2",
    "django.contrib.auth.backends.ModelBackend",
]
```

Env vars: `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`.

Custom pipeline step `users/pipeline.py:set_github_username` copies the GitHub login to `User.github_username`.

**REST endpoint** — `POST /api/users/auth/github/` accepts `{"access_token": "<github_token>"}`, authenticates via social-core's `do_auth`, returns JWT access + refresh tokens.

---

## RBAC

### User Roles (`users/models.py`)

```python
class Role(models.TextChoices):
    ADMIN = "admin"
    REVIEWER = "reviewer"
    AUTHOR = "author"       # default
```

`User.role` — `CharField`, default `"author"`.

### Permission Classes (`users/permissions.py`)

| Class | Logic |
|-------|-------|
| `IsAdmin` | `user.role == "admin"` |
| `IsReviewerOrAdmin` | `user.role in ("reviewer", "admin")` |
| `IsRepoOwnerOrAdmin` | object-level: `obj.owner == user` or admin |
| `IsPRAuthorOrAdmin` | object-level: `obj.author == user` or admin |

**Enforcement:**
- Review submission (`POST /api/prs/{id}/reviews/`) requires `IsReviewerOrAdmin`.
- All other endpoints require `IsAuthenticated` (DRF default).
- Registration and GitHub auth are `AllowAny`.

---

## PR State Machine (django-fsm)

### FSM Field (`repos/models.py`)

`PullRequest.status` is now an `FSMField` (was plain `CharField`). Transition methods enforce valid state changes at the model layer:

```
draft ──→ open ──→ in_review ──→ approved ──→ merged
  │         │         │              │
  └─────────┴─────────┴──────────────┘
                      ↓
                   closed ──→ open (reopen)
```

| Method | Source | Target |
|--------|--------|--------|
| `open_pr()` | draft | open |
| `submit_for_review()` | open | in_review |
| `approve()` | in_review | approved |
| `merge()` | approved | merged |
| `close()` | draft, open, in_review, approved | closed |
| `reopen()` | closed | open |

Invalid transitions raise `django_fsm.TransitionNotAllowed`.

### Transition History (`repos/models.py`)

```python
class PRTransitionHistory(models.Model):
    pr           # FK → PullRequest
    from_status  # CharField
    to_status    # CharField
    actor        # FK → User
    timestamp    # DateTimeField (auto_now_add)
```

History records are created in the `PRTransitionView` after a successful transition and save.

`PullRequest.TRANSITION_MAP` maps client-facing transition names to method names (both are identical: `open_pr`, `submit_for_review`, `approve`, `merge`, `close`, `reopen`).

---

## REST API Endpoints

### Users (`users/urls.py`, prefix `/api/users/`)

| Method | Path | View | Permission | Description |
|--------|------|------|------------|-------------|
| POST | `register/` | `RegisterView` | AllowAny | Create account |
| GET/PATCH | `me/` | `MeView` | IsAuthenticated | Current user profile |
| POST | `logout/` | `LogoutView` | IsAuthenticated | Blacklist refresh token |
| POST | `auth/github/` | `GitHubAuthView` | AllowAny | GitHub OAuth → JWT |

### Repositories (`repos/urls.py`, prefix `/api/repos/`)

| Method | Path | View | Description |
|--------|------|------|-------------|
| GET | `` | `RepositoryListCreate` | List all repos (paginated) |
| POST | `` | `RepositoryListCreate` | Create repo (owner = current user) |
| GET | `{id}/` | `RepositoryDetail` | Repo detail |
| GET | `{repo_id}/prs/` | `PRListCreate` | List PRs for repo (paginated) |
| POST | `{repo_id}/prs/` | `PRListCreate` | Create PR under repo |

### Pull Requests (root `urls.py`, prefix `/api/prs/`)

| Method | Path | View | Description |
|--------|------|------|-------------|
| GET | `{id}/` | `PRDetail` | PR detail |
| GET | `{id}/diff/` | `PRDiffView` | All commits + diff files |
| POST | `{id}/comments/` | `PRCommentCreate` | Add inline comment (auto-creates pending review) |
| POST | `{id}/reviews/` | `PRReviewSubmit` | Submit review (approved / changes_requested) |
| POST | `{id}/transition/` | `PRTransitionView` | State transition (`{"transition": "open_pr"}`) |
| GET | `{id}/history/` | `PRTransitionHistoryView` | Transition history (paginated) |

### Reviews (`reviews/urls.py`, prefix `/api/reviews/`)

| Method | Path | View | Description |
|--------|------|------|-------------|
| POST | `comments/{id}/resolve/` | `CommentResolveView` | Toggle `is_resolved` |

---

## Serializers

| Serializer | App | Notes |
|------------|-----|-------|
| `UserSerializer` | users | Read-only: id, role |
| `RegisterSerializer` | users | Write-only password, validates strength |
| `RepositorySerializer` | repos | owner from context; validates unique (owner, name) |
| `PullRequestSerializer` | repos | repo + author + status are read-only |
| `PRTransitionSerializer` | repos | Validates transition name against `TRANSITION_MAP` |
| `PRTransitionHistorySerializer` | repos | Read-only |
| `CommitSerializer` | repos | Nested `DiffFileSerializer` |
| `DiffFileSerializer` | repos | Includes `patch` JSONField |
| `ReviewSerializer` | reviews | Nested comments |
| `ReviewCommentSerializer` | reviews | review + is_resolved are read-only |
| `SubmitReviewSerializer` | reviews | get_or_create review, sets submitted_at |

---

## Comment Threading & Resolution (`reviews/models.py`)

`ReviewComment` additions in Phase 2:
- `is_resolved` — `BooleanField(default=False)`. Toggled via `POST /api/reviews/comments/{id}/resolve/`.
- `parent` — self-referential FK existed in Phase 1. Phase 2 wired it through the comment creation endpoint (`parent` field in POST body).

---

## Notification Model (`notifications/models.py`)

```python
class Notification(models.Model):
    class EventType(models.TextChoices):
        REVIEW_SUBMITTED = "review_submitted"
        COMMENT_ADDED = "comment_added"
        PR_STATE_CHANGED = "pr_state_changed"
        COMMENT_RESOLVED = "comment_resolved"

    recipient    # FK → User
    actor        # FK → User
    event_type   # CharField
    message      # TextField
    is_read      # BooleanField(default=False)
    created_at   # DateTimeField(auto_now_add)
```

Model is defined; endpoints and Celery tasks for sending notifications are **not yet wired**.

---

## Admin Registrations

All models registered in their respective `admin.py`:
- `UserAdmin` — extends Django's `UserAdmin` with role, github_username, bio, avatar_url fields.
- `RepositoryAdmin`, `PullRequestAdmin`, `CommitAdmin`, `DiffFileAdmin`, `PRTransitionHistoryAdmin` — list display, filters, search.
- `ReviewAdmin`, `ReviewCommentAdmin` — list display with is_resolved filter.

---

## Factories (`factory_boy`)

| Factory | App | Notes |
|---------|-----|-------|
| `UserFactory` | users | role=author, password=testpass123 |
| `AdminFactory` | users | role=admin |
| `ReviewerFactory` | users | role=reviewer |
| `RepositoryFactory` | repos | auto owner via UserFactory |
| `PullRequestFactory` | repos | auto repo + author |
| `CommitFactory` | repos | sequential 40-char sha |
| `DiffFileFactory` | repos | default modified + stub patch |
| `ReviewFactory` | reviews | auto PR + reviewer |
| `ReviewCommentFactory` | reviews | auto review + diff_file |

---

## Tests

68 tests total. Run with:
```
pytest
```

| File | Tests | Covers |
|------|-------|--------|
| `repos/tests/test_diff_parser.py` | 29 | Git diff parser (Phase 1) |
| `repos/tests/test_api.py` | 20 | Repos CRUD, PR CRUD, diff view, FSM transitions, transition history, invalid transitions |
| `reviews/tests.py` | 13 | Submit review (RBAC), inline comments, auto-create review, threaded replies, resolve/unresolve |
| `users/tests.py` | 11 | Registration, token obtain, logout/blacklist, me endpoint, RBAC roles |

---

## Migrations Added in Phase 2

- `users/0002_user_role.py` — adds `role` field
- `repos/0002_alter_pullrequest_status_prtransitionhistory.py` — converts status to FSMField, creates PRTransitionHistory
- `reviews/0002_reviewcomment_is_resolved.py` — adds `is_resolved` field
- `notifications/0001_initial.py` — creates Notification model
- `social_django` and `token_blacklist` migrations auto-applied

---

## Dependencies Added in Phase 2

- `social-auth-app-django==5.4.3` (Django 4.2 compatible) — brings in `social-auth-core`, `requests`, `cryptography`, etc.

---

## What Is NOT Done (Phase 3 scope)

- Celery tasks (e.g., send notification on review submitted, PR state changed)
- Notification delivery endpoints (list, mark-read)
- `django-fsm` permission hooks (restrict who can trigger which transition)
- Webhook integration for real GitHub repository events
- File upload / real git repository cloning
