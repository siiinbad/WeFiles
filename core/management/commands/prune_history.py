from datetime import timedelta

from axes.models import AccessAttempt, AccessFailureLog, AccessLog
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.utils import timezone

from activity.models import ActivityEvent
from core.models import RateLimitBucket


class Command(BaseCommand):
    help = (
        "Apply configured security/activity retention and remove expired sessions. Schedule daily."
    )

    def handle(self, *args, **options):
        now = timezone.now()
        cutoff = now - timedelta(days=settings.SECURITY_RETENTION_DAYS)
        for model in (AccessAttempt, AccessFailureLog, AccessLog):
            model.objects.filter(attempt_time__lt=cutoff).delete()
        ActivityEvent.objects.filter(
            created_at__lt=now - timedelta(days=settings.ACTIVITY_RETENTION_DAYS)
        ).delete()
        RateLimitBucket.objects.filter(started_at__lt=now - timedelta(days=1)).delete()
        Session.objects.filter(expire_date__lt=now).delete()
        self.stdout.write("Configured history retention applied.")
