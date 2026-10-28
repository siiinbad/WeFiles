from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    template_name = "notifications/list.html"
    context_object_name = "notifications"
    paginate_by = 25

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


@login_required
def unread(request):
    return render(
        request,
        "notifications/badge.html",
        {"unread_count": request.user.notifications.filter(read_at__isnull=True).count()},
    )


@login_required
@require_POST
def mark_read(request, pk):
    notification = get_object_or_404(Notification, recipient=request.user, pk=pk)
    notification.read_at = timezone.now()
    notification.save(update_fields=["read_at"])
    messages.success(request, "Notification marked as read.")
    return redirect("notifications:list")


@login_required
@require_POST
def read_all(request):
    request.user.notifications.filter(read_at__isnull=True).update(read_at=timezone.now())
    messages.success(request, "You're all caught up.")
    return redirect("notifications:list")
