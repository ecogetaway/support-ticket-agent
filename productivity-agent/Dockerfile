# ── Build stage ────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Runtime stage ──────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

ENV PORT=8081
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PRODUCTIVITY_DB_PATH=/tmp/productivity.db

EXPOSE 8081

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
