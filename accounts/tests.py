import re
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import Client
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from activity.models import ActivityEvent
from core.tests.base import PASSWORD, WorkspaceTestCase
from notifications.models import Notification
from vault.models import Folder, StorageDeletionJob

from .backends import EmailBackend
from .forms import ProfileForm, RegistrationForm
from .services import change_membership, delete_account, send_verification, verify_user
from .tokens import verification_token


class AvatarTests(WorkspaceTestCase):
    def test_profile_offers_all_icons_as_native_radio_choices(self):
        from .avatars import AVATAR_CHOICES

        self.sign_in()
        response = self.client.get(reverse("accounts:profile"))
        self.assertContains(response, "Choose your avatar")
        self.assertContains(response, 'class="avatar-radio visually-hidden"', count=30)
        self.assertContains(response, "<fieldset", html=False)
        self.assertEqual(len(AVATAR_CHOICES), 30)
        self.assertEqual(response.context["form"]["avatar_icon"].value(), self.member.avatar_icon)

    def test_selection_saves_without_javascript_and_is_visible_to_crew(self):
        self.admin.avatar_icon = "portrait-01"
        self.admin.save()
        self.sign_in()
        admin_icon = self.admin.avatar_icon
        response = self.client.post(
            reverse("accounts:profile"),
            {
                "username": self.member.username,
                "display_name": "Nora",
                "avatar_icon": "portrait-03",
                "role": "admin",
                "status": "disabled",
            },
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.member.refresh_from_db()
        self.assertEqual(self.member.avatar_icon, "portrait-03")
        self.assertEqual(self.member.role, "member")
        self.assertEqual(self.member.status, "approved")
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.avatar_icon, admin_icon)
        self.assertContains(self.client.get("/dashboard/"), 'data-portrait="portrait-03"')
        from chat.services import send_message

        send_message(self.member, "Meet the crew.")
        self.sign_in(self.admin)
        self.assertContains(self.client.get("/chat/"), 'data-portrait="portrait-03"')
        self.assertContains(self.client.get("/manage/members/"), 'data-portrait="portrait-03"')

    def test_old_profile_submissions_preserve_the_chosen_icon(self):
        self.member.avatar_icon = "portrait-16"
        self.member.save()
        self.sign_in()
        response = self.client.post(
            reverse("accounts:profile"), {"username": "new_name", "display_name": "Crew"}
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.member.refresh_from_db()
        self.assertEqual(self.member.avatar_icon, "portrait-16")

    def test_invalid_icon_is_rejected_without_changing_profile(self):
        previous = self.member.avatar_icon
        self.sign_in()
        response = self.client.post(
            reverse("accounts:profile"),
            {"username": self.member.username, "avatar_icon": "https://evil.example/icon.svg"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("avatar_icon", response.context["form"].errors)
        self.member.refresh_from_db()
        self.assertEqual(self.member.avatar_icon, previous)
        with self.assertRaises(IntegrityError), transaction.atomic():
            get_user_model().objects.filter(pk=self.member.pk).update(avatar_icon="missing-icon")

    def test_original_sheet_regions_are_complete_and_new_defaults_are_valid(self):
        import struct
        from pathlib import Path

        from django.contrib.staticfiles import finders

        from .avatars import (
            AVATAR_KEYS,
            PORTRAIT_REGIONS,
            PORTRAIT_SIZE,
            PORTRAIT_SOURCE,
            random_portrait,
        )

        source = Path(finders.find(PORTRAIT_SOURCE)).read_bytes()
        self.assertEqual(source[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", source[16:24]), PORTRAIT_SIZE)
        self.assertEqual(len(AVATAR_KEYS), 30)
        self.assertEqual(
            sum(width * height for x, y, width, height in PORTRAIT_REGIONS.values()),
            PORTRAIT_SIZE[0] * PORTRAIT_SIZE[1],
        )
        regions = list(PORTRAIT_REGIONS.values())
        for index, (x, y, width, height) in enumerate(regions):
            self.assertTrue(0 <= x < x + width <= PORTRAIT_SIZE[0])
            self.assertTrue(0 <= y < y + height <= PORTRAIT_SIZE[1])
            for xx, yy, ww, hh in regions[index + 1 :]:
                self.assertTrue(x + width <= xx or xx + ww <= x or y + height <= yy or yy + hh <= y)
        self.assertIn(random_portrait(), AVATAR_KEYS)
        self.assertIn(
            get_user_model()
            .objects.create_user("avatar@example.test", PASSWORD, username="avatar_user")
            .avatar_icon,
            AVATAR_KEYS,
        )

    def test_portrait_rendering_keeps_entire_cell_and_padding_at_every_size(self):
        from xml.etree import ElementTree

        from accounts.templatetags.accounts_ui import avatar_art

        from .avatars import AVATAR_KEYS, PORTRAIT_PADDING, PORTRAIT_REGIONS

        for key in AVATAR_KEYS:
            x, y, width, height = PORTRAIT_REGIONS[key]
            art = ElementTree.fromstring(str(avatar_art(key)))
            self.assertEqual(art.attrib["preserveAspectRatio"], "xMidYMid meet")
            self.assertEqual(
                tuple(map(int, art.attrib["viewBox"].split())),
                (
                    x - PORTRAIT_PADDING,
                    y - PORTRAIT_PADDING,
                    width + 2 * PORTRAIT_PADDING,
                    height + 2 * PORTRAIT_PADDING,
                ),
            )
            cell = art.find("svg")
            self.assertEqual(tuple(map(int, cell.attrib["viewBox"].split())), (x, y, width, height))
            self.assertEqual(int(cell.attrib["width"]), width)
            self.assertEqual(int(cell.attrib["height"]), height)
            self.assertEqual(cell.attrib["overflow"], "hidden")
            self.assertIn("avatars/source", cell.find("image").attrib["href"])

    def test_legacy_icon_still_renders_and_legacy_migration_default_is_valid(self):
        from accounts.templatetags.accounts_ui import avatar_art

        from .avatars import LEGACY_AVATAR_CHOICES, random_avatar

        self.assertIn(random_avatar(), [key for key, _ in LEGACY_AVATAR_CHOICES])
        self.assertIn("icons.svg?v=plain-1#avatar-cat", str(avatar_art("avatar-cat")))

    def test_unapproved_member_can_personalize_their_own_profile(self):
        self.sign_in(self.pending)
        self.assertRedirects(
            self.client.post(
                reverse("accounts:profile"),
                {"username": self.pending.username, "avatar_icon": "portrait-07"},
            ),
            reverse("accounts:profile"),
        )
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.avatar_icon, "portrait-07")
        self.assertFalse(self.pending.approved)


class UserTests(WorkspaceTestCase):
    def test_manager_and_properties(self):
        User = get_user_model()
        user = User.objects.create_superuser(" Boss@Example.Test ", PASSWORD, username="boss")
        self.assertEqual(user.email, "boss@example.test")
        self.assertTrue(user.workspace_admin)
        self.assertTrue(user.is_staff)
        user.display_name = "Maya"
        self.assertEqual(user.name, "Maya")
        self.assertEqual(user.initials, "MA")
        self.assertEqual(str(user), "boss")
        with self.assertRaises(ValueError):
            User.objects.create_user("", PASSWORD, username="missing")

    def test_case_insensitive_uniqueness_in_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            get_user_model().objects.create_user("other@example.test", PASSWORD, username="CREW")

    def test_email_backend_and_dummy_hash(self):
        backend = EmailBackend()
        self.assertEqual(
            backend.authenticate(None, username=" CREW@EXAMPLE.TEST ", password=PASSWORD),
            self.member,
        )
        self.assertIsNone(backend.authenticate(None, username=self.member.email, password="wrong"))
        self.assertIsNone(
            backend.authenticate(None, username="missing@example.test", password=PASSWORD)
        )

    def test_registration_and_profile_validation(self):
        form = RegistrationForm(
            {
                "email": "CREW@example.test",
                "username": "CREW",
                "password1": PASSWORD,
                "password2": PASSWORD,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertIn("username", form.errors)
        self.assertFalse(ProfileForm({"username": "ADMIN"}, instance=self.member).is_valid())
        self.assertFalse(ProfileForm({"username": "bad/name"}, instance=self.member).is_valid())


class AuthenticationFlowTests(WorkspaceTestCase):
    def test_register_verify_approval_login_journey(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "email": "new@example.test",
                "username": "new_crew",
                "password1": PASSWORD,
                "password2": PASSWORD,
                "role": "admin",
                "status": "approved",
            },
        )
        self.assertRedirects(response, reverse("accounts:verification_sent"))
        user = get_user_model().objects.get(email="new@example.test")
        self.assertEqual((user.role, user.status), ("member", "pending"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(Notification.objects.filter(recipient=self.admin).exists())
        url = (
            re.search(r"http[^\s]+", mail.outbox[0].body)
            .group()
            .replace("http://127.0.0.1:8000", "")
        )
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertIsNone(get_user_model().objects.get(pk=user.pk).email_verified_at)
        self.assertRedirects(self.client.post(url), reverse("accounts:status"))
        user.refresh_from_db()
        self.assertIsNotNone(user.email_verified_at)
        self.assertRedirects(self.client.get("/vault/"), reverse("accounts:status"))
        change_membership(self.admin, user.pk, "status", "approved")
        self.assertEqual(self.client.get("/vault/").status_code, 200)
        self.assertEqual(self.client.get("/dashboard/").status_code, 200)
        self.assertEqual(self.client.get("/chat/").status_code, 200)
        self.assertEqual(self.client.get("/accounts/logout/").status_code, 405)
        self.assertRedirects(self.client.post("/accounts/logout/"), reverse("accounts:login"))
        self.assertRedirects(
            self.client.post(
                reverse("accounts:login"), {"username": user.email.upper(), "password": PASSWORD}
            ),
            reverse("core:dashboard"),
        )

    def test_login_status_safe_redirect_and_errors(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": self.pending.email, "password": PASSWORD}
        )
        self.assertRedirects(response, reverse("accounts:status"))
        self.client.logout()
        response = self.client.post(
            reverse("accounts:login") + "?next=https://evil.example/",
            {"username": self.member.email, "password": PASSWORD},
        )
        self.assertRedirects(response, reverse("core:dashboard"))
        self.client.logout()
        self.assertContains(
            self.client.post(
                reverse("accounts:login"), {"username": self.member.email, "password": "incorrect"}
            ),
            "Please enter a correct",
        )

    def test_verification_invalid_expired_used_and_resend(self):
        uid = urlsafe_base64_encode(force_bytes(self.pending.pk))
        token = verification_token.make_token(self.pending)
        url = reverse("accounts:verify", args=[uid, token])
        self.assertEqual(
            self.client.post(reverse("accounts:verify", args=["bad", "bad"])).status_code, 400
        )
        with patch.object(
            verification_token, "_now", return_value=verification_token._now() + timedelta(hours=2)
        ):
            self.assertContains(self.client.get(url), "expired")
        verify_user(self.pending)
        verify_user(self.pending)
        self.assertEqual(self.client.post(url).status_code, 400)
        self.sign_in(self.pending)
        self.assertContains(self.client.get(reverse("accounts:resend")), "fresh link")
        self.assertRedirects(
            self.client.post(reverse("accounts:resend")), reverse("accounts:status")
        )
        self.pending.email_verified_at = None
        self.pending.save()
        self.client.post(reverse("accounts:resend"))
        self.assertEqual(len(mail.outbox), 1)

    def test_email_failure_does_not_destroy_account(self):
        with patch("accounts.services.send_mail", side_effect=OSError("offline")):
            self.assertFalse(send_verification(self.pending))
            response = self.client.post(
                reverse("accounts:register"),
                {
                    "email": "fail@example.test",
                    "username": "emailfail",
                    "password1": PASSWORD,
                    "password2": PASSWORD,
                },
                follow=True,
            )
        self.assertContains(response, "could not be sent")
        self.assertTrue(get_user_model().objects.filter(username="emailfail").exists())
        self.sign_in(self.pending)
        with patch("accounts.services.send_mail", return_value=0, side_effect=OSError()):
            self.assertContains(
                self.client.post(reverse("accounts:resend"), follow=True), "could not be sent"
            )

    def test_profile_only_updates_safe_fields(self):
        self.sign_in()
        response = self.client.post(
            reverse("accounts:profile"),
            {"username": "renamed", "display_name": "Nora", "role": "admin", "status": "disabled"},
            follow=True,
        )
        self.assertContains(response, "updated")
        self.member.refresh_from_db()
        self.assertEqual(self.member.role, "member")
        self.assertEqual(self.member.status, "approved")
        self.assertEqual(self.member.display_name, "Nora")
        self.assertContains(self.client.get(reverse("accounts:profile")), "Nora")

    def test_password_reset_generic_and_complete(self):
        url = reverse("accounts:password_reset")
        known = self.client.post(url, {"email": self.member.email}, follow=True)
        unknown = self.client.post(url, {"email": "unknown@example.test"}, follow=True)
        self.assertEqual(known.content, unknown.content)
        self.assertEqual(len(mail.outbox), 1)
        reset_url = (
            re.search(r"http[^\s]+", mail.outbox[0].body)
            .group()
            .replace("http://127.0.0.1:8000", "")
        )
        response = self.client.get(reset_url)
        self.assertEqual(response.status_code, 302)
        confirm_url = response.url
        self.assertContains(self.client.get(confirm_url), "Choose a new password")
        response = self.client.post(
            confirm_url,
            {
                "new_password1": "Different-Wonderful-2026!",
                "new_password2": "Different-Wonderful-2026!",
            },
        )
        self.assertRedirects(response, reverse("accounts:password_reset_complete"))
        self.member.refresh_from_db()
        self.assertTrue(self.member.check_password("Different-Wonderful-2026!"))

    def test_password_reset_delivery_failure_is_generic(self):
        with patch(
            "django.contrib.auth.forms.EmailMultiAlternatives.send",
            side_effect=OSError("mail down"),
        ):
            response = self.client.post(
                reverse("accounts:password_reset"), {"email": self.member.email}, follow=True
            )
        self.assertContains(response, "If an active account")

    def test_change_password_and_csrf(self):
        self.sign_in()
        self.assertEqual(self.client.get(reverse("accounts:password_change")).status_code, 200)
        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": PASSWORD,
                "new_password1": "Changed-Wonderful-2026!",
                "new_password2": "Changed-Wonderful-2026!",
            },
        )
        self.assertRedirects(response, reverse("accounts:password_change_done"))
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.member, backend="accounts.backends.EmailBackend")
        self.assertEqual(
            client.post(reverse("accounts:profile"), {"username": "changed"}).status_code, 403
        )

    def test_login_throttling(self):
        for attempt in range(6):
            response = self.client.post(
                reverse("accounts:login"),
                {
                    "username": self.member.email.upper() if attempt % 2 else self.member.email,
                    "password": "bad",
                },
            )
        self.assertEqual(response.status_code, 429)


class MembershipAndErasureTests(WorkspaceTestCase):
    def test_access_matrix_and_immediate_revocation(self):
        file = self.upload()
        protected = [
            "/dashboard/",
            "/vault/",
            "/vault/saved/",
            "/vault/export.csv",
            "/chat/",
            "/chat/messages/",
            reverse("vault:download", args=[file.pk]),
        ]
        for url in protected:
            self.assertEqual(self.client.get(url).status_code, 302)
        for status in ("pending", "rejected", "disabled", "approved"):
            self.pending.status = status
            self.pending.save()
            self.sign_in(self.pending)
            for url in protected:
                self.assertRedirects(self.client.get(url), reverse("accounts:status"))
        self.sign_in()
        for url in ["/manage/", "/manage/members/", "/manage/activity/"]:
            self.assertEqual(self.client.get(url).status_code, 403)
        change_membership(self.admin, self.member.pk, "status", "disabled")
        self.assertRedirects(self.client.get("/vault/"), reverse("accounts:status"))

    def test_membership_permissions_validation_and_audit(self):
        with self.assertRaises(PermissionDenied):
            change_membership(self.member, self.pending.pk, "role", "admin")
        with self.assertRaises(ValidationError):
            change_membership(self.admin, self.admin.pk, "status", "disabled")
        with self.assertRaises(ValidationError):
            change_membership(self.admin, self.member.pk, "anything", "admin")
        change_membership(self.admin, self.member.pk, "role", "admin")
        self.assertTrue(ActivityEvent.objects.filter(action="member.role_changed").exists())
        self.assertTrue(
            Notification.objects.filter(recipient=self.member, kind="membership").exists()
        )

    def test_admin_pages_and_actions(self):
        self.sign_in(self.admin)
        for url in ["/manage/", "/manage/members/?q=crew&status=approved", "/manage/activity/"]:
            self.assertEqual(self.client.get(url).status_code, 200)
        url = reverse("management:member_action", args=[self.pending.pk, "status"])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertRedirects(
            self.client.post(url, {"value": "approved"}), reverse("management:members")
        )
        self.assertContains(self.client.post(url, {"value": "nonsense"}, follow=True), "valid")
        self.assertEqual(
            self.client.post(
                reverse("management:member_action", args=[self.member.pk, "other"])
            ).status_code,
            404,
        )

    def test_superuser_maintenance_boundaries(self):
        user = get_user_model().objects.create_superuser(
            "root@example.test", PASSWORD, username="root"
        )
        change_membership(self.admin, user.pk, "role", "member")
        user.refresh_from_db()
        self.assertEqual(user.role, "member")
        self.assertFalse(user.workspace_admin)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        with self.assertRaises(ValidationError):
            change_membership(self.admin, user.pk, "status", "disabled")
        self.sign_in(user)
        self.assertEqual(self.client.get("/manage/").status_code, 403)
        self.assertEqual(self.client.get("/manage/members/").status_code, 403)
        self.assertEqual(self.client.get("/vault/").status_code, 200)
        self.assertEqual(self.client.get("/admin/").status_code, 200)
        self.assertEqual(self.client.get("/admin/accounts/user/").status_code, 200)
        self.assertEqual(
            self.client.get(f"/admin/accounts/user/{self.member.pk}/change/").status_code, 200
        )
        self.assertEqual(
            self.client.get(f"/admin/accounts/user/{self.member.pk}/delete/").status_code, 403
        )
        self.assertEqual(self.client.get("/admin/vault/file/add/").status_code, 403)
        user.status = "disabled"
        user.save()
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    def test_admin_can_be_changed_to_member_and_promoted_again(self):
        self.member.role = "admin"
        self.member.save()
        self.sign_in(self.member)
        self.assertEqual(self.client.get("/manage/").status_code, 200)

        change_membership(self.admin, self.member.pk, "role", "member")
        self.member.refresh_from_db()
        self.assertEqual(self.member.role, "member")
        self.assertEqual(self.client.get("/manage/").status_code, 403)
        self.assertEqual(self.client.get("/vault/").status_code, 200)
        self.assertTrue(
            ActivityEvent.objects.filter(
                actor=self.admin, action="member.role_changed", object_id=self.member.pk
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.member, text="Your role is now Member."
            ).exists()
        )

        change_membership(self.admin, self.member.pk, "role", "admin")
        self.assertEqual(self.client.get("/manage/").status_code, 200)

    def test_self_demotion_redirects_to_an_accessible_page_and_revokes_access(self):
        self.member.role = "admin"
        self.member.save()
        self.sign_in(self.admin)
        response = self.client.post(
            reverse("management:member_action", args=[self.admin.pk, "role"]),
            {"value": "member"},
        )
        self.assertRedirects(response, reverse("core:dashboard"))
        self.assertEqual(self.client.get("/manage/members/").status_code, 403)
        # The service reloads authority, even if a caller retained the old object.
        with self.assertRaises(PermissionDenied):
            change_membership(self.admin, self.admin.pk, "role", "admin")
        self.assertEqual(
            self.client.post(
                reverse("management:member_action", args=[self.admin.pk, "role"]),
                {"value": "admin"},
            ).status_code,
            403,
        )

    def test_role_controls_include_the_signed_in_admin_and_maintenance_superuser(self):
        root = get_user_model().objects.create_superuser(
            "root@example.test", PASSWORD, username="root"
        )
        self.sign_in(self.admin)
        response = self.client.get(reverse("management:members"))
        for user in (self.admin, root, self.member):
            self.assertContains(response, f'for="role-{user.pk}"')
            self.assertContains(
                response,
                f'action="{reverse("management:member_action", args=[user.pk, "role"])}"',
            )
        self.assertNotContains(response, f'for="status-{self.admin.pk}"')
        self.assertNotContains(response, f'for="status-{root.pk}"')

    def test_last_workspace_admin_cannot_demote_even_with_a_maintenance_member(self):
        root = get_user_model().objects.create_superuser(
            "root@example.test", PASSWORD, username="root"
        )
        root.role = "member"
        root.save()
        self.pending.role = "admin"
        self.pending.save()
        self.sign_in(self.admin)
        response = self.client.post(
            reverse("management:member_action", args=[self.admin.pk, "role"]),
            {"value": "member"},
            follow=True,
        )
        self.assertContains(response, "At least one approved administrator must remain.")
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, "admin")
        self.assertFalse(ActivityEvent.objects.filter(action="member.role_changed").exists())

    def test_last_admin_protected(self):
        with self.assertRaises(ValidationError):
            delete_account(self.admin)
        self.sign_in(self.admin)
        self.assertContains(
            self.client.post(reverse("accounts:delete"), {"password": PASSWORD, "confirm": "on"}),
            "Appoint another",
        )

    def test_account_erasure_preserves_shared_folders_and_retries_bytes(self):
        folder = Folder.objects.create(creator=self.member, name="Shared")
        file = self.upload(folder=folder)
        foreign_file = self.upload(user=self.admin, name="other.txt", folder=folder)
        key = file.blob.name
        from chat.services import send_message

        send_message(self.member, "Hello")
        self.sign_in()
        self.assertEqual(self.client.get(reverse("accounts:delete")).status_code, 200)
        self.assertContains(
            self.client.post(reverse("accounts:delete"), {"password": "wrong", "confirm": "on"}),
            "did not match",
        )
        with patch("vault.services.default_storage.delete", side_effect=OSError("offline")):
            response = self.client.post(
                reverse("accounts:delete"), {"password": PASSWORD, "confirm": "on"}
            )
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertFalse(get_user_model().objects.filter(pk=self.member.pk).exists())
        folder.refresh_from_db()
        self.assertIsNone(folder.creator_id)
        self.assertTrue(folder.files.filter(pk=foreign_file.pk).exists())
        self.assertFalse(folder.files.filter(pk=file.pk).exists())
        self.assertTrue(StorageDeletionJob.objects.filter(storage_key=key).exists())
        self.assertFalse(ActivityEvent.objects.filter(actor_id=self.member.pk).exists())
