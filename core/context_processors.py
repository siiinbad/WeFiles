from django.conf import settings


def workspace(request):
    unread = 0
    if request.user.is_authenticated:
        unread = request.user.notifications.filter(read_at__isnull=True).count()
    return {"unread_count": unread, "privacy_contact": settings.PRIVACY_CONTACT}
