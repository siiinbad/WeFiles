import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from vault.services import upload_file

PASSWORD = "Crew-Wonderful-2026!"


class WorkspaceTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_media = tempfile.TemporaryDirectory()
        cls.media_override = override_settings(MEDIA_ROOT=cls.temp_media.name)
        cls.media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.media_override.disable()
        cls.temp_media.cleanup()

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user(
            "admin@example.test",
            PASSWORD,
            username="admin",
            role="admin",
            status="approved",
            email_verified_at=timezone.now(),
        )
        cls.member = User.objects.create_user(
            "crew@example.test",
            PASSWORD,
            username="crew",
            status="approved",
            email_verified_at=timezone.now(),
        )
        cls.pending = User.objects.create_user("pending@example.test", PASSWORD, username="pending")

    def sign_in(self, user=None):
        self.client.force_login(user or self.member, backend="accounts.backends.EmailBackend")

    def upload(self, user=None, name="notes.txt", folder=None):
        return upload_file(
            user or self.member,
            SimpleUploadedFile(name, b"A useful shared document.\n", content_type="text/plain"),
            folder,
        )
