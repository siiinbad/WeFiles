from .models import Notification


def notify(user, kind, text, destination=""):
    if destination and (not destination.startswith("/") or destination.startswith("//")):
        raise ValueError("Notifications require an internal destination.")
    return Notification.objects.create(
        recipient=user, kind=kind, text=text, destination=destination
    )
