from django.db import transaction

from vault.services import require_member

from .models import ChatMessage


@transaction.atomic
def send_message(user, content):
    require_member(user)
    message = ChatMessage(sender=user, content=content)
    message.full_clean()
    message.save()
    return message
