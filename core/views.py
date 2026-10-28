import logging

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.generic import TemplateView

from chat.models import ChatMessage
from vault.models import File, Folder

from .access import ApprovedMixin

logger = logging.getLogger(__name__)


def home(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    return redirect("core:dashboard" if request.user.approved else "accounts:status")


class DashboardView(ApprovedMixin, TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stats"] = File.objects.aggregate(total=Count("id"), storage=Sum("size_bytes"))
        context["folder_count"] = Folder.objects.count()
        context["member_count"] = (
            get_user_model()
            .objects.filter(status="approved", email_verified_at__isnull=False, is_active=True)
            .count()
        )
        context["recent_files"] = File.objects.select_related("owner", "folder")[:5]
        context["recent_messages"] = ChatMessage.objects.select_related("sender")[:3]
        return context


class PrivacyView(TemplateView):
    template_name = "core/privacy.html"


def live(request):
    return JsonResponse({"status": "ok", "service": "wefiles"})


def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        logger.exception("Database readiness failed")
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ready"})


def error_400(request, exception=None):
    return render(request, "errors/400.html", status=400)


def error_403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def error_404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def error_500(request):
    # Avoid context processors/database calls while handling an outage.
    return render(None, "errors/500.html", status=500)
