from django.urls import path

from . import views

app_name = "notifications"
urlpatterns = [
    path("", views.NotificationListView.as_view(), name="list"),
    path("unread/", views.unread, name="unread"),
    path("read-all/", views.read_all, name="read_all"),
    path("<uuid:pk>/read/", views.mark_read, name="read"),
]
