from django.urls import include, path

from .admin import site

urlpatterns = [
    path("", include("core.urls")),
    path("accounts/", include("accounts.urls")),
    path("vault/", include("vault.urls")),
    path("chat/", include("chat.urls")),
    path("notifications/", include("notifications.urls")),
    path("manage/activity/", include("activity.urls")),
    path("manage/", include("accounts.management_urls", namespace="management")),
    path("admin/", site.urls),
]
handler400 = "core.views.error_400"
handler403 = "core.views.error_403"
handler404 = "core.views.error_404"
handler500 = "core.views.error_500"
