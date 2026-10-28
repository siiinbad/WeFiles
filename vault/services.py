"""Permission-checked mutations with retryable private-storage deletion."""

import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from activity.services import record

from .models import Favorite, File, Folder, StorageDeletionJob, validate_name

logger = logging.getLogger(__name__)


def require_member(user, admin=False):
    if not user.approved or (admin and not user.workspace_admin):
        raise PermissionDenied


def _lock_folders():
    # A stable order serializes tree operations on PostgreSQL.
    return list(Folder.objects.select_for_update().order_by("pk"))


def upload_file(user, upload, folder=None, description=""):
    require_member(user)
    validate_name(upload.name)
    if not 0 < upload.size <= settings.MAX_UPLOAD_BYTES:
        raise ValidationError("The file is empty or exceeds the upload limit.")
    file = File(
        owner=user,
        folder=folder,
        name=upload.name,
        description=description,
        size_bytes=upload.size,
        content_type=(upload.content_type or "")[:150],
    )
    try:
        with transaction.atomic():
            if folder:
                Folder.objects.select_for_update().get(pk=folder.pk)
            file.blob.save(upload.name, upload, save=False)
            file.full_clean()
            file.save()
            record(user, "file.uploaded", file)
    except Exception:
        if file.blob.name:
            try:
                file.blob.storage.delete(file.blob.name)
            except Exception:
                StorageDeletionJob.objects.get_or_create(storage_key=file.blob.name)
                logger.exception("Upload compensation queued for retry")
        raise
    return file


@transaction.atomic
def save_folder(user, folder):
    require_member(user, admin=not folder._state.adding)
    tree = _lock_folders()
    if folder.parent_id:
        parent = next((item for item in tree if item.pk == folder.parent_id), None)
        if parent is None:
            raise ValidationError("That parent folder no longer exists. Choose another location.")
        folder.parent = parent
    if folder._state.adding:
        folder.creator = user
    folder.full_clean()
    depth, parent = 0, folder.parent
    while parent:
        depth += 1
        parent = parent.parent
    children = {}
    for item in tree:
        children.setdefault(item.parent_id, []).append(item.pk)
    frontier, height = [folder.pk], 0
    while frontier:
        frontier = [child for node in frontier for child in children.get(node, [])]
        if frontier:
            height += 1
        if depth + height > 20:
            raise ValidationError("Moving this folder would exceed the maximum depth of 20.")
    folder.save()
    record(user, "folder.saved", folder)
    return folder


@transaction.atomic
def delete_folder(user, folder):
    require_member(user, admin=True)
    _lock_folders()
    if folder.children.exists() or folder.files.exists():
        raise ValidationError(
            "Move or delete the contents first. Only empty folders can be deleted."
        )
    record(user, "folder.deleted", folder)
    folder.delete()


@transaction.atomic
def update_file(user, file):
    require_member(user, admin=True)
    File.objects.select_for_update().get(pk=file.pk)
    if file.folder_id:
        Folder.objects.select_for_update().get(pk=file.folder_id)
    file.full_clean()
    file.save(update_fields=["name", "description", "folder", "updated_at"])
    record(user, "file.updated", file)
    return file


@transaction.atomic
def delete_file(user, file):
    require_member(user, admin=True)
    file = File.objects.select_for_update().get(pk=file.pk)
    StorageDeletionJob.objects.get_or_create(storage_key=file.blob.name)
    record(user, "file.deleted", file)
    file.delete()


@transaction.atomic
def toggle_favorite(user, file):
    require_member(user)
    # Lock the account to serialize repeated toggles without duplicate rows.
    get_user_model().objects.select_for_update().get(pk=user.pk)
    favorite, created = Favorite.objects.get_or_create(user=user, file=file)
    if not created:
        favorite.delete()
    return created


def process_deletions(limit=100):
    """Process a bounded outbox batch; a missing object is already deleted."""
    done = failed = 0
    ids = list(
        StorageDeletionJob.objects.filter(next_attempt_at__lte=timezone.now()).values_list(
            "pk", flat=True
        )[:limit]
    )
    for job_id in ids:
        with transaction.atomic():
            job = StorageDeletionJob.objects.select_for_update().filter(pk=job_id).first()
            if not job or job.next_attempt_at > timezone.now():
                continue
            try:
                default_storage.delete(job.storage_key)
            except Exception as exc:
                job.attempts += 1
                job.last_error_code = type(exc).__name__[:80]
                job.next_attempt_at = timezone.now() + timedelta(
                    seconds=min(3600, 30 * 2 ** min(job.attempts, 7))
                )
                job.save()
                logger.warning("Private storage deletion will be retried (%s)", job.last_error_code)
                failed += 1
            else:
                job.delete()
                done += 1
    return done, failed
