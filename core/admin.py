from django.contrib import admin

from config.admin import site


class ReadOnlyAdmin(admin.ModelAdmin):
    """Maintenance inspection must not bypass mutation and cleanup services."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


def register_readonly(model, list_display):
    site.register(
        model, type(f"{model.__name__}Admin", (ReadOnlyAdmin,), {"list_display": list_display})
    )
