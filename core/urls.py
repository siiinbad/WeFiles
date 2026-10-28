from django.urls import path

from . import views

app_name = "core"
urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("privacy/", views.PrivacyView.as_view(), name="privacy"),
    path("health/live/", views.live, name="live"),
    path("health/ready/", views.ready, name="ready"),
]
