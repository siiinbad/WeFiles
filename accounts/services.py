"""Explicit account mutations keep privileges out of ordinary model forms."""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from activity.models import ActivityEvent
from activity.services import record
from notifications.services import notify

from .tokens import verification_token

logger = logging.getLogger(__name__)


def send_verification(user):
    path = reverse(
        "accounts:verify",
        kwargs={
            "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": verification_token.make_token(user),
        },
    )
    body = render_to_string(
        "accounts/registration/verification_email.txt",
        {"url": settings.SITE_URL + path, "user": user},
    )
    try:
        send_mail("Verify your WeFiles email", body, settings.DEFAULT_FROM_EMAIL, [user.email])
    except Exception:
        logger.exception("Verification email delivery failed")
        return False
    return True


@transaction.atomic
def register_user(form):
    user = form.save(commit=False)
    user.role, user.status = "member", "pending"
    user.save()
    admins = get_user_model().objects.filter(
        role="admin", status="approved", is_active=True, email_verified_at__isnull=False
    )
    for admin in admins:
        notify(
            admin,
            "registration",
            "A new member is waiting for approval.",
            reverse("management:members"),
        )
    record(user, "account.registered", user)
    return user


def _lock_admins():
    """Serialize membership changes on the approved administrator rows."""
    return list(
        get_user_model()
        .objects.select_for_update()
        .filter(role="admin", status="approved", is_active=True, email_verified_at__isnull=False)
        .order_by("pk")
    )


@transaction.atomic
def change_membership(actor, target_id, field, value):
    """Change workspace access without modifying Django maintenance privileges.

    Administrators may change their own workspace role, provided another
    approved administrator remains. Self status changes remain unavailable.
    """
    admins = _lock_admins()
    actor = get_user_model().objects.get(pk=actor.pk)
    if not actor.workspace_admin:
        raise PermissionDenied
    target = get_user_model().objects.select_for_update().get(pk=target_id)
    choices = {
        "role": ["member", "admin"],
        "status": ["pending", "approved", "rejected", "disabled"],
    }
    if field not in choices or value not in choices[field]:
        raise ValidationError("Choose a valid role or status.")
    if actor.pk == target.pk and field == "status":
        raise ValidationError("You cannot change your own approval status.")
    if target.is_superuser and field == "status":
        raise ValidationError(
            "Maintenance superuser status must be managed through the maintenance tools."
        )
    if (
        target.workspace_admin
        and len(admins) <= 1
        and ((field == "role" and value != "admin") or (field == "status" and value != "approved"))
    ):
        raise ValidationError("At least one approved administrator must remain.")
    setattr(target, field, value)
    target.save(update_fields=[field, "updated_at"])
    record(actor, f"member.{field}_changed", target)
    notify(
        target,
        "membership",
        f"Your {field} is now {getattr(target, 'get_' + field + '_display')()}.",
        reverse("accounts:status"),
    )
    return target


@transaction.atomic
def delete_account(user):
    """Erase account-owned data and enqueue private bytes for retryable removal."""
    from axes.models import AccessAttempt, AccessFailureLog, AccessLog

    from vault.models import StorageDeletionJob

    admins = _lock_admins()
    user = get_user_model().objects.select_for_update().get(pk=user.pk)
    if user.workspace_admin and len(admins) <= 1:
        raise ValidationError(
            "Appoint another verified, approved administrator before deleting your account."
        )
    keys = list(user.files.values_list("blob", flat=True))
    StorageDeletionJob.objects.bulk_create(
        [StorageDeletionJob(storage_key=key) for key in keys], ignore_conflicts=True
    )
    ActivityEvent.objects.filter(Q(actor=user) | Q(object_type="user", object_id=user.pk)).update(
        actor=None, object_label="Deleted account"
    )
    ActivityEvent.objects.filter(object_id__in=user.files.values("pk")).update(
        object_label="Deleted file"
    )
    for model in (AccessAttempt, AccessFailureLog, AccessLog):
        model.objects.filter(username__iexact=user.email).delete()
    user.delete()


def verify_user(user):
    if not user.email_verified_at:
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email_verified_at", "updated_at"])
