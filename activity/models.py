import uuid

from django.conf import settings
from django.db import models


class ActivityEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=40)
    object_type = models.CharField(max_length=30)
    object_id = models.UUIDField(null=True)
    object_label = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=["action", "created_at"])]

    @property
    def description(self):
        return {
            "account.registered": "requested to join the crew",
            "member.role_changed": "changed a member’s role",
            "member.status_changed": "updated a member’s access",
            "file.uploaded": "shared a file",
            "file.updated": "updated file details",
            "file.deleted": "deleted a file",
            "folder.saved": "organized a folder",
            "folder.deleted": "deleted a folder",
        }.get(self.action, "updated the workspace")
