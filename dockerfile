# Use official Python image as base
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

# Create a non-root user (Heroku best practice)
RUN useradd -m -r appuser && chown -R appuser /app
USER appuser

# Heroku sets PORT environment variable
CMD gunicorn app.wsgi:application --bind 0.0.0.0:$PORT