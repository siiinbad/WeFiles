"""Create fictional local-only data, without fixed/default credentials."""

import os
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from chat.models import ChatMessage
from chat.services import send_message
from notifications.services import notify
from vault.models import File, Folder
from vault.services import save_folder, toggle_favorite, upload_file


class Command(BaseCommand):
    help = "Seed an idempotent, fictional WeFiles workspace (DEBUG only)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--extra-files",
            type=int,
            default=0,
            help="Additional real, tiny files for scale checks.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo data can only be created with DEBUG=True.")
        password = os.environ.get("DEMO_PASSWORD") or secrets.token_urlsafe(18)
        User = get_user_model()
        people = [
            ("demo@wefiles.example", "alex", "Alex Morgan", "admin"),
            ("maya@wefiles.example", "maya", "Maya Chen", "member"),
            ("leo@wefiles.example", "leo", "Leo Santos", "member"),
            ("nora@wefiles.example", "nora", "Nora Patel", "member"),
        ]
        users = []
        new_accounts = []
        for email, username, display_name, role in people:
            user = User.objects.filter(email=email).first()
            if user is None:
                user = User.objects.create_user(
                    email,
                    password,
                    username=username,
                    display_name=display_name,
                    role=role,
                    status="approved",
                    email_verified_at=timezone.now(),
                )
                new_accounts.append(email)
            users.append(user)
        admin, maya, leo, nora = users
        folders = []
        for name in ("Getting started", "Projects", "Brand & design", "Crew resources"):
            folder = Folder.objects.filter(name=name, parent=None).first()
            folders.append(folder or save_folder(admin, Folder(name=name)))
        samples = [
            (
                "Welcome to the crew.md",
                b"# Welcome to WeFiles\n\nA shared home for your files and your people.\n\n1. Find a useful file.\n2. Save it for later.\n3. Say hello in crew chat.\n",
                "text/markdown",
                maya,
                folders[0],
                "A friendly first stop for every new crew member.",
            ),
            (
                "Project roadmap.csv",
                b"Milestone,Owner,Status\nDiscovery,Maya,Complete\nDesign,Alex,In progress\nBuild,Leo,Upcoming\nReview,Nora,Upcoming\n",
                "text/csv",
                leo,
                folders[1],
                "A small, shared view of where we are headed.",
            ),
            (
                "Design principles.txt",
                b"Make it useful.\nKeep it clear.\nLeave room for everyone.\nUse consistent patterns.\nDesign for the smallest screen first.\n",
                "text/plain",
                nora,
                folders[2],
                "Five principles for thoughtful work.",
            ),
            (
                "Crew handbook.md",
                b"# Crew handbook\n\nBe generous with context.\nName files clearly.\nKeep personal data out of shared documents.\nUse chat for quick updates.\n",
                "text/markdown",
                maya,
                None,
                "A few habits that make working together easier.",
            ),
            (
                "Team availability.csv",
                b"Name,Monday,Tuesday,Wednesday\nAlex,AM,PM,AM\nMaya,PM,AM,PM\nLeo,AM,AM,PM\nNora,PM,PM,AM\n",
                "text/csv",
                admin,
                None,
                "Fictional sample availability for planning.",
            ),
        ]
        for index, (name, content, mime, owner, folder, description) in enumerate(samples):
            if not File.objects.filter(owner=owner, name=name).exists():
                file = upload_file(
                    owner, SimpleUploadedFile(name, content, content_type=mime), folder, description
                )
                File.objects.filter(pk=file.pk).update(
                    created_at=timezone.now() - timedelta(hours=index * 3 + 1)
                )
        if not ChatMessage.objects.filter(sender=maya).exists():
            for sender, content in [
                (
                    maya,
                    "The welcome guide is in the vault. A good place to start if you’re new here 👋",
                ),
                (leo, "Roadmap is updated. I added a quick overview of the next milestones."),
                (nora, "Love having everything in one place. Thanks for keeping it organized!"),
            ]:
                send_message(sender, content)
        if not admin.notifications.exists():
            notify(admin, "workspace", "Welcome to your WeFiles workspace.", "/dashboard/")
        first = File.objects.filter(name="Welcome to the crew.md").first()
        if first and not first.favorites.filter(user=admin).exists():
            toggle_favorite(admin, first)
        for index in range(max(0, min(options["extra_files"], 100000))):
            name = f"Scale sample {index:05d}.txt"
            if not File.objects.filter(name=name, owner=admin).exists():
                upload_file(
                    admin,
                    SimpleUploadedFile(
                        name, b"Synthetic performance fixture.\n", content_type="text/plain"
                    ),
                )
        self.stdout.write(self.style.SUCCESS("WeFiles demo workspace is ready."))
        if new_accounts:
            self.stdout.write("New demo accounts: " + ", ".join(new_accounts))
            self.stdout.write(
                "Generated demo password: " + password
                if "DEMO_PASSWORD" not in os.environ
                else "Password: supplied through DEMO_PASSWORD."
            )
        else:
            self.stdout.write("Existing account passwords were preserved.")
