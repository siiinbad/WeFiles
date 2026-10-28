from datetime import timedelta
from unittest.mock import patch

from django.db import connection
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from core import views
from core.models import RateLimitBucket
from core.services import consume_limit
from core.tests.base import WorkspaceTestCase


class CoreTests(WorkspaceTestCase):
    def test_home_status_and_public_privacy(self):
        self.assertRedirects(self.client.get("/"), reverse("accounts:login"))
        self.assertContains(self.client.get("/privacy/"), "Privacy &amp; data")
        self.sign_in(self.pending)
        self.assertRedirects(self.client.get("/"), reverse("accounts:status"))
        self.sign_in()
        self.assertRedirects(self.client.get("/"), reverse("core:dashboard"))

    def test_health_failure_and_error_pages(self):
        self.assertEqual(self.client.get("/health/live/").json()["status"], "ok")
        self.assertEqual(self.client.get("/health/ready/").status_code, 200)
        with patch("core.views.connection.cursor", side_effect=OSError("db offline")):
            self.assertEqual(self.client.get("/health/ready/").status_code, 503)
        request = RequestFactory().get("/")
        from django.contrib.auth.models import AnonymousUser
        from django.contrib.messages.storage.fallback import FallbackStorage

        request.user = AnonymousUser()
        request.session = {}
        request._messages = FallbackStorage(request)
        for code in (400, 403, 404):
            self.assertEqual(getattr(views, f"error_{code}")(request).status_code, code)
        with patch("core.views.connection.cursor", side_effect=OSError()):
            self.assertEqual(views.error_500(request).status_code, 500)

    def test_headers_and_template_labels(self):
        self.sign_in()
        response = self.client.get("/dashboard/")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertIn("frame-ancestors 'none'", response["Content-Security-Policy"])
        self.assertIn("noindex", response["X-Robots-Tag"])
        self.assertContains(response, 'href="#main"')
        self.assertContains(response, 'aria-label="Main navigation"')
        self.assertContains(response, "WeFiles")
        self.assertNotContains(response, "Liki")

    def test_private_htmx_redirects_use_full_page_navigation(self):
        self.sign_in(self.pending)
        response = self.client.get("/chat/messages/", HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["HX-Redirect"], reverse("accounts:status"))
        self.assertEqual(response.content, b"")

    def test_rate_limits_expire_and_hide_identity(self):
        self.assertTrue(consume_limit("person@example.test", 1, 60))
        self.assertFalse(consume_limit("person@example.test", 1, 60))
        self.assertNotIn("person", RateLimitBucket.objects.get().key)
        RateLimitBucket.objects.update(started_at=timezone.now() - timedelta(seconds=61))
        self.assertTrue(consume_limit("person@example.test", 1, 60))

    def test_dashboard_and_vault_query_budget_stays_bounded(self):
        for i in range(30):
            self.upload(name=f"Document-{i}.txt")
        self.sign_in()
        with CaptureQueriesContext(connection) as dashboard_queries:
            response = self.client.get("/dashboard/")
            self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(dashboard_queries), 12)
        with CaptureQueriesContext(connection) as vault_queries:
            response = self.client.get("/vault/")
            self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(vault_queries), 12)
