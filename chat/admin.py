from core.admin import register_readonly

from .models import ChatMessage

register_readonly(ChatMessage, ("id", "sender", "created_at"))
