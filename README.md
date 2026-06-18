# Code Review Platform

A Django 4.2 REST API for collaborative code review, built with DRF, Celery, and PostgreSQL.

## Stack

- **Django 4.2** + **Django REST Framework** — API layer
- **PostgreSQL** — primary database
- **Redis** + **Celery** — async task queue
- **django-fsm** — review state machine
- **simplejwt** — JWT authentication
- **GitPython** — repository introspection

## Apps

| App | Responsibility |
|-----|---------------|
| `users` | Custom user model, auth |
| `repos` | Repository management |
| `reviews` | Code review workflow |
| `notifications` | Async notification delivery |

## Quick start

### 1. Start backing services

```bash
docker compose up -d
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env with your secrets
```

### 5. Run migrations and create a superuser

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. Start the dev server

```bash
python manage.py runserver
```

API root: http://localhost:8000/api/

### 7. Start Celery worker (separate terminal)

```bash
celery -A codereview worker -l info
```

## Settings

| File | Purpose |
|------|---------|
| `codereview/settings/base.py` | Shared settings |
| `codereview/settings/dev.py` | Local development overrides |
| `codereview/settings/prod.py` | Production hardening |

Override with `DJANGO_SETTINGS_MODULE` env var (defaults to `dev`).

## Testing

```bash
pytest
```
