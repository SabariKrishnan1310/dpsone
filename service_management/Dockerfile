FROM python:3.11-alpine

ENV PYTHONUNBUFFERED=1

WORKDIR /usr/s/rc/app


RUN apk update && \
    apk add --no-cache postgresql-client libpq-dev build-base

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install --no-cache-dir daphne channels_redis whitenoise


COPY . .


RUN python manage.py collectstatic --noinput


RUN apk del build-base
