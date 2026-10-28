from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from config.admin import site


class MaintenanceCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("email", "username")


class MaintenanceChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = get_user_model()
        fields = ("email", "username", "display_name")


@admin.register(get_user_model(), site=site)
class UserAdmin(BaseUserAdmin):
    form = MaintenanceChangeForm
    add_form = MaintenanceCreateForm
    list_display = ("username", "email", "role", "status", "email_verified_at")
    list_filter = ("role", "status")
    ordering = ("email",)
    search_fields = ("username", "email")
    fieldsets = (
        (None, {"fields": ("email", "username", "display_name", "password")}),
        (
            "Access (manage in the WeFiles member screen)",
            {
                "fields": (
                    "role",
                    "status",
                    "email_verified_at",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    add_fieldsets = ((None, {"fields": ("email", "username", "password1", "password2")}),)
    readonly_fields = (
        "role",
        "status",
        "email_verified_at",
        "is_active",
        "is_staff",
        "is_superuser",
        "groups",
        "user_permissions",
    )

    def has_add_permission(self, request):
        return request.user.is_superuser

    def get_readonly_fields(self, request, obj=None):
        return (*self.readonly_fields, "email") if obj else self.readonly_fields

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False  # Account erasure must run its storage/privacy service.
