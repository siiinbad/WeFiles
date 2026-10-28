import uuid
from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from core.tests.base import WorkspaceTestCase

from .forms import UploadForm
from .models import File, Folder, StorageDeletionJob, validate_name
from .selectors import breadcrumbs, file_query
from .services import (
    delete_file,
    delete_folder,
    process_deletions,
    save_folder,
    toggle_favorite,
    update_file,
    upload_file,
)
from .views import csv_safe


class FolderTests(WorkspaceTestCase):
    def test_moving_subtree_cannot_exceed_depth_limit(self):
        root = save_folder(self.member, Folder(name="Root"))
        deepest = root
        for i in range(20):
            deepest = save_folder(self.member, Folder(name=f"Level {i}", parent=deepest))
        move = save_folder(self.member, Folder(name="Move"))
        save_folder(self.member, Folder(name="Nested", parent=move))
        move.parent = deepest.parent
        with self.assertRaises(ValidationError):
            save_folder(self.admin, move)

    def test_unique_root_and_sibling_names(self):
        root = save_folder(self.member, Folder(name="Guides"))
        child = save_folder(self.member, Folder(name="Crew", parent=root))
        with self.assertRaises(ValidationError):
            save_folder(self.member, Folder(name="GUIDES"))
        with self.assertRaises(ValidationError):
            save_folder(self.member, Folder(name="crew", parent=root))
        self.assertEqual(breadcrumbs(child), [root, child])
        self.assertEqual(str(root), "Guides")

    def test_invalid_names_and_cycles(self):
        for name in ("", " ", ".", "..", "a/b", "a\\b", "bad\nname"):
            with self.assertRaises(ValidationError):
                validate_name(name)
        root = save_folder(self.member, Folder(name="One"))
        child = save_folder(self.member, Folder(name="Two", parent=root))
        root.parent = child
        with self.assertRaises(ValidationError):
            save_folder(self.admin, root)
        child.parent = child
        with self.assertRaises(ValidationError):
            child.clean()

    def test_member_update_and_nonempty_delete_denied(self):
        folder = save_folder(self.member, Folder(name="Useful"))
        with self.assertRaises(PermissionDenied):
            save_folder(self.member, folder)
        file = self.upload(folder=folder)
        with self.assertRaises(ValidationError):
            delete_folder(self.admin, folder)
        delete_file(self.admin, file)
        save_folder(self.member, Folder(name="Child", parent=folder))
        with self.assertRaises(ValidationError):
            delete_folder(self.admin, folder)
        with self.assertRaises(PermissionDenied):
            delete_folder(self.member, folder)

    def test_folder_create_edit_delete_views(self):
        self.sign_in()
        self.assertEqual(self.client.get(reverse("vault:folder_create")).status_code, 200)
        response = self.client.post(reverse("vault:folder_create"), {"name": "Source"})
        folder = Folder.objects.get(name="Source")
        self.assertRedirects(response, reverse("vault:folder", args=[folder.pk]))
        self.assertEqual(
            self.client.get(reverse("vault:folder_edit", args=[folder.pk])).status_code, 403
        )
        self.sign_in(self.admin)
        self.assertEqual(
            self.client.get(reverse("vault:folder_edit", args=[folder.pk])).status_code, 200
        )
        self.assertRedirects(
            self.client.post(reverse("vault:folder_edit", args=[folder.pk]), {"name": "Renamed"}),
            reverse("vault:folder", args=[folder.pk]),
        )
        url = reverse("vault:folder_delete", args=[folder.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertContains(self.client.post(url), "confirm")
        self.upload(folder=folder)
        self.assertContains(self.client.post(url, {"confirm": "yes"}), "Only empty")
        empty = save_folder(self.member, Folder(name="Empty"))
        self.assertRedirects(
            self.client.post(reverse("vault:folder_delete", args=[empty.pk]), {"confirm": "yes"}),
            reverse("vault:list"),
        )


class FileTests(WorkspaceTestCase):
    def test_invalid_destination_parameters_are_404(self):
        self.sign_in()
        for url in (
            "/vault/upload/?folder=bad",
            "/vault/folders/new/?parent=bad",
            "/vault/export.csv?folder=bad",
        ):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_file_upload_private_path_download_and_metadata(self):
        self.sign_in()
        self.assertEqual(self.client.get(reverse("vault:upload")).status_code, 200)
        response = self.client.post(
            reverse("vault:upload"),
            {
                "file": SimpleUploadedFile(
                    "Guide.txt", b"Good information", content_type="text/plain"
                ),
                "description": "Start here",
            },
        )
        file = File.objects.get()
        self.assertRedirects(response, reverse("vault:detail", args=[file.pk]))
        self.assertNotIn("Guide", file.blob.name)
        self.assertTrue(file.blob.name.startswith("objects/"))
        self.assertEqual(file.size_bytes, 16)
        response = self.client.get(reverse("vault:download", args=[file.pk]))
        self.assertEqual(b"".join(response.streaming_content), b"Good information")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(response["Content-Type"], "application/octet-stream")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(self.client.get("/private-media/" + file.blob.name).status_code, 404)

    def test_upload_validation(self):
        with override_settings(MAX_UPLOAD_BYTES=4):
            form = UploadForm(files={"file": SimpleUploadedFile("big.txt", b"12345")})
            self.assertFalse(form.is_valid())
            with self.assertRaises(ValidationError):
                upload_file(self.member, SimpleUploadedFile("big.txt", b"12345"))
        self.assertFalse(
            UploadForm(files={"file": SimpleUploadedFile("empty.txt", b"")}).is_valid()
        )
        with self.assertRaises(PermissionDenied):
            self.upload(user=self.pending)

    def test_upload_failure_compensates_and_queues_cleanup(self):
        with patch(
            "activity.services.ActivityEvent.objects.create", side_effect=RuntimeError("db fail")
        ):
            with self.assertRaises(RuntimeError):
                self.upload()
        self.assertFalse(File.objects.exists())
        with (
            patch("vault.services.record", side_effect=RuntimeError("db fail")),
            patch(
                "django.core.files.storage.filesystem.FileSystemStorage.delete",
                side_effect=OSError("offline"),
            ),
        ):
            with self.assertRaises(RuntimeError):
                self.upload()
        self.assertTrue(StorageDeletionJob.objects.exists())

    def test_upload_storage_failure_shows_friendly_error(self):
        self.sign_in()
        with patch("vault.views.upload_file", side_effect=OSError("offline")):
            response = self.client.post(
                reverse("vault:upload"), {"file": SimpleUploadedFile("notes.txt", b"hello")}
            )
        self.assertContains(response, "could not be stored")
        with patch("vault.views.upload_file", side_effect=ValidationError("bad destination")):
            response = self.client.post(
                reverse("vault:upload"), {"file": SimpleUploadedFile("notes.txt", b"hello")}
            )
        self.assertContains(response, "bad destination")

    def test_edit_and_delete_permissions_and_service(self):
        file = self.upload()
        old_key = file.blob.name
        file.name = "new.txt"
        with self.assertRaises(PermissionDenied):
            update_file(self.member, file)
        with self.assertRaises(PermissionDenied):
            delete_file(self.member, file)
        update_file(self.admin, file)
        self.assertEqual(file.blob.name, old_key)
        self.sign_in()
        for name in ("edit", "delete"):
            self.assertEqual(
                self.client.post(
                    reverse("vault:" + name, args=[file.pk]),
                    {"name": "hacked.txt", "confirm": "yes"},
                ).status_code,
                403,
            )
        self.sign_in(self.admin)
        self.assertEqual(self.client.get(reverse("vault:edit", args=[file.pk])).status_code, 200)
        folder = save_folder(self.member, Folder(name="Move here"))
        response = self.client.post(
            reverse("vault:edit", args=[file.pk]),
            {"name": "moved.txt", "description": "Updated", "folder": folder.pk},
        )
        self.assertRedirects(response, reverse("vault:detail", args=[file.pk]))
        file.refresh_from_db()
        self.assertEqual(file.folder, folder)
        response = self.client.post(reverse("vault:delete", args=[file.pk]), {"confirm": "yes"})
        self.assertRedirects(response, reverse("vault:list"))
        self.assertFalse(File.objects.filter(pk=file.pk).exists())
        self.assertFalse(file.blob.storage.exists(old_key))

    def test_missing_download_and_unknown_file(self):
        file = self.upload()
        file.blob.delete(save=False)
        self.sign_in()
        self.assertEqual(
            self.client.get(reverse("vault:download", args=[file.pk])).status_code, 404
        )
        self.assertEqual(
            self.client.get(reverse("vault:detail", args=[uuid.uuid4()])).status_code, 404
        )

    def test_storage_deletion_retry(self):
        file = self.upload()
        delete_file(self.admin, file)
        with patch("vault.services.default_storage.delete", side_effect=OSError("offline")):
            self.assertEqual(process_deletions(), (0, 1))
        job = StorageDeletionJob.objects.get()
        self.assertEqual(job.attempts, 1)
        self.assertEqual(job.last_error_code, "OSError")
        self.assertEqual(process_deletions(), (0, 0))
        StorageDeletionJob.objects.update(next_attempt_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(process_deletions(), (1, 0))
        self.assertFalse(StorageDeletionJob.objects.exists())


class SearchAndSavedTests(WorkspaceTestCase):
    def setUp(self):
        self.root_file = self.upload(name="Roadmap.txt")
        self.folder = save_folder(self.member, Folder(name="Docs"))
        self.nested = self.upload(name="Budget.csv", folder=self.folder)
        self.sign_in()

    def test_search_folder_scope_and_types(self):
        self.assertEqual(list(file_query(self.member, {})[0]), [self.root_file])
        self.assertEqual(list(file_query(self.member, {"q": "Budget"})[0]), [self.nested])
        self.assertEqual(list(file_query(self.member, {"q": "Roadmap"}, self.folder)[0]), [])
        self.assertEqual(
            list(file_query(self.member, {"kind": "sheet"}, self.folder)[0]), [self.nested]
        )
        for kind in ("pdf", "image"):
            self.assertFalse(file_query(self.member, {"kind": kind})[0].exists())
        self.assertTrue(file_query(self.member, {"kind": "document"})[0].exists())
        for sort in ("oldest", "name", "size", "invalid"):
            self.assertEqual(file_query(self.member, {"sort": sort})[0].count(), 1)
        self.assertEqual(file_query(self.member, {"owner": str(self.admin.pk)})[0].count(), 0)
        self.assertEqual(self.client.get("/vault/?owner=bad&sort=bad&kind=bad").status_code, 200)

    def test_saves_private_idempotent_and_htmx(self):
        self.assertTrue(toggle_favorite(self.member, self.nested))
        self.assertEqual(list(file_query(self.member, {}, saved_only=True)[0]), [self.nested])
        self.assertFalse(file_query(self.admin, {}, saved_only=True)[0].exists())
        self.assertFalse(toggle_favorite(self.member, self.nested))
        url = reverse("vault:favorite", args=[self.nested.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        response = self.client.post(url, HTTP_HX_REQUEST="true")
        self.assertContains(response, 'aria-pressed="true"')
        self.assertContains(self.client.get(reverse("vault:saved")), "Budget.csv")
        self.assertRedirects(self.client.post(url), reverse("vault:detail", args=[self.nested.pk]))

    def test_search_ui_and_pagination(self):
        self.assertContains(self.client.get("/vault/?q=Budget"), "Budget.csv")
        self.assertNotContains(self.client.get("/vault/?q=Budget"), "Roadmap.txt")
        self.assertContains(
            self.client.get(reverse("vault:folder", args=[self.folder.pk])), "Budget.csv"
        )
        for i in range(26):
            self.upload(name=f"File-{i}.txt")
        response = self.client.get("/vault/?sort=name&page=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["files"]), 2)
        self.assertContains(response, "Previous")
        self.assertEqual(self.client.get("/vault/?page=nonsense").status_code, 404)

    def test_csv_filters_and_formula_injection(self):
        self.nested.name = "=DANGEROUS.csv"
        self.nested.save()
        response = self.client.get("/vault/export.csv?q=DANGEROUS")
        data = b"".join(response.streaming_content).decode()
        self.assertIn("'=DANGEROUS.csv", data)
        self.assertNotIn("Roadmap", data)
        self.assertNotIn("objects/", data)
        self.assertNotIn(self.member.email, data)
        for value in ("=A1", "+1", "-1", "@SUM", "  =A1", "\tvalue", "\rline", "\nline"):
            self.assertTrue(csv_safe(value).startswith("'"))
        self.assertEqual(csv_safe("normal"), "normal")
