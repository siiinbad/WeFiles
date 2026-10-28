"""Integration checks for feature-owned presentation and stable route contracts."""

from django.contrib.staticfiles import finders
from django.template.loader import get_template
from django.test import SimpleTestCase
from django.urls import resolve, reverse

from core.tests.base import WorkspaceTestCase


class FeatureDiscoveryTests(SimpleTestCase):
    def test_templates_and_assets_are_discovered_from_installed_apps(self):
        for feature, page in (
            ("accounts", "profile"),
            ("vault", "list"),
            ("chat", "room"),
            ("notifications", "list"),
            ("activity", "list"),
            ("core", "dashboard"),
        ):
            with self.subTest(feature=feature):
                origin = get_template(f"{feature}/{page}.html").origin.name
                self.assertIn(f"/{feature}/templates/{feature}/", origin)
        for asset in (
            "accounts/avatars/source.png",
            "accounts/js/profile.js",
            "accounts/css/avatars.css",
            "vault/js/upload.js",
            "vault/js/favorites.js",
            "chat/js/room.js",
            "notifications/js/refresh.js",
        ):
            with self.subTest(asset=asset):
                self.assertIsNotNone(finders.find(asset))

    def test_administration_routes_keep_their_public_names(self):
        self.assertEqual(reverse("activity"), "/manage/activity/")
        self.assertEqual(resolve(reverse("activity")).func.view_class.__module__, "activity.views")
        self.assertEqual(reverse("management:admin_dashboard"), "/manage/")
        self.assertEqual(reverse("management:members"), "/manage/members/")


class FeaturePresentationTests(WorkspaceTestCase):
    def test_auth_pages_use_wefiles_templates_instead_of_admin_defaults(self):
        for name, template in (
            ("login", "login"),
            ("password_reset", "password_reset_form"),
            ("password_reset_done", "password_reset_done"),
            ("password_reset_complete", "password_reset_complete"),
        ):
            with self.subTest(name=name):
                response = self.client.get(reverse(f"accounts:{name}"))
                self.assertTemplateUsed(response, f"accounts/registration/{template}.html")
                self.assertContains(response, "WeFiles")
        self.sign_in()
        for name in ("password_change", "password_change_done"):
            response = self.client.get(reverse(f"accounts:{name}"))
            self.assertContains(response, "WeFiles")

    def test_page_enhancements_load_with_the_feature_that_uses_them(self):
        self.sign_in()
        for url, script in (
            ("/accounts/profile/", "accounts/js/profile.js"),
            ("/chat/", "chat/js/room.js"),
            ("/vault/upload/", "vault/js/upload.js"),
            ("/vault/", "vault/js/favorites.js"),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, script)
                self.assertContains(response, "notifications/js/refresh.js")
        response = self.client.get("/dashboard/")
        self.assertNotContains(response, "accounts/js/profile.js")
        self.assertNotContains(response, "chat/js/room.js")
