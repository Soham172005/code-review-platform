# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /install

COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY --from=builder /install /usr/local

WORKDIR /app
COPY . .

RUN python manage.py collectstatic --noinput --settings=codereview.settings.prod 2>/dev/null || true

USER appuser

EXPOSE 8000

CMD ["gunicorn", "codereview.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
