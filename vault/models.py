import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


def private_upload_path(instance, filename):
    return f"objects/{uuid.uuid4().hex}"


def validate_name(value):
    if (
        not value.strip()
        or value.strip() in (".", "..")
        or any(c in value for c in "/\\")
        or any(ord(c) < 32 for c in value)
    ):
        raise ValidationError("Enter a name without slashes or control characters.")


class Folder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    name = models.CharField(max_length=80, validators=[validate_name])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "pk"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                "parent",
                condition=models.Q(parent__isnull=False),
                name="folder_sibling_ci",
            ),
            models.UniqueConstraint(
                Lower("name"), condition=models.Q(parent__isnull=True), name="folder_root_ci"
            ),
            models.CheckConstraint(
                condition=~models.Q(id=models.F("parent")), name="folder_not_self_parent"
            ),
        ]

    def clean(self):
        super().clean()
        self.name = self.name.strip()
        validate_name(self.name)
        seen = {self.pk}
        parent = self.parent
        depth = 0
        while parent:
            if parent.pk in seen or depth >= 20:
                raise ValidationError(
                    {
                        "parent": "Choose a folder outside this folder's descendants (maximum depth: 20)."
                    }
                )
            seen.add(parent.pk)
            depth += 1
            parent = parent.parent

    def __str__(self):
        return self.name


class File(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="files"
    )
    folder = models.ForeignKey(
        Folder, null=True, blank=True, on_delete=models.PROTECT, related_name="files"
    )
    blob = models.FileField(upload_to=private_upload_path, max_length=100)
    name = models.CharField(max_length=255, validators=[validate_name])
    description = models.CharField(max_length=1000, blank=True)
    size_bytes = models.PositiveBigIntegerField()
    content_type = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(fields=["folder", "created_at"]),
            models.Index(fields=["owner", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(size_bytes__gt=0), name="file_positive_size")
        ]

    @property
    def extension(self):
        return Path(self.name).suffix.lstrip(".").upper()[:5] or "FILE"

    @property
    def category(self):
        if self.content_type.startswith("image/"):
            return "image"
        if self.extension == "PDF":
            return "pdf"
        if self.extension in ("CSV", "XLS", "XLSX"):
            return "sheet"
        return "document"

    def __str__(self):
        return self.name


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name="favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "file"], name="favorite_once")]


class StorageDeletionJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    storage_key = models.CharField(max_length=100, unique=True)
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_error_code = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
