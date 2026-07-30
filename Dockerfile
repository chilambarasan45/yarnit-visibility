# Backend Dockerfile — Yarnit AI Visibility Platform
FROM python:3.13-slim

WORKDIR /app

# System deps needed for psycopg2 to build/run
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright + headless Chromium, used as a fallback in serp_service.py
# for JS-rendered storefronts (React/Next.js sites) where a plain
# requests.get() only sees an empty page shell.
#
# --with-deps installs the browser binary AND the system-level shared
# libraries (fonts, codecs, etc.) it needs to actually launch on a bare
# Linux container -- skipping --with-deps here is the #1 cause of
# "playwright works locally on Windows but fails on the server" bugs.
RUN pip install --no-cache-dir playwright \
    && playwright install --with-deps chromium

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]