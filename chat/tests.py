from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse

from core.tests.base import WorkspaceTestCase

from .models import ChatMessage
from .services import send_message


class ChatTests(WorkspaceTestCase):
    def test_validation_and_approval(self):
        for content in (" ", "x" * 2001):
            with self.assertRaises(ValidationError):
                send_message(self.member, content)
        with self.assertRaises(PermissionDenied):
            send_message(self.pending, "Hello")
        with self.assertRaises(IntegrityError), transaction.atomic():
            ChatMessage.objects.create(sender=self.member, content=" " * 2)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ChatMessage.objects.create(sender=self.member, content="x" * 2001)

    def test_send_binds_sender_and_escapes_content(self):
        self.sign_in()
        response = self.client.post(
            reverse("chat:send"),
            {"content": "  <script>alert('hello')</script>  ", "sender": self.admin.pk},
            follow=True,
        )
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert")
        message = ChatMessage.objects.get()
        self.assertEqual(message.sender, self.member)
        self.assertEqual(message.content, "<script>alert('hello')</script>")
        self.assertEqual(self.client.post(reverse("chat:send"), {"content": " "}).status_code, 400)
        self.assertEqual(self.client.get(reverse("chat:send")).status_code, 405)

    def test_history_loads_latest_50_and_older_messages(self):
        for i in range(55):
            send_message(self.member, f"Message {i:02d}")
        self.sign_in()
        response = self.client.get(reverse("chat:room"))
        self.assertEqual(len(response.context["chat_messages"]), 50)
        self.assertEqual(response.context["chat_messages"][0].content, "Message 05")
        self.assertEqual(response.context["chat_messages"][-1].content, "Message 54")
        self.assertContains(response, "Older messages")
        older = self.client.get(reverse("chat:room") + "?page=2")
        self.assertEqual(len(older.context["chat_messages"]), 5)
        self.assertNotContains(older, 'id="conversation" hx-get')
        self.assertContains(older, "Newer messages")
        self.assertContains(self.client.get(reverse("chat:messages")), "Message 54")

    def test_post_throttling(self):
        self.sign_in()
        for _ in range(21):
            response = self.client.post(reverse("chat:send"), {"content": "A quick note"})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "60")
        self.assertEqual(ChatMessage.objects.count(), 20)

    def test_unchanged_poll_does_not_replace_history(self):
        message = send_message(self.member, "Keep the scroll position.")
        self.sign_in()
        response = self.client.get(
            reverse("chat:messages"),
            HTTP_X_WEFILES_LATEST=str(message.pk),
            HTTP_X_WEFILES_COUNT="1",
        )
        self.assertEqual(response.status_code, 204)
        send_message(self.admin, "A new message")
        response = self.client.get(
            reverse("chat:messages"),
            HTTP_X_WEFILES_LATEST=str(message.pk),
            HTTP_X_WEFILES_COUNT="1",
        )
        self.assertContains(response, "A new message")
