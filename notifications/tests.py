from django.urls import reverse

from core.tests.base import WorkspaceTestCase

from .services import notify


class NotificationTests(WorkspaceTestCase):
    def test_own_notifications_only_and_post_only_reads(self):
        own = notify(self.member, "membership", "Your account is approved.", "/accounts/status/")
        other = notify(self.admin, "registration", "Private admin note")
        self.sign_in()
        response = self.client.get(reverse("notifications:list"))
        self.assertContains(response, "account is approved")
        self.assertNotContains(response, "Private admin note")
        self.assertContains(self.client.get(reverse("notifications:unread")), "1 unread")
        self.assertEqual(
            self.client.get(reverse("notifications:read", args=[own.pk])).status_code, 405
        )
        self.assertEqual(
            self.client.post(reverse("notifications:read", args=[other.pk])).status_code, 404
        )
        self.assertRedirects(
            self.client.post(reverse("notifications:read", args=[own.pk])),
            reverse("notifications:list"),
        )
        own.refresh_from_db()
        self.assertIsNotNone(own.read_at)
        self.assertNotContains(self.client.get(reverse("notifications:unread")), "1 unread")
        notify(self.member, "membership", "Another update")
        self.assertRedirects(
            self.client.post(reverse("notifications:read_all")), reverse("notifications:list")
        )
        self.assertFalse(self.member.notifications.filter(read_at__isnull=True).exists())
        other.refresh_from_db()
        self.assertIsNone(other.read_at)

    def test_destinations_are_internal(self):
        for destination in ("https://evil.example/", "//evil.example/"):
            with self.assertRaises(ValueError):
                notify(self.member, "test", "hello", destination)

    def test_pending_can_see_own_account_updates(self):
        notify(self.pending, "membership", "Your application is being reviewed.")
        self.sign_in(self.pending)
        self.assertContains(self.client.get(reverse("notifications:list")), "being reviewed")
