# Code Review Platform — Project Brief

This is a full-stack code review platform (Django 4.2 API + React 18 frontend) that replicates core GitHub code-review workflows: repositories, pull requests, commit diffs, inline review comments, and notifications.

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
| Backend testing | pytest + pytest-django + factory_boy |
| Frontend | React 18 + Vite 8 + Tailwind CSS 3.4 |
| Frontend testing | Vitest + Testing Library + MSW 2 |
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
notifications/       ← Notification model, signals, Celery tasks, SSE stream

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
# THIRD_PARTY: rest_framework, rest_framework_simplejwt, django_fsm, social_django
# LOCAL: users, repos, reviews, notifications.apps.NotificationsConfig
```

**Important:** `notifications` must be registered as `notifications.apps.NotificationsConfig` (not bare `"notifications"`) so that `AppConfig.ready()` is called, which connects the Django signals in `notifications/signals.py`.

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

**Dev mode:** `CELERY_TASK_ALWAYS_EAGER = True` in `dev.py` — tasks execute synchronously in the Django process, no worker needed.

**Prod / manual worker:** On Windows, use `--pool=solo`:
```bash
celery -A codereview worker -l info --pool=solo
```

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

## URL Structure

```
/admin/
/api/token/          ← JWT obtain
/api/token/refresh/  ← JWT refresh
/api/users/          ← users.urls (register, me, logout, github auth)
/api/repos/          ← repos.urls (CRUD, PRs per repo)
/api/prs/            ← flat PR endpoints (detail, diff, comments, reviews, transitions)
/api/reviews/        ← reviews.urls (comment resolve)
/api/notifications/  ← notifications.urls (list, mark-read, SSE stream)
/api/webhooks/github/ ← GitHub webhook receiver (HMAC-verified)
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

Model is defined. Endpoints and Celery tasks wired in Phase 4.

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

91 tests total (68 from Phases 1–2, 23 added in Phase 4). Run with:
```
pytest
```

| File | Tests | Covers |
|------|-------|--------|
| `repos/tests/test_diff_parser.py` | 29 | Git diff parser (Phase 1) |
| `repos/tests/test_api.py` | 20 | Repos CRUD, PR CRUD, diff view, FSM transitions, transition history, invalid transitions |
| `repos/tests/test_webhooks.py` | 11 | HMAC verification, push/PR/review webhook handlers (Phase 4) |
| `reviews/tests.py` | 13 | Submit review (RBAC), inline comments, auto-create review, threaded replies, resolve/unresolve |
| `users/tests.py` | 11 | Registration, token obtain, logout/blacklist, me endpoint, RBAC roles |
| `notifications/tests.py` | 14 | Notification list/filter, mark read, mark all read, SSE stream auth, signals (Phase 4) |

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

## What Was Deferred to Phase 4

- ~~Celery tasks~~ → Done in Phase 4
- ~~Notification delivery endpoints~~ → Done in Phase 4
- ~~Webhook integration for real GitHub repository events~~ → Done in Phase 4
- `django-fsm` permission hooks (restrict who can trigger which transition) — still deferred
- File upload / real git repository cloning — still deferred

---

## Phase 3 — Completed (Session 3)

Full React frontend built and wired to the Django API.

---

### Frontend Stack

| Layer | Technology |
|-------|-----------|
| UI framework | React 18.3 + Vite 8 |
| Styling | Tailwind CSS 3.4, dark mode (`darkMode: 'class'`) |
| Fonts | Inter (UI), JetBrains Mono (code) via Google Fonts |
| Routing | React Router v6 |
| Server state | TanStack React Query v5 |
| HTTP client | Axios (with JWT interceptor + auto-refresh) |
| Syntax highlighting | Prism.js (custom GitHub-style token colors for light + dark) |
| Notifications | react-hot-toast (bottom-right) |
| Icons | Heroicons v2 (`@heroicons/react`) |
| Testing | Vitest + Testing Library + MSW 2 |

Dev server: `http://localhost:5173`, proxies `/api/*` to `http://127.0.0.1:8000`.

---

### Frontend Project Layout

```
frontend/
  index.html              ← entry HTML, loads Inter + JetBrains Mono
  vite.config.js          ← port 5173, /api proxy to Django, vitest config
  tailwind.config.js      ← darkMode: 'class', custom fonts + animations
  postcss.config.js       ← Tailwind + Autoprefixer
  package.json            ← scripts: dev, build, test, lint
  src/
    main.jsx              ← React root: BrowserRouter, QueryClient, ThemeProvider, AuthProvider, Toaster
    App.jsx               ← route definitions, sidebar layout, NotificationProvider wrapper
    index.css             ← Tailwind directives, custom scrollbar, Prism token colors (light + dark)
    api/
      index.js            ← Axios instance, Bearer token interceptor, 401 auto-refresh, all API functions
    context/
      AuthContext.jsx      ← JWT stored in memory, login/logout/fetchUser, useAuth() hook
      ThemeContext.jsx      ← dark/light toggle, persists to localStorage('cr-theme'), useTheme() hook
    components/
      Sidebar.jsx          ← fixed left sidebar (240px / 64px collapsed), nav items, theme toggle, user avatar
      PageHeader.jsx       ← sticky top header with breadcrumbs + actions slot, backdrop blur
      StatusBadge.jsx      ← pill with colored dot + label per PR status, dark mode variants
      DiffViewer.jsx       ← GitHub-style file headers, line gutters, "+" comment button on hover, Prism highlight
      CommentThread.jsx    ← avatar initials, relative timestamps, reply indent, resolve checkmark toggle
      ReviewerPanel.jsx    ← PR status, author, branches as badges, transition buttons with icons, review submission
      NotificationToast.jsx ← SSE listener via useSSE, fires react-hot-toast, exports NotificationProvider + useNotificationCount
      Modal.jsx            ← dark-themed modal with backdrop blur, animate-fade-in
      ProtectedRoute.jsx   ← auth guard, spinner on loading, redirect to /login
      Skeleton.jsx         ← Skeleton, SkeletonCard, SkeletonRow for loading states
      EmptyState.jsx       ← icon + title + description + optional CTA button
      Navbar.jsx           ← original top navbar (unused — replaced by Sidebar, kept for reference)
    pages/
      LoginPage.jsx        ← gradient background, floating labels, logo, shake animation on error, spinner
      RegisterPage.jsx     ← same treatment as LoginPage, 3 fields (username, email, password)
      RepositoryListPage.jsx ← card grid, skeleton loading (6 cards), empty state with CTA, hover elevation
      PRListPage.jsx       ← table layout, filter tabs (All / Open / Merged / Closed), client-side filtering
      PRDetailPage.jsx     ← breadcrumbs, title + status header, 2-column (diff + sidebar with file tree + reviewer panel)
      NotificationsPage.jsx ← notification list, date grouping, unread highlighting, mark-read, filter tabs
    hooks/
      usePR.js             ← React Query wrapper for getPR()
      useDiff.js           ← React Query wrapper for getDiff()
      useComments.js       ← extracts comments from PR reviews via getPR()
      useSSE.js            ← connects to SSE with JWT token query param, returns { event, unreadCount, resetCount }
    utils/
      dates.js             ← formatDate(), formatDateTime(), relativeTime() ("3h ago")
      classNames.js        ← cn() — filters falsy values, joins with space
    test/
      setup.js             ← jest-dom matchers, MSW server lifecycle, matchMedia polyfill
      mocks/handlers.js    ← MSW handlers: /api/token/, /api/users/me/, /api/users/register/, /api/repos/, /api/prs/:id/diff/
      mocks/server.js      ← MSW setupServer
      AuthContext.test.jsx  ← login sets user, logout clears user
      StatusBadge.test.jsx  ← all 6 statuses render correct label + bg color class
      DiffViewer.test.jsx   ← renders container, file path, added/removed/context line testids, empty state
      CommentThread.test.jsx ← renders comments, submits new comment, rejects empty submit
      LoginPage.test.jsx    ← renders form fields, shows error toast on invalid credentials
```

---

### Frontend Routes

| Path | Component | Auth | Description |
|------|-----------|------|-------------|
| `/login` | LoginPage | public | JWT login form |
| `/register` | RegisterPage | public | User registration |
| `/` | RepositoryListPage | protected | Repo card grid |
| `/repos/:repoId/prs` | PRListPage | protected | PR table for a repo |
| `/prs/:id` | PRDetailPage | protected | Diff viewer + reviewer panel |
| `/prs` | PlaceholderPage | protected | "Coming soon" placeholder |
| `/notifications` | NotificationsPage | protected | Notification list with filters, mark read |

---

### Auth Flow

1. **Login:** POST `/api/token/` → stores access token in memory (not localStorage)
2. **API calls:** Axios interceptor adds `Authorization: Bearer <token>` header
3. **401 handling:** Interceptor attempts POST `/api/token/refresh/`; on success retries original request; on failure redirects to `/login`
4. **Logout:** Clears in-memory token + user state

---

### Design System

- **Theme:** Dark default, light mode toggle via ThemeContext (class `dark` on `<html>`)
- **Color palette:** Zinc/slate neutrals, indigo/violet accents
- **Typography:** Inter for UI, JetBrains Mono for code and diffs
- **Spacing:** Tailwind's default 8px-grid scale
- **Components use `text-[13px]`** for compact, dev-tool density
- **Transitions:** `transition-colors` on interactive elements, `animate-fade-in` on modals, `animate-shake` on login error
- **Scrollbar:** Custom thin 6px scrollbar via `::-webkit-scrollbar` in index.css

---

### Frontend Tests

20 tests, all passing. Run with:
```
cd frontend && npm test
```

| File | Tests | Covers |
|------|-------|--------|
| `AuthContext.test.jsx` | 3 | Login sets user, logout clears, starts with no user |
| `StatusBadge.test.jsx` | 6 | All 6 statuses: correct label text + `bg-*-100` color class |
| `DiffViewer.test.jsx` | 6 | Container renders, file path shown, added/removed/context line testids, empty state |
| `CommentThread.test.jsx` | 3 | Renders comments with author, submits comment with correct payload, rejects empty |
| `LoginPage.test.jsx` | 2 | Form renders with labeled inputs, shows error toast on bad credentials |

Tests use MSW to mock API responses. `matchMedia` polyfilled in setup for react-hot-toast.

---

### How to Run

```bash
# 1. Start infrastructure (postgres + redis)
docker compose up -d

# 2. Start Django backend (separate terminal)
python manage.py runserver

# 3. Start frontend dev server (separate terminal)
cd frontend && npm run dev

# 4. (Optional) Start Celery worker — not needed in dev (CELERY_TASK_ALWAYS_EAGER)
#    On Windows use --pool=solo:
celery -A codereview worker -l info --pool=solo
```

Frontend: `http://localhost:5173`
Backend: `http://localhost:8000`
Admin: `http://localhost:8000/admin/`

---

### Known Gaps (Phase 5 scope)

- `/prs` frontend route still shows "Coming soon" placeholder
- Diff viewer shows "No changes" until real git commits are attached to PRs
- Split-view toggle in diff viewer is UI-only (not implemented)
- `django-fsm` permission hooks not yet wired
- File upload / real git repository cloning
- Docker containerization for the Django/Celery/frontend services
- CI/CD pipeline
- AI-powered code reviewer
- Production deployment

---

## Phase 4 — Completed (Session 4)

Webhooks, async Celery workers, SSE notifications, and full notification UI.

---

### Celery Tasks

#### repos/tasks.py

| Task | Description |
|------|-------------|
| `parse_pr_diff(pr_id)` | Fetches PR commits, runs GitDiffParser, creates DiffFile records |
| `process_webhook_event(event_type, payload)` | Routes incoming webhook events to appropriate handlers |

#### notifications/tasks.py

| Task | Description |
|------|-------------|
| `send_comment_notification(comment_id)` | Notifies PR author when a new comment is added |
| `send_review_notification(review_id)` | Notifies PR author when a review is submitted |
| `send_pr_state_notification(pr_id, from_status, to_status, actor_id)` | Notifies PR author + all reviewers on state change |
| `send_email_notification(user_id, subject, body)` | Sends email via Django email backend |

All notification tasks skip self-notifications (actor == recipient). When testing with a single user who is both PR author and actor, zero notifications will be created — use two separate users to see notifications.

---

### Django Signals (`notifications/signals.py`)

| Signal | Sender | Fires Task |
|--------|--------|------------|
| `post_save` | `ReviewComment` (created) | `send_comment_notification.delay()` |
| `post_save` | `Review` (submitted_at set) | `send_review_notification.delay()` |
| `post_save` | `PRTransitionHistory` (created) | `send_pr_state_notification.delay()` |

Connected via `NotificationsConfig.ready()` in `notifications/apps.py`.

---

### GitHub Webhooks

**Endpoint:** `POST /api/webhooks/github/`

**HMAC verification** (`repos/webhooks.py:verify_signature`):
- Reads `X-Hub-Signature-256` header
- Computes HMAC-SHA256 using `GITHUB_WEBHOOK_SECRET` env var
- Timing-safe comparison via `hmac.compare_digest()`
- Returns 400 if header missing, 403 if mismatch

**Event handlers** (`repos/webhooks.py`):

| Handler | Event | Behavior |
|---------|-------|----------|
| `handle_push` | `push` | Finds repo by `github_url`, creates Commit records for open PRs |
| `handle_pull_request` | `pull_request` | Creates PR on `opened`, updates status on `closed`/`reopened`/`merged` |
| `handle_pull_request_review` | `pull_request_review` | Creates/updates Review record from GitHub review state |

**View** (`repos/views.py:GitHubWebhookView`):
- `AllowAny` permission, no authentication
- Reads raw body before parsing, verifies signature first
- Dispatches to `process_webhook_event.delay()` for async processing
- Always returns 200 quickly

**Settings:** `GITHUB_WEBHOOK_SECRET = config("GITHUB_WEBHOOK_SECRET", default="dev-secret")` in `base.py`

---

### SSE Endpoint

`GET /api/notifications/stream/?token=<JWT_access_token>`

- Auth via JWT token in query param (EventSource can't set headers)
- Returns `StreamingHttpResponse` with `Content-Type: text/event-stream`
- Polls for unread notifications every 2 seconds
- Marks notifications as read after sending
- Sends heartbeat comment every 15 seconds
- CORS header: `Access-Control-Allow-Origin: http://localhost:5173`

---

### Notification REST Endpoints (`notifications/urls.py`, prefix `/api/notifications/`)

| Method | Path | View | Description |
|--------|------|------|-------------|
| GET | `` | `NotificationListView` | Paginated list, filter with `?unread=true` |
| PATCH | `{id}/read/` | `NotificationMarkReadView` | Mark single notification as read |
| POST | `mark-all-read/` | `NotificationMarkAllReadView` | Mark all as read, returns `{"marked": N}` |
| GET | `stream/` | `NotificationStreamView` | SSE stream (see above) |

---

### Frontend Updates (Phase 4)

**useSSE.js** — now appends `?token=<accessToken>` to SSE URL. Returns `{ event, unreadCount, resetCount }`.

**NotificationToast.jsx** — exports `NotificationProvider` (wraps app, provides `useNotificationCount` context) and `useNotificationCount()` hook for Sidebar badge.

**Sidebar.jsx** — Notifications nav item shows indigo unread count badge (pill in expanded, dot in collapsed).

**api/index.js** — three new functions: `getNotifications(unreadOnly)`, `markNotificationRead(id)`, `markAllNotificationsRead()`.

**NotificationsPage.jsx** — replaces placeholder. Features:
- All/Unread filter tabs
- Grouped by date with day headers
- Unread notifications highlighted with indigo left border
- Emoji icons per event type
- Hover-reveal "mark as read" button per item
- "Mark all read" button in header
- Empty state with context-sensitive message
- Uses React Query for data fetching + cache invalidation

**App.jsx** — wraps everything in `<NotificationProvider>`, routes `/notifications` to `NotificationsPage`.

---

### Factories Added in Phase 4

| Factory | App | Notes |
|---------|-----|-------|
| `NotificationFactory` | notifications | auto recipient + actor, default comment_added |

---

### Settings Changes in Phase 4

- `GITHUB_WEBHOOK_SECRET` added to `base.py` (via `python-decouple`, default `"dev-secret"`)
- `DEFAULT_FROM_EMAIL` added to `base.py` (default `"noreply@codereview.local"`)
- `CELERY_TASK_ALWAYS_EAGER = True` + `CELERY_TASK_EAGER_PROPAGATES = True` in `dev.py` (tasks run synchronously in dev/test)
- `GITHUB_WEBHOOK_SECRET`, `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET` added to `.env.example`

---

### Tests Added in Phase 4

91 backend tests total (23 new). Run with:
```
pytest
```

| File | New Tests | Covers |
|------|-----------|--------|
| `repos/tests/test_webhooks.py` | 11 | HMAC valid/invalid/missing, push creates commits, push unknown repo ignored, PR opened/closed/merged, review creates review |
| `notifications/tests.py` | 14 | List/filter, mark read own/others/nonexistent, mark all read, SSE auth required/invalid/valid, signals: comment/review/transition create notifications, no self-notification |

20 frontend tests unchanged (all passing).
