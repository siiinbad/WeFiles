"""Workspace membership and administration routes owned by accounts."""

from django.urls import path

from . import views

app_name = "management"
urlpatterns = [
    path("", views.AdminDashboardView.as_view(), name="admin_dashboard"),
    path("members/", views.MemberListView.as_view(), name="members"),
    path("members/<uuid:pk>/<str:field>/", views.member_action, name="member_action"),
]
