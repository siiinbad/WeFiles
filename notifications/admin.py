from core.admin import register_readonly

from .models import Notification

register_readonly(Notification, ("kind", "recipient", "read_at", "created_at"))
