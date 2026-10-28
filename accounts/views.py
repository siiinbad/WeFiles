import binascii
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import FormView, ListView, TemplateView, UpdateView

from core.access import AdminMixin, admin_required
from core.services import rate_limit
from vault.models import File
from vault.services import process_deletions

from .forms import DeleteAccountForm, EmailLoginForm, ProfileForm, RegistrationForm
from .services import (
    change_membership,
    delete_account,
    register_user,
    send_verification,
    verify_user,
)
from .tokens import verification_token

logger = logging.getLogger(__name__)


@method_decorator(rate_limit("register"), name="dispatch")
class RegisterView(FormView):
    template_name = "accounts/register.html"
    form_class = RegistrationForm

    def form_valid(self, form):
        try:
            user = register_user(form)
        except IntegrityError:
            form.add_error(
                None,
                "That email or username was just registered. Please choose another or sign in.",
            )
            return self.form_invalid(form)
        login(self.request, user, backend="accounts.backends.EmailBackend")
        if not send_verification(user):
            messages.warning(
                self.request,
                "Your account was created, but the email could not be sent. Please try Resend verification shortly.",
            )
        return redirect("accounts:verification_sent")


@method_decorator(rate_limit("login", limit=30), name="dispatch")
class LoginView(auth_views.LoginView):
    authentication_form = EmailLoginForm
    template_name = "accounts/registration/login.html"

    def get_success_url(self):
        if not self.request.user.approved:
            return str(reverse_lazy("accounts:status"))
        return super().get_success_url()


class AccountStatusView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/status.html"


class VerificationSentView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/verification_sent.html"


@method_decorator(rate_limit("resend"), name="dispatch")
class ResendVerificationView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, "accounts/resend.html")

    def post(self, request):
        if request.user.email_verified_at:
            messages.info(request, "Your email is already verified.")
        elif send_verification(request.user):
            messages.success(request, "Verification sent. Please check your email.")
        else:
            messages.error(request, "Email could not be sent. Please try again shortly.")
        return redirect("accounts:status")


class VerifyEmailView(View):
    def get_user(self, uidb64):
        try:
            return get_user_model().objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
        except (
            ValueError,
            TypeError,
            UnicodeDecodeError,
            ValidationError,
            binascii.Error,
            get_user_model().DoesNotExist,
        ):
            return None

    def get(self, request, uidb64, token):
        user = self.get_user(uidb64)
        valid = bool(user and verification_token.check_token(user, token))
        return render(request, "accounts/verify.html", {"valid": valid})

    def post(self, request, uidb64, token):
        user = self.get_user(uidb64)
        if not user or not verification_token.check_token(user, token):
            return render(request, "accounts/verify.html", {"valid": False}, status=400)
        verify_user(user)
        messages.success(
            request,
            "Email verified. An administrator must also approve your account before you can access the vault.",
        )
        return redirect("accounts:status" if request.user.is_authenticated else "accounts:login")


@method_decorator(rate_limit("password-reset"), name="dispatch")
class PasswordResetView(auth_views.PasswordResetView):
    template_name = "accounts/registration/password_reset_form.html"
    email_template_name = "accounts/registration/password_reset_email.txt"
    subject_template_name = "accounts/registration/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")
    extra_email_context = {"site_url": settings.SITE_URL}

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except Exception:
            logger.exception("Password reset email delivery failed")
            return redirect(self.success_url)


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except IntegrityError:
            form.add_error("username", "That username is taken. Please choose another.")
            return self.form_invalid(form)
        messages.success(self.request, "Your profile has been updated.")
        return response


class AccountDeleteView(LoginRequiredMixin, FormView):
    form_class = DeleteAccountForm
    template_name = "accounts/delete.html"

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}

    def form_valid(self, form):
        try:
            delete_account(self.request.user)
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        logout(self.request)
        process_deletions(limit=100)
        messages.success(
            self.request,
            "Your account has been deleted. Any remaining storage cleanup will retry automatically.",
        )
        return redirect("accounts:login")


class AdminDashboardView(AdminMixin, TemplateView):
    template_name = "accounts/admin_dashboard.html"

    def get_context_data(self, **kwargs):
        from django.db.models import Sum

        from activity.models import ActivityEvent

        context = super().get_context_data(**kwargs)
        context["member_stats"] = get_user_model().objects.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status="pending")),
            approved=Count("id", filter=Q(status="approved")),
        )
        context["file_stats"] = File.objects.aggregate(total=Count("id"), storage=Sum("size_bytes"))
        context["pending_members"] = (
            get_user_model().objects.filter(status="pending").order_by("date_joined")[:5]
        )
        context["events"] = ActivityEvent.objects.select_related("actor")[:6]
        return context


class MemberListView(AdminMixin, ListView):
    template_name = "accounts/members.html"
    context_object_name = "members"
    paginate_by = 25

    def get_queryset(self):
        users = get_user_model().objects.order_by("-date_joined", "pk")
        q = self.request.GET.get("q", "")[:100]
        if q:
            users = users.filter(Q(username__icontains=q) | Q(email__icontains=q))
        status = self.request.GET.get("status")
        if status in get_user_model().Status.values:
            users = users.filter(status=status)
        return users


@admin_required
@require_POST
def member_action(request, pk, field):
    get_object_or_404(get_user_model(), pk=pk)
    if field not in ("role", "status"):
        raise Http404
    try:
        change_membership(request.user, pk, field, request.POST.get("value"))
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(request, "Member access updated.")
        if pk == request.user.pk and field == "role" and request.POST.get("value") == "member":
            return redirect("core:dashboard")
    return redirect("management:members")
