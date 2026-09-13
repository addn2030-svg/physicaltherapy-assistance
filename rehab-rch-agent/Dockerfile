# Rehab RCH Agent v2 — container build (optional alternative to systemd)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# .env + credentials.json are mounted at runtime, never baked into the image.
HEALTHCHECK --interval=2m --timeout=10s --start-period=90s --retries=3 \
  CMD python -c "import time,os; assert time.time()-os.stat('/app/output/heartbeat.txt').st_mtime < 300"
CMD ["python", "bot.py"]
