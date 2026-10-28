from django.views.generic import ListView

from core.access import AdminMixin

from .models import ActivityEvent


class ActivityListView(AdminMixin, ListView):
    queryset = ActivityEvent.objects.select_related("actor")
    template_name = "activity/list.html"
    context_object_name = "events"
    paginate_by = 30
