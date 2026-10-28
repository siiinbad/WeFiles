FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=config.settings.production
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . ./
RUN SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')" ALLOWED_HOSTS=build.local SITE_URL=https://build.local python manage.py collectstatic --noinput \
    && groupadd --gid 10001 wefiles \
    && useradd --uid 10001 --gid wefiles --no-create-home wefiles \
    && mkdir -p /app/media \
    && chown -R wefiles:wefiles /app
USER wefiles
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "120", "--access-logfile", "-", "--access-logformat", "%(h)s %(t)s %(m)s %(s)s %(L)s", "--error-logfile", "-"]
