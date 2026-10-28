"""Fail-closed production settings for a TLS reverse proxy."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False
if len(SECRET_KEY) < 50:  # noqa: F405
    raise ImproperlyConfigured("Production SECRET_KEY must have at least 50 characters.")
if not env("ALLOWED_HOSTS", default="") or "*" in ALLOWED_HOSTS:  # noqa: F405
    raise ImproperlyConfigured("Set explicit production ALLOWED_HOSTS.")
if not SITE_URL.startswith("https://"):  # noqa: F405
    raise ImproperlyConfigured("Production SITE_URL must use HTTPS.")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = "same-origin"
if env.bool("TRUST_PROXY_HTTPS", default=False):  # noqa: F405
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if env("SENTRY_DSN", default=""):  # noqa: F405
    import sentry_sdk

    sentry_sdk.init(dsn=env("SENTRY_DSN"), send_default_pii=False, traces_sample_rate=0.0)  # noqa: F405
