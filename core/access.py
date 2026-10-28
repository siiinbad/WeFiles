from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


class ApprovedMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.approved:
            return redirect("accounts:status")
        return super().dispatch(request, *args, **kwargs)


class AdminMixin(ApprovedMixin):
    def dispatch(self, request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and request.user.approved
            and not request.user.workspace_admin
        ):
            raise PermissionDenied("Only administrators can do that.")
        return super().dispatch(request, *args, **kwargs)


def approved_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.approved:
            return redirect("accounts:status")
        return view(request, *args, **kwargs)

    return wrapped


def admin_required(view):
    @approved_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.workspace_admin:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped
