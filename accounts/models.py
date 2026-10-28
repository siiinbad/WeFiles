"""The user model is installed before the first migration."""

import uuid

from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from .avatars import STORED_AVATAR_CHOICES, STORED_AVATAR_KEYS, random_portrait


class WeFilesUserManager(UserManager):
    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = email.strip().lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.update(is_staff=True, is_superuser=True, role="admin", status="approved")
        extra_fields.setdefault("email_verified_at", timezone.now())
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        MEMBER = "member", "Member"
        ADMIN = "admin", "Administrator"

    class Status(models.TextChoices):
        PENDING = "pending", "Awaiting approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Not approved"
        DISABLED = "disabled", "Disabled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    username = models.CharField(
        max_length=20,
        unique=True,
        validators=[
            RegexValidator(r"^[a-zA-Z0-9_]{3,20}$", "Use 3–20 letters, numbers, or underscores.")
        ],
    )
    display_name = models.CharField(max_length=80, blank=True)
    avatar_icon = models.CharField(
        max_length=32, choices=STORED_AVATAR_CHOICES, default=random_portrait
    )
    role = models.CharField(max_length=10, choices=Role, default=Role.MEMBER)
    status = models.CharField(max_length=10, choices=Status, default=Status.PENDING, db_index=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]
    objects = WeFilesUserManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(avatar_icon__in=STORED_AVATAR_KEYS), name="valid_user_avatar"
            ),
            models.UniqueConstraint(Lower("email"), name="user_email_ci"),
            models.UniqueConstraint(Lower("username"), name="user_username_ci"),
            models.CheckConstraint(
                condition=models.Q(role__in=["member", "admin"]), name="valid_user_role"
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["pending", "approved", "rejected", "disabled"]),
                name="valid_user_status",
            ),
        ]

    @property
    def approved(self):
        return (
            self.is_active and self.status == self.Status.APPROVED and bool(self.email_verified_at)
        )

    @property
    def workspace_admin(self):
        return self.approved and self.role == self.Role.ADMIN

    @property
    def name(self):
        return self.display_name or self.username

    @property
    def initials(self):
        return self.name[:2].upper()

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username
