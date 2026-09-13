# Rehab RCH Agent v2 — container build (optional alternative to systemd)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# .env + credentials.json are mounted at runtime, never baked into the image.
CMD ["python", "bot.py"]
