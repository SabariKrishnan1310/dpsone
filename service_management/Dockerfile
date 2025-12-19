FROM python:3.11-alpine

ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

# System deps
RUN apk update && \
    apk add --no-cache postgresql-client libpq-dev build-base

# Install Python deps
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install --no-cache-dir daphne channels_redis whitenoise

# 🔴 COPY APP FIRST (THIS WAS MISSING)
COPY . .

# 🔴 NOW collect static (admin CSS will exist)
RUN python manage.py collectstatic --noinput

# Optional cleanup
RUN apk del build-base
