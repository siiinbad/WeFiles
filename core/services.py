from functools import wraps

from django.db import transaction
from django.shortcuts import render
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import RateLimitBucket


def consume_limit(identity, limit, seconds):
    """Atomically consume a window; persist only a keyed digest of the identity."""
    key = salted_hmac("wefiles.throttle", identity, algorithm="sha256").hexdigest()
    now = timezone.now()
    with transaction.atomic():
        bucket, _ = RateLimitBucket.objects.select_for_update().get_or_create(
            key=key, defaults={"started_at": now}
        )
        if (now - bucket.started_at).total_seconds() >= seconds:
            bucket.started_at, bucket.count = now, 0
        if bucket.count >= limit:
            return False
        bucket.count += 1
        bucket.save()
    return True


def rate_limit(scope, limit=5, seconds=900):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method == "POST":
                identity = (
                    str(request.user.pk)
                    if request.user.is_authenticated
                    else request.META.get("REMOTE_ADDR", "unknown")
                )
                if not consume_limit(f"{scope}:{identity}", limit, seconds):
                    response = render(request, "errors/429.html", status=429)
                    response["Retry-After"] = str(seconds)
                    return response
            return view(request, *args, **kwargs)

        return wrapped

    return decorator
