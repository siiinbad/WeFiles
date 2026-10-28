from core.admin import register_readonly

from .models import ActivityEvent

register_readonly(ActivityEvent, ("action", "actor", "object_type", "created_at"))
