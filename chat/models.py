import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Length, Trim


class ChatMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.CharField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=["created_at", "id"])]
        constraints = [
            models.CheckConstraint(
                condition=models.lookups.GreaterThan(Length(Trim("content")), 0),
                name="chat_not_blank",
            ),
            models.CheckConstraint(
                condition=models.lookups.LessThanOrEqual(Length("content"), 2000),
                name="chat_max_length",
            ),
        ]

    def clean(self):
        self.content = self.content.strip()
        if not self.content:
            raise ValidationError({"content": "Write a message before sending."})
