from core.admin import register_readonly

from .models import File, Folder, StorageDeletionJob

register_readonly(File, ("name", "owner", "folder", "size_bytes", "created_at"))
register_readonly(Folder, ("name", "parent", "creator"))
register_readonly(StorageDeletionJob, ("id", "attempts", "next_attempt_at", "last_error_code"))
